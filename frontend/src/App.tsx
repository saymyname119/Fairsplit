import React, { useState, useEffect } from 'react';
import { useDarkMode } from './utils/useDarkMode';

import {
  api,
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
import { ExpenseModal } from './components/ExpenseModal';
import { ExpenseDetailModal } from './components/ExpenseDetailModal';
import { NewGroupModal } from './components/NewGroupModal';
import { AddMemberModal } from './components/AddMemberModal';
import { AcceptInvitationModal } from './components/AcceptInvitationModal';
import { AuthModal } from './components/AuthModal';
import { Footer } from './components/Footer';

export const App: React.FC = () => {
  const [isDark, toggleDark] = useDarkMode();

  const [currentUser, setCurrentUser] = useState<User | null>(() => {
    try {
      const saved = localStorage.getItem('sw_current_user');
      if (saved) return JSON.parse(saved);
    } catch {
      // ignore
    }
    return null;
  });
  const [groups, setGroups] = useState<Group[]>([]);
  const [selectedGroupId, setSelectedGroupId] = useState<string>('');
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [balances, setBalances] = useState<Record<string, number>>({});
  const [simplifiedDebts, setSimplifiedDebts] = useState<SettlementTransaction[]>([]);
  const [activeTab, setActiveTab] = useState<'overview' | 'balances' | 'expenses'>('overview');

  // Modals state
  const [isExpenseModalOpen, setIsExpenseModalOpen] = useState(false);
  const [isGroupModalOpen, setIsGroupModalOpen] = useState(false);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [isAddMemberModalOpen, setIsAddMemberModalOpen] = useState(false);
  const [addMemberGroupId, setAddMemberGroupId] = useState<string>('');
  const [selectedExpense, setSelectedExpense] = useState<Expense | null>(null);
  const [inviteToken, setInviteToken] = useState<string | null>(null);

  // Check URL for invitation token (?token=xxx or /invite/accept?token=xxx)
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get('token');
    if (token) {
      setInviteToken(token);
    }
  }, []);

  // Supabase session state — tracks Google OAuth + any Supabase auth
  const [supabaseSession, setSupabaseSession] = useState<Session | null>(null);

  // Load initial groups
  useEffect(() => {
    const init = async () => {
      await api.checkLiveBackend();
      const fetchedGroups = await api.getGroups();
      setGroups(fetchedGroups);
      if (fetchedGroups.length > 0) {
        setSelectedGroupId(fetchedGroups[0].id);
      }
    };
    init();
  }, [currentUser]);

  // ── Supabase Auth State Listener ──────────────────────────────────────
  // Listens for Google OAuth redirects, session refresh, and sign-outs.
  useEffect(() => {
    // Check for existing session on mount
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSupabaseSession(session);
      if (session?.user) {
        const meta = session.user.user_metadata;
        const name = meta?.full_name || meta?.name || session.user.email?.split('@')[0] || 'User';
        const avatarUrl = meta?.avatar_url || meta?.picture;

        api.syncOAuthUser(session.user.email || '', name, avatarUrl).then((syncedUser) => {
          setCurrentUser(syncedUser);
          localStorage.setItem('sw_current_user', JSON.stringify(syncedUser));
          api.getGroups().then((fetched) => setGroups(fetched));
        }).catch((err) => {
          console.warn('OAuth sync with backend failed, using session user:', err);
          const userObj: User = {
            id: session.user.id,
            name,
            email: session.user.email || '',
            avatar_url: avatarUrl,
          };
          setCurrentUser(userObj);
          localStorage.setItem('sw_current_user', JSON.stringify(userObj));
        });
      }
    });

    // Subscribe to future auth changes (OAuth callback, sign-out, etc.)
    const unsubscribe = onAuthStateChange((session, user) => {
      setSupabaseSession(session);
      if (session && user) {
        const meta = user.user_metadata;
        const name = meta?.full_name || meta?.name || user.email?.split('@')[0] || 'User';
        const avatarUrl = meta?.avatar_url || meta?.picture;

        api.syncOAuthUser(user.email || '', name, avatarUrl).then((syncedUser) => {
          setCurrentUser(syncedUser);
          localStorage.setItem('sw_current_user', JSON.stringify(syncedUser));
          api.getGroups().then((fetched) => setGroups(fetched));
        }).catch((err) => {
          console.warn('OAuth sync with backend failed, using session user:', err);
          const userObj: User = {
            id: user.id,
            name,
            email: user.email || '',
            avatar_url: avatarUrl,
          };
          setCurrentUser(userObj);
          localStorage.setItem('sw_current_user', JSON.stringify(userObj));
        });
      } else if (!session) {
        api.clearToken();
        localStorage.removeItem('sw_current_user');
        setCurrentUser(null);
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
  }, [selectedGroupId]);

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

  // Safe trigger handlers that gate on authentication
  const handleOpenNewGroup = () => {
    if (!currentUser || !api.hasToken()) {
      setIsAuthModalOpen(true);
    } else {
      setIsGroupModalOpen(true);
    }
  };

  const handleOpenNewExpense = () => {
    if (!currentUser || !api.hasToken()) {
      setIsAuthModalOpen(true);
    } else {
      setIsExpenseModalOpen(true);
    }
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
    if (!currentUser || !api.hasToken()) {
      setIsAuthModalOpen(true);
      throw new Error('Please sign in to record an expense.');
    }
    if (!selectedGroupId) {
      throw new Error('Please select or create a group first.');
    }
    const newExp = await api.createExpense({
      group_id: selectedGroupId,
      ...data,
    });
    setExpenses([newExp, ...expenses]);
    await refreshBalances();
  };

  // Create Group Handler
  const handleCreateGroup = async (name: string, currency: string) => {
    if (!currentUser || !api.hasToken()) {
      setIsAuthModalOpen(true);
      throw new Error('Please sign in or create an account to create a shared ledger.');
    }
    const newGrp = await api.createGroup(name, currency, currentUser.id);
    setGroups([newGrp, ...groups]);
    setSelectedGroupId(newGrp.id);
  };

  // Record Settlement Handler
  const handleSettle = async (payerId: string, payeeId: string, amount: number) => {
    if (!currentUser || !api.hasToken()) {
      setIsAuthModalOpen(true);
      return;
    }
    if (!selectedGroupId || !currentGroup) return;
    await api.recordSettlement(selectedGroupId, payerId, payeeId, amount, currentGroup.currency);
    const updatedExpenses = await api.getExpenses(selectedGroupId);
    setExpenses(updatedExpenses);
    await refreshBalances();
  };

  // Delete Expense Handler
  const handleDeleteExpense = async (expenseId: string) => {
    if (!currentUser || !api.hasToken()) {
      setIsAuthModalOpen(true);
      return;
    }
    if (!selectedGroupId) return;
    await api.deleteExpense(expenseId, selectedGroupId);
    setExpenses(expenses.filter((e) => e.id !== expenseId));
    await refreshBalances();
  };

  // Update Expense Handler
  const handleUpdateExpense = async (expenseId: string, updates: Parameters<typeof api.updateExpense>[2]) => {
    if (!currentUser || !api.hasToken()) {
      setIsAuthModalOpen(true);
      return;
    }
    if (!selectedGroupId) return;
    const updated = await api.updateExpense(expenseId, selectedGroupId, updates);
    setExpenses(expenses.map((e) => (e.id === expenseId ? updated : e)));
    setSelectedExpense(updated);
    await refreshBalances();
  };

  // Add Member Handler
  const handleOpenAddMember = (groupId: string) => {
    if (!currentUser || !api.hasToken()) {
      setIsAuthModalOpen(true);
      return;
    }
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
    if (!currentUser || !api.hasToken()) {
      setIsAuthModalOpen(true);
      return;
    }
    const confirmed = window.confirm(`Remove ${userName} from this group?`);
    if (!confirmed) return;
    const success = await api.removeMember(groupId, userId);
    if (success) {
      setGroups(
        groups.map((g) => {
          if (g.id !== groupId) return g;
          return { ...g, members: g.members.filter((m) => m.user_id !== userId) };
        })
      );
      // Refresh balances since member composition changed
      if (groupId === selectedGroupId) {
        await refreshBalances();
      }
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Navigation */}
      <TopNav
        currentUser={currentUser}
        isDark={isDark}
        onToggleDark={toggleDark}
        onOpenAuth={() => setIsAuthModalOpen(true)}
        onOpenNewGroup={handleOpenNewGroup}
        onOpenNewExpense={handleOpenNewExpense}
      />

      {/* Hero Band with warm cream & metric cards */}
      <HeroBand
        currentGroup={currentGroup}
        currentUser={currentUser}
        userNetBalance={userNetBalance}
        totalExpensesAmount={totalExpensesAmount}
        expensesCount={expenses.length}
        onOpenExpenseModal={handleOpenNewExpense}
        onOpenGroupModal={handleOpenNewGroup}
      />

      {/* Main Content Area */}
      <main className="app-container" style={{ flex: 1, paddingTop: '36px' }}>
        {/* Ledgers / Group Cards Row */}
        <GroupSelector
          groups={groups}
          selectedGroupId={selectedGroupId}
          onSelectGroup={(id) => setSelectedGroupId(id)}
          onOpenNewGroup={handleOpenNewGroup}
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
        </div>

        {/* Tab Content */}
        {currentGroup ? (
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
                  onOpenNewExpense={handleOpenNewExpense}
                  onSelectExpense={setSelectedExpense}
                />
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
                onOpenNewExpense={handleOpenNewExpense}
                onSelectExpense={setSelectedExpense}
              />
            )}
          </>
        ) : (
          <div
            style={{
              textAlign: 'center',
              padding: '64px 20px',
              backgroundColor: 'var(--color-card)',
              borderRadius: 'var(--radius-lg)',
              border: '1px dashed var(--color-hairline)',
              marginTop: '16px',
            }}
          >
            <h3 style={{ fontSize: '18px', fontWeight: 600, color: 'var(--color-primary)', marginBottom: '8px' }}>
              No ledger selected
            </h3>
            <p style={{ fontSize: '14px', color: 'var(--color-secondary)', maxWidth: '440px', margin: '0 auto 20px' }}>
              Create your first shared group ledger or sign in to collaborate with your team and split expenses seamlessly.
            </p>
            <button
              className="btn btn-primary"
              onClick={handleOpenNewGroup}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}
            >
              + Create Ledger
            </button>
          </div>
        )}
      </main>

      {/* Footer & Pre-footer Callout */}
      <Footer onOpenNewExpense={handleOpenNewExpense} />

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
        currentUser={currentUser}
        onOpenAuth={() => setIsAuthModalOpen(true)}
        onClose={() => setIsGroupModalOpen(false)}
        onSubmit={handleCreateGroup}
      />

      {currentGroup && (
        <AddMemberModal
          isOpen={isAddMemberModalOpen}
          groupId={addMemberGroupId || currentGroup.id}
          groupName={groups.find((g) => g.id === addMemberGroupId)?.name || currentGroup.name}
          onClose={() => setIsAddMemberModalOpen(false)}
          onSubmit={handleAddMember}
        />
      )}

      {inviteToken && (
        <AcceptInvitationModal
          token={inviteToken}
          onClose={() => setInviteToken(null)}
          onAccepted={async (groupId, joinedUser) => {
            if (joinedUser) {
              setCurrentUser(joinedUser);
            }
            const refreshed = await api.getGroups();
            setGroups(refreshed);
            setSelectedGroupId(groupId);
            setInviteToken(null);
            window.history.replaceState({}, document.title, window.location.pathname);
          }}
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
        onSelectUser={(u) => {
          setCurrentUser(u);
          if (u) {
            localStorage.setItem('sw_current_user', JSON.stringify(u));
            api.getGroups().then((fetched) => setGroups(fetched));
          } else {
            localStorage.removeItem('sw_current_user');
            setGroups([]);
          }
        }}
        onSupabaseLogout={async () => {
          await signOutSupabase();
          setSupabaseSession(null);
          api.clearToken();
          localStorage.removeItem('sw_current_user');
          setCurrentUser(null);
          setGroups([]);
          setIsAuthModalOpen(false);
        }}
      />
    </div>
  );
};

export default App;
