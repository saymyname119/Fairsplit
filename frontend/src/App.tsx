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
import { ExpenseDetailModal } from './components/ExpenseDetailModal';
import { NewGroupModal } from './components/NewGroupModal';
import { AddMemberModal } from './components/AddMemberModal';
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
  const [isAddMemberModalOpen, setIsAddMemberModalOpen] = useState(false);
  const [addMemberGroupId, setAddMemberGroupId] = useState<string>('');
  const [selectedExpense, setSelectedExpense] = useState<Expense | null>(null);

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
        if (session.access_token) {
          api.setToken(session.access_token);
        }
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
        if (session.access_token) {
          api.setToken(session.access_token);
        }
        api.isDemoMode = false;
        setIsDemoMode(false);
      } else if (!session) {
        api.clearToken();
        setCurrentUser(SEED_USERS[0]);
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

  // Delete Expense Handler
  const handleDeleteExpense = async (expenseId: string) => {
    if (!selectedGroupId) return;
    await api.deleteExpense(expenseId, selectedGroupId);
    setExpenses(expenses.filter((e) => e.id !== expenseId));
    await refreshBalances();
  };

  // Update Expense Handler
  const handleUpdateExpense = async (expenseId: string, updates: Parameters<typeof api.updateExpense>[2]) => {
    if (!selectedGroupId) return;
    const updated = await api.updateExpense(expenseId, selectedGroupId, updates);
    setExpenses(expenses.map((e) => e.id === expenseId ? updated : e));
    setSelectedExpense(updated);
    await refreshBalances();
  };

  // Add Member Handler
  const handleOpenAddMember = (groupId: string) => {
    setAddMemberGroupId(groupId);
    setIsAddMemberModalOpen(true);
  };

  const handleAddMember = async (name: string, email: string) => {
    if (!addMemberGroupId) return;
    const updated = await api.addMember(addMemberGroupId, name, email);
    if (updated) {
      setGroups(groups.map((g) => (g.id === updated.id ? updated : g)));
    }
  };

  // Remove Member Handler
  const handleRemoveMember = async (groupId: string, userId: string, userName: string) => {
    const confirmed = window.confirm(`Remove ${userName} from this group?`);
    if (!confirmed) return;
    const success = await api.removeMember(groupId, userId);
    if (success) {
      setGroups(groups.map((g) => {
        if (g.id !== groupId) return g;
        return { ...g, members: g.members.filter((m) => m.user_id !== userId) };
      }));
      // Refresh balances since member composition changed
      if (groupId === selectedGroupId) {
        await refreshBalances();
      }
    }
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
          onAddMember={handleOpenAddMember}
          onRemoveMember={handleRemoveMember}
        />

        {/* Section Navigation — Apple Segmented Control */}
        <div className="segmented-control" style={{ marginBottom: '28px' }}>
          <button
            className={`segmented-btn ${activeTab === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveTab('overview')}
          >
            Ledger Overview
          </button>
          <button
            className={`segmented-btn ${activeTab === 'balances' ? 'active' : ''}`}
            onClick={() => setActiveTab('balances')}
          >
            Settlement Plan
          </button>
          <button
            className={`segmented-btn ${activeTab === 'expenses' ? 'active' : ''}`}
            onClick={() => setActiveTab('expenses')}
          >
            Expenses ({expenses.length})
          </button>
          <button
            className={`segmented-btn ${activeTab === 'telemetry' ? 'active' : ''}`}
            onClick={() => setActiveTab('telemetry')}
          >
            Architecture
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
                  onSelectExpense={setSelectedExpense}
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
                onSelectExpense={setSelectedExpense}
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

      {currentGroup && (
        <AddMemberModal
          isOpen={isAddMemberModalOpen}
          groupName={groups.find((g) => g.id === addMemberGroupId)?.name || 'Group'}
          onClose={() => setIsAddMemberModalOpen(false)}
          onSubmit={handleAddMember}
        />
      )}

      {currentGroup && selectedExpense && (
        <ExpenseDetailModal
          expense={selectedExpense}
          group={currentGroup}
          isOpen={!!selectedExpense}
          onClose={() => setSelectedExpense(null)}
          onDelete={handleDeleteExpense}
          onUpdate={handleUpdateExpense}
        />
      )}

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
