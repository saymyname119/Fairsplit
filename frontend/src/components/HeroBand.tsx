import React from 'react';
import { ArrowUpRight, ArrowDownLeft, Receipt, Users, PlusCircle } from 'lucide-react';
import type { Group, User } from '../api/client';

interface HeroBandProps {
  currentGroup: Group | null;
  currentUser: User | null;
  userNetBalance: number;
  totalExpensesAmount: number;
  expensesCount: number;
  onOpenExpenseModal: () => void;
  onOpenGroupModal: () => void;
}

export const HeroBand: React.FC<HeroBandProps> = ({
  currentGroup,
  currentUser,
  userNetBalance,
  totalExpensesAmount,
  expensesCount,
  onOpenExpenseModal,
  onOpenGroupModal,
}) => {
  const isOwed = userNetBalance > 0.009;
  const owes = userNetBalance < -0.009;

  return (
    <section
      style={{
        padding: '48px 0 36px',
        backgroundColor: 'var(--color-canvas)',
        borderBottom: '1px solid var(--color-hairline)',
      }}
    >
      <div className="app-container">
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'minmax(0, 1.4fr) minmax(0, 1fr)',
            gap: '36px',
            alignItems: 'center',
          }}
        >
          {/* Left: Editorial Headline & Subtitle */}
          <div>
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
              <span className="badge badge-coral">MODULAR MONOLITH</span>
              <span className="caption" style={{ color: 'var(--color-muted)' }}>
                Exact Money Arithmetic • Write-Invalidate Cache
              </span>
            </div>

            <h1 className="display-lg" style={{ marginBottom: '16px', color: 'var(--color-ink)' }}>
              Expenses divided, <br />
              <span style={{ fontStyle: 'italic', color: 'var(--color-primary)' }}>friendships multiplied.</span>
            </h1>

            <p className="body-md" style={{ color: 'var(--color-body)', maxWidth: '520px', marginBottom: '28px' }}>
              Track group travel, flatmate ledgers, and shared dinners with exact decimal arithmetic.
              Greedy net-flow debt simplification guarantees minimum settlements.
            </p>

            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <button onClick={onOpenExpenseModal} className="btn btn-primary" style={{ height: '42px', padding: '0 26px', fontSize: '15px', fontWeight: 500 }}>
                <PlusCircle size={16} />
                <span>Record Expense</span>
              </button>
              <button onClick={onOpenGroupModal} className="btn btn-secondary" style={{ height: '42px', padding: '0 22px', fontSize: '15px' }}>
                <Users size={16} />
                <span>Create Group</span>
              </button>
            </div>
          </div>

          {/* Right: Metric Showcase Card */}
          <div
            className="card-cream"
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '20px',
              padding: '28px',
              boxShadow: '0 4px 16px rgba(20, 20, 19, 0.03)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <span className="caption-uppercase" style={{ color: 'var(--color-muted)' }}>
                  Active Focus Group
                </span>
                <h3
                  style={{
                    fontFamily: 'var(--font-display)',
                    fontSize: '22px',
                    fontWeight: 500,
                    marginTop: '2px',
                  }}
                >
                  {currentGroup ? currentGroup.name : 'All Groups'}
                </h3>
              </div>
              <span className="badge badge-teal font-mono">
                {currentGroup ? `${currentGroup.members.length} members` : '0 members'}
              </span>
            </div>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: '16px',
                paddingTop: '6px',
                borderTop: '1px solid var(--color-hairline)',
              }}
            >
              {/* User Net Balance */}
              <div
                style={{
                  backgroundColor: 'var(--color-canvas)',
                  padding: '16px',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--color-hairline)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
                  {isOwed ? (
                    <ArrowDownLeft size={16} style={{ color: 'var(--color-success)' }} />
                  ) : owes ? (
                    <ArrowUpRight size={16} style={{ color: 'var(--color-primary)' }} />
                  ) : (
                    <Receipt size={16} style={{ color: 'var(--color-muted)' }} />
                  )}
                  <span className="caption" style={{ color: 'var(--color-muted)' }}>
                    {currentUser ? `${currentUser.name.split(' ')[0]}'s Net Position` : 'Your Net Position'}
                  </span>
                </div>
                <div
                  className="font-mono"
                  style={{
                    fontSize: '22px',
                    fontWeight: 600,
                    color: isOwed ? 'var(--color-success)' : owes ? 'var(--color-primary)' : 'var(--color-ink)',
                  }}
                >
                  {isOwed ? `+$${userNetBalance.toFixed(2)}` : owes ? `-$${Math.abs(userNetBalance).toFixed(2)}` : '$0.00'}
                </div>
                <div className="caption" style={{ color: 'var(--color-muted-soft)', marginTop: '2px' }}>
                  {isOwed ? 'You are owed' : owes ? 'You owe money' : 'Completely settled up'}
                </div>
              </div>

              {/* Total Group Volume */}
              <div
                style={{
                  backgroundColor: 'var(--color-canvas)',
                  padding: '16px',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--color-hairline)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
                  <Receipt size={16} style={{ color: 'var(--color-accent-amber)' }} />
                  <span className="caption" style={{ color: 'var(--color-muted)' }}>
                    Group Spending
                  </span>
                </div>
                <div className="font-mono" style={{ fontSize: '22px', fontWeight: 600, color: 'var(--color-ink)' }}>
                  ${totalExpensesAmount.toFixed(2)}
                </div>
                <div className="caption" style={{ color: 'var(--color-muted-soft)', marginTop: '2px' }}>
                  Across {expensesCount} expenses
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
