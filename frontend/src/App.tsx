import React, { useState, useEffect } from 'react';
import {
  api,
  demoStore,
  SEED_USERS,
  type Group,
  type Expense,
  type User,
  type SettlementTransaction,
  type SplitStrategy,
  type SplitItem,
} from './api/client';
import { supabase, onAuthStateChange, signOutSupabase, type Session } from './utils/supabase';
import { TopNav } from './components/TopNav';
import { HeroBand } from './components/HeroBand';
import { GroupSelector } from './components/GroupSelector';
import { BalanceView } from './components/BalanceView';
import { ExpensesList } from './components/ExpensesList';
import { ActivityMockup } from './components/ActivityMockup';
import { ExpenseModal } from './components/ExpenseModal';
import { NewGroupModal } from './components/NewGroupModal';
import { AuthModal } from './components/AuthModal';
import { Footer } from './components/Footer';

export const App: React.FC = () => {
  const [currentUser, setCurrentUser] = useState<User>(SEED_USERS[0]);
  const [groups, setGroups] = useState<Group[]>([]);
  const [selectedGroupId, setSelectedGroupId] = useState<string>('');
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [balances, setBalances] = useState<Record<string, number>>({});
  const [simplifiedDebts, setSimplifiedDebts] = useState<SettlementTransaction[]>([]);
  const [isDemoMode, setIsDemoMode] = useState<boolean>(api.isDemoMode);
  const [activeTab, setActiveTab] = useState<'overview' | 'balances' | 'expenses' | 'telemetry'>('overview');

  // Modals state
  const [isExpenseModalOpen, setIsExpenseModalOpen] = useState(false);
  const [isGroupModalOpen, setIsGroupModalOpen] = useState(false);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  // Supabase session state — tracks Google OAuth + any Supabase auth
  const [supabaseSession, setSupabaseSession] = useState<Session | null>(null);

  // Load initial groups
  useEffect(() => {
    const init = async () => {
      await api.checkLiveBackend();
      setIsDemoMode(api.isDemoMode);
      const fetchedGroups = await api.getGroups();
      setGroups(fetchedGroups);
      if (fetchedGroups.length > 0) {
        setSelectedGroupId(fetchedGroups[0].id);
      }
    };
    init();
  }, []);

  // ── Supabase Auth State Listener ──────────────────────────────────────
  // Listens for Google OAuth redirects, session refresh, and sign-outs.
  useEffect(() => {
    // Check for existing session on mount
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSupabaseSession(session);
      if (session?.user) {
        const meta = session.user.user_metadata;
        setCurrentUser({
          id: session.user.id,
          name: meta?.full_name || meta?.name || session.user.email?.split('@')[0] || 'User',
          email: session.user.email || '',
          avatar_url: meta?.avatar_url || meta?.picture,
        });
        api.isDemoMode = false;
        setIsDemoMode(false);
      }
    });

    // Subscribe to future auth changes (OAuth callback, sign-out, etc.)
    const unsubscribe = onAuthStateChange((session, user) => {
      setSupabaseSession(session);
      if (session && user) {
        const meta = user.user_metadata;
        setCurrentUser({
          id: user.id,
          name: meta?.full_name || meta?.name || user.email?.split('@')[0] || 'User',
          email: user.email || '',
          avatar_url: meta?.avatar_url || meta?.picture,
        });
        api.isDemoMode = false;
        setIsDemoMode(false);
      }
    });

    return unsubscribe;
  }, []);

  // When selected group changes, load its data
  useEffect(() => {
    if (!selectedGroupId) return;

    const loadGroupData = async () => {
      const expList = await api.getExpenses(selectedGroupId);
      setExpenses(expList);

      const bal = await api.getBalances(selectedGroupId);
      setBalances(bal);

      const debts = await api.getSimplifiedDebts(selectedGroupId);
      setSimplifiedDebts(debts);
    };

    loadGroupData();
  }, [selectedGroupId, isDemoMode]);

  const currentGroup = groups.find((g) => g.id === selectedGroupId) || groups[0] || null;
  const userNetBalance = currentUser ? balances[currentUser.id] || 0 : 0;
  const totalExpensesAmount = expenses.reduce((sum, e) => sum + e.amount, 0);

  // Refresh handler
  const refreshBalances = async () => {
    if (!selectedGroupId) return;
    const b = await api.getBalances(selectedGroupId);
    setBalances(b);
    const d = await api.getSimplifiedDebts(selectedGroupId);
    setSimplifiedDebts(d);
  };

  // Add Expense Handler
  const handleAddExpense = async (data: {
    description: string;
    amount: number;
    currency: string;
    paid_by_id: string;
    split_strategy: SplitStrategy;
    splits: SplitItem[];
  }) => {
    if (!selectedGroupId) return;
    const newExp = await api.createExpense({
      group_id: selectedGroupId,
      ...data,
    });
    setExpenses([newExp, ...expenses]);
    await refreshBalances();
  };

  // Create Group Handler
  const handleCreateGroup = async (name: string, currency: string) => {
    const newGrp = await api.createGroup(name, currency, currentUser.id);
    setGroups([newGrp, ...groups]);
    setSelectedGroupId(newGrp.id);
  };

  // Record Settlement Handler
  const handleSettle = async (payerId: string, payeeId: string, amount: number) => {
    if (!selectedGroupId || !currentGroup) return;
    await api.recordSettlement(selectedGroupId, payerId, payeeId, amount, currentGroup.currency);
    const updatedExpenses = await api.getExpenses(selectedGroupId);
    setExpenses(updatedExpenses);
    await refreshBalances();
  };

  // Toggle demo mode
  const handleToggleDemo = async () => {
    if (api.isDemoMode) {
      const liveOk = await api.checkLiveBackend();
      if (!liveOk) {
        alert('FastAPI backend is currently offline at http://localhost:8000. Running in Demo Sandbox mode!');
      }
    } else {
      api.isDemoMode = true;
    }
    setIsDemoMode(api.isDemoMode);
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Navigation */}
      <TopNav
        currentUser={currentUser}
        isDemoMode={isDemoMode}
        onToggleDemo={handleToggleDemo}
        onOpenAuth={() => setIsAuthModalOpen(true)}
        onOpenNewGroup={() => setIsGroupModalOpen(true)}
        onOpenNewExpense={() => setIsExpenseModalOpen(true)}
      />

      {/* Hero Band with warm cream & metric cards */}
      <HeroBand
        currentGroup={currentGroup}
        currentUser={currentUser}
        userNetBalance={userNetBalance}
        totalExpensesAmount={totalExpensesAmount}
        expensesCount={expenses.length}
        onOpenExpenseModal={() => setIsExpenseModalOpen(true)}
        onOpenGroupModal={() => setIsGroupModalOpen(true)}
      />

      {/* Main Content Area */}
      <main className="app-container" style={{ flex: 1, paddingTop: '36px' }}>
        {/* Ledgers / Group Cards Row */}
        <GroupSelector
          groups={groups}
          selectedGroupId={selectedGroupId}
          onSelectGroup={(id) => setSelectedGroupId(id)}
          onOpenNewGroup={() => setIsGroupModalOpen(true)}
        />

        {/* Section Navigation Tabs */}
        <div className="tabs-container" style={{ marginBottom: '28px' }}>
          <button
            className={`tab-btn ${activeTab === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveTab('overview')}
          >
            Ledger Overview
          </button>
          <button
            className={`tab-btn ${activeTab === 'balances' ? 'active' : ''}`}
            onClick={() => setActiveTab('balances')}
          >
            Settlement Plan & Balances
          </button>
          <button
            className={`tab-btn ${activeTab === 'expenses' ? 'active' : ''}`}
            onClick={() => setActiveTab('expenses')}
          >
            Expenses & Receipts ({expenses.length})
          </button>
          <button
            className={`tab-btn ${activeTab === 'telemetry' ? 'active' : ''}`}
            onClick={() => setActiveTab('telemetry')}
          >
            Architecture Telemetry
          </button>
        </div>

        {/* Tab Content */}
        {currentGroup && (
          <>
            {activeTab === 'overview' && (
              <>
                <BalanceView
                  group={currentGroup}
                  balances={balances}
                  simplifiedDebts={simplifiedDebts}
                  onSettle={handleSettle}
                  onRefresh={refreshBalances}
                />
                <ExpensesList
                  expenses={expenses}
                  currency={currentGroup.currency}
                  onOpenNewExpense={() => setIsExpenseModalOpen(true)}
                />
                <ActivityMockup events={demoStore.events} />
              </>
            )}

            {activeTab === 'balances' && (
              <BalanceView
                group={currentGroup}
                balances={balances}
                simplifiedDebts={simplifiedDebts}
                onSettle={handleSettle}
                onRefresh={refreshBalances}
              />
            )}

            {activeTab === 'expenses' && (
              <ExpensesList
                expenses={expenses}
                currency={currentGroup.currency}
                onOpenNewExpense={() => setIsExpenseModalOpen(true)}
              />
            )}

            {activeTab === 'telemetry' && <ActivityMockup events={demoStore.events} />}
          </>
        )}
      </main>

      {/* Footer & Pre-footer Callout */}
      <Footer onOpenNewExpense={() => setIsExpenseModalOpen(true)} />

      {/* Modals */}
      {currentGroup && (
        <ExpenseModal
          group={currentGroup}
          isOpen={isExpenseModalOpen}
          onClose={() => setIsExpenseModalOpen(false)}
          onSubmit={handleAddExpense}
        />
      )}

      <NewGroupModal
        isOpen={isGroupModalOpen}
        onClose={() => setIsGroupModalOpen(false)}
        onSubmit={handleCreateGroup}
      />

      <AuthModal
        isOpen={isAuthModalOpen}
        currentUser={currentUser}
        supabaseSession={supabaseSession}
        onClose={() => setIsAuthModalOpen(false)}
        onSelectUser={(u) => setCurrentUser(u)}
        onSupabaseLogout={async () => {
          await signOutSupabase();
          setSupabaseSession(null);
          api.isDemoMode = true;
          setIsDemoMode(true);
          setCurrentUser(SEED_USERS[0]);
          setIsAuthModalOpen(false);
        }}
      />
    </div>
  );
};

export default App;
