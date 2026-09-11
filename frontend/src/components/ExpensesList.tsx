import React from 'react';
import { Receipt, Calendar, CreditCard } from 'lucide-react';
import type { Expense } from '../api/client';

interface ExpensesListProps {
  expenses: Expense[];
  currency: string;
  onOpenNewExpense: () => void;
}

export const ExpensesList: React.FC<ExpensesListProps> = ({
  expenses,
  currency,
  onOpenNewExpense,
}) => {
  return (
    <div style={{ marginBottom: '36px' }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '16px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Receipt size={18} style={{ color: 'var(--color-primary)' }} />
          <h2
            style={{
              fontFamily: 'var(--font-display)',
              fontSize: '22px',
              fontWeight: 500,
              color: 'var(--color-ink)',
            }}
          >
            Ledger Activity & Receipts
          </h2>
        </div>
        <button
          onClick={onOpenNewExpense}
          className="btn btn-primary"
          style={{ height: '32px', padding: '0 14px', fontSize: '13px' }}
        >
          + Add Expense
        </button>
      </div>

      {expenses.length === 0 ? (
        <div
          className="card-white"
          style={{
            textAlign: 'center',
            padding: '48px 24px',
            borderRadius: 'var(--radius-lg)',
          }}
        >
          <Receipt size={36} style={{ color: 'var(--color-muted-soft)', margin: '0 auto 12px' }} />
          <h4 style={{ fontFamily: 'var(--font-display)', fontSize: '20px', color: 'var(--color-ink)' }}>
            No expenses recorded yet
          </h4>
          <p className="body-sm" style={{ maxWidth: '400px', margin: '6px auto 18px' }}>
            Add your first shared expense to start tracking splits and balances.
          </p>
          <button onClick={onOpenNewExpense} className="btn btn-primary">
            Record First Expense
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {expenses.map((expense) => {
            const isSettlement = expense.description.startsWith('Settlement:');
            const dateStr = new Date(expense.created_at).toLocaleDateString('en-US', {
              month: 'short',
              day: 'numeric',
              year: 'numeric',
            });

            return (
              <div
                key={expense.id}
                className="card-white"
                style={{
                  padding: '16px 20px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  borderRadius: 'var(--radius-md)',
                  transition: 'border-color 0.15s ease',
                  borderLeft: isSettlement
                    ? '4px solid var(--color-success)'
                    : '4px solid var(--color-primary)',
                }}
              >
                {/* Left info */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                  <div
                    style={{
                      width: '40px',
                      height: '40px',
                      borderRadius: 'var(--radius-md)',
                      backgroundColor: isSettlement ? 'rgba(93, 184, 114, 0.12)' : 'var(--color-surface-soft)',
                      color: isSettlement ? 'var(--color-success)' : 'var(--color-primary)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    {isSettlement ? <CreditCard size={20} /> : <Receipt size={20} />}
                  </div>

                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <h4 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--color-ink)' }}>
                        {expense.description}
                      </h4>
                      <span className="badge badge-cream caption-uppercase" style={{ fontSize: '10px' }}>
                        {expense.split_strategy}
                      </span>
                    </div>

                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '12px',
                        marginTop: '4px',
                        fontSize: '13px',
                        color: 'var(--color-muted)',
                      }}
                    >
                      <span>
                        Paid by <strong>{expense.paid_by?.name || 'Member'}</strong>
                      </span>
                      <span>•</span>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <Calendar size={12} />
                        {dateStr}
                      </span>
                      <span>•</span>
                      <span>{expense.splits.length} split participants</span>
                    </div>
                  </div>
                </div>

                {/* Right Amount */}
                <div style={{ textAlign: 'right' }}>
                  <div
                    className="font-mono"
                    style={{
                      fontSize: '18px',
                      fontWeight: 600,
                      color: isSettlement ? 'var(--color-success)' : 'var(--color-ink)',
                    }}
                  >
                    ${expense.amount.toFixed(2)}
                  </div>
                  <div className="caption" style={{ color: 'var(--color-muted-soft)', fontSize: '11px' }}>
                    {currency}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
