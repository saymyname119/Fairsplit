import React, { useState, useMemo } from 'react';
import { Receipt, Calendar, CreditCard, ChevronRight, Search, Filter } from 'lucide-react';
import type { Expense } from '../api/client';

interface ExpensesListProps {
  expenses: Expense[];
  currency: string;
  onOpenNewExpense: () => void;
  onSelectExpense: (expense: Expense) => void;
}

export const ExpensesList: React.FC<ExpensesListProps> = ({
  expenses,
  currency,
  onOpenNewExpense,
  onSelectExpense,
}) => {
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [payerFilter, setPayerFilter] = useState<string>('all');

  // Unique payers for filter dropdown
  const uniquePayers = useMemo(() => {
    const map = new Map<string, string>();
    expenses.forEach((e) => {
      if (e.paid_by_id && !map.has(e.paid_by_id)) {
        map.set(e.paid_by_id, e.paid_by?.name || 'Member');
      }
    });
    return Array.from(map.entries()); // [id, name][]
  }, [expenses]);

  // Filtered expenses
  const filteredExpenses = useMemo(() => {
    return expenses.filter((e) => {
      const matchesSearch = searchQuery.trim() === '' ||
        e.description.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesPayer = payerFilter === 'all' || e.paid_by_id === payerFilter;
      return matchesSearch && matchesPayer;
    });
  }, [expenses, searchQuery, payerFilter]);

  const hasActiveFilter = searchQuery.trim() !== '' || payerFilter !== 'all';

  return (
    <div style={{ marginBottom: '36px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Receipt size={18} style={{ color: 'var(--color-primary)' }} />
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '22px', fontWeight: 500, color: 'var(--color-ink)' }}>
            Ledger Activity &amp; Receipts
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

      {/* Search & Filter Bar */}
      {expenses.length > 0 && (
        <div
          style={{
            display: 'flex',
            gap: '10px',
            marginBottom: '14px',
            alignItems: 'center',
          }}
        >
          <div
            style={{
              flex: 1,
              position: 'relative',
            }}
          >
            <Search
              size={15}
              style={{
                position: 'absolute',
                left: '12px',
                top: '50%',
                transform: 'translateY(-50%)',
                color: 'var(--color-muted)',
                pointerEvents: 'none',
              }}
            />
            <input
              type="text"
              placeholder="Search expenses…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: '100%',
                height: '36px',
                paddingLeft: '36px',
                paddingRight: '12px',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--color-hairline)',
                backgroundColor: 'var(--color-canvas)',
                fontSize: '13px',
                color: 'var(--color-ink)',
                fontFamily: 'var(--font-body)',
                outline: 'none',
                transition: 'border-color 0.15s ease',
              }}
              onFocus={(e) => (e.target.style.borderColor = 'var(--color-primary)')}
              onBlur={(e) => (e.target.style.borderColor = 'var(--color-hairline)')}
            />
          </div>

          <div
            style={{
              position: 'relative',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <Filter size={14} style={{ color: 'var(--color-muted)', flexShrink: 0 }} />
            <select
              value={payerFilter}
              onChange={(e) => setPayerFilter(e.target.value)}
              style={{
                height: '36px',
                padding: '0 28px 0 8px',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--color-hairline)',
                backgroundColor: 'var(--color-canvas)',
                fontSize: '13px',
                color: 'var(--color-ink)',
                fontFamily: 'var(--font-body)',
                cursor: 'pointer',
                outline: 'none',
                appearance: 'auto',
              }}
            >
              <option value="all">All Payers</option>
              {uniquePayers.map(([id, name]) => (
                <option key={id} value={id}>
                  {name}
                </option>
              ))}
            </select>
          </div>

          {hasActiveFilter && (
            <button
              onClick={() => { setSearchQuery(''); setPayerFilter('all'); }}
              className="btn btn-secondary"
              style={{ height: '36px', padding: '0 10px', fontSize: '12px', flexShrink: 0 }}
            >
              Clear
            </button>
          )}
        </div>
      )}

      {expenses.length === 0 ? (
        <div className="card-white" style={{ textAlign: 'center', padding: '48px 24px', borderRadius: 'var(--radius-lg)' }}>
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
      ) : filteredExpenses.length === 0 ? (
        <div
          className="card-white"
          style={{
            textAlign: 'center',
            padding: '36px 24px',
            borderRadius: 'var(--radius-lg)',
          }}
        >
          <Search size={28} style={{ color: 'var(--color-muted-soft)', margin: '0 auto 10px' }} />
          <h4 style={{ fontFamily: 'var(--font-display)', fontSize: '18px', color: 'var(--color-ink)' }}>
            No matching expenses
          </h4>
          <p className="body-sm" style={{ color: 'var(--color-muted)', marginTop: '4px' }}>
            Try adjusting your search or filter criteria.
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {filteredExpenses.map((expense) => {
            const isSettlement = expense.description.startsWith('Settlement:');
            const isHovered = hoveredId === expense.id;
            const dateStr = new Date(expense.created_at).toLocaleDateString('en-US', {
              month: 'short', day: 'numeric', year: 'numeric',
            });

            return (
              <div
                key={expense.id}
                onClick={() => onSelectExpense(expense)}
                onMouseEnter={() => setHoveredId(expense.id)}
                onMouseLeave={() => setHoveredId(null)}
                style={{
                  padding: '14px 18px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  borderRadius: 'var(--radius-md)',
                  borderLeft: `4px solid ${isSettlement ? 'var(--color-success)' : 'var(--color-primary)'}`,
                  borderTop: isHovered
                    ? `1px solid ${isSettlement ? 'var(--color-success)' : 'var(--color-primary)'}`
                    : '1px solid var(--color-hairline)',
                  borderRight: isHovered
                    ? `1px solid ${isSettlement ? 'var(--color-success)' : 'var(--color-primary)'}`
                    : '1px solid var(--color-hairline)',
                  borderBottom: isHovered
                    ? `1px solid ${isSettlement ? 'var(--color-success)' : 'var(--color-primary)'}`
                    : '1px solid var(--color-hairline)',
                  backgroundColor: isHovered
                    ? (isSettlement ? 'rgba(93,184,114,0.04)' : 'rgba(204,120,92,0.04)')
                    : '#ffffff',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                  boxShadow: isHovered ? '0 2px 12px rgba(20,20,19,0.07)' : '0 1px 3px rgba(20,20,19,0.04)',
                  transform: isHovered ? 'translateY(-1px)' : 'none',
                }}
              >
                {/* Left */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                  <div style={{
                    width: '38px', height: '38px', borderRadius: 'var(--radius-md)', flexShrink: 0,
                    backgroundColor: isSettlement ? 'rgba(93,184,114,0.12)' : 'var(--color-surface-soft)',
                    color: isSettlement ? 'var(--color-success)' : 'var(--color-primary)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                  }}>
                    {isSettlement ? <CreditCard size={18} /> : <Receipt size={18} />}
                  </div>

                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <h4 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--color-ink)' }}>
                        {expense.description}
                      </h4>
                      <span style={{
                        display: 'inline-flex', alignItems: 'center', padding: '2px 8px',
                        borderRadius: 'var(--radius-pill)', fontSize: '10px', fontWeight: 700,
                        textTransform: 'uppercase', letterSpacing: '0.5px',
                        backgroundColor: 'var(--color-surface-cream-strong)', color: 'var(--color-muted)',
                        border: '1px solid var(--color-hairline)',
                      }}>
                        {expense.split_strategy}
                      </span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '3px', fontSize: '12px', color: 'var(--color-muted)' }}>
                      <span>
                        Paid by{' '}
                        <strong style={{ color: 'var(--color-body-strong)' }}>
                          {expense.paid_by?.name || 'Member'}
                        </strong>
                      </span>
                      <span style={{ opacity: 0.4 }}>·</span>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
                        <Calendar size={11} />
                        {dateStr}
                      </span>
                      <span style={{ opacity: 0.4 }}>·</span>
                      <span>{expense.splits.length} participants</span>
                    </div>
                  </div>
                </div>

                {/* Right */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexShrink: 0 }}>
                  <div style={{ textAlign: 'right' }}>
                    <div className="font-mono" style={{
                      fontSize: '16px', fontWeight: 700,
                      color: isSettlement ? 'var(--color-success)' : 'var(--color-ink)',
                    }}>
                      ${expense.amount.toFixed(2)}
                    </div>
                    <div style={{ fontSize: '10px', color: 'var(--color-muted-soft)' }}>{currency}</div>
                  </div>
                  <ChevronRight
                    size={16}
                    style={{
                      color: isHovered ? 'var(--color-primary)' : 'var(--color-muted-soft)',
                      transition: 'color 0.15s ease, transform 0.15s ease',
                      transform: isHovered ? 'translateX(2px)' : 'none',
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
