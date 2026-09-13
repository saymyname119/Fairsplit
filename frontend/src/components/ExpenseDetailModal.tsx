import React, { useState, useEffect } from 'react';
import {
  X, Trash2, Pencil, CheckCircle2, AlertCircle, Calendar,
  CreditCard, Receipt, Users, ArrowRight,
} from 'lucide-react';
import type { Expense, Group, SplitStrategy, SplitItem } from '../api/client';

interface ExpenseDetailModalProps {
  expense: Expense | null;
  group: Group;
  isOpen: boolean;
  onClose: () => void;
  onDelete: (expenseId: string) => Promise<void>;
  onUpdate: (expenseId: string, updates: {
    description?: string;
    amount?: number;
    paid_by_id?: string;
    split_strategy?: SplitStrategy;
    splits?: SplitItem[];
  }) => Promise<void>;
}

export const ExpenseDetailModal: React.FC<ExpenseDetailModalProps> = ({
  expense,
  group,
  isOpen,
  onClose,
  onDelete,
  onUpdate,
}) => {
  const [mode, setMode] = useState<'view' | 'edit'>('view');
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Edit form state
  const [description, setDescription] = useState('');
  const [amountStr, setAmountStr] = useState('');
  const [paidById, setPaidById] = useState('');
  const [splitStrategy, setSplitStrategy] = useState<SplitStrategy>('EQUAL');
  const [selectedUserIds, setSelectedUserIds] = useState<string[]>([]);
  const [exactAmounts, setExactAmounts] = useState<Record<string, string>>({});

  // Sync form state when expense changes
  useEffect(() => {
    if (expense) {
      setDescription(expense.description);
      setAmountStr(String(expense.amount));
      setPaidById(expense.paid_by_id);
      setSplitStrategy(expense.split_strategy);
      setSelectedUserIds(expense.splits.map((s) => s.user_id));
      const ex: Record<string, string> = {};
      expense.splits.forEach((s) => { if (s.amount) ex[s.user_id] = String(s.amount); });
      setExactAmounts(ex);
      setMode('view');
      setConfirmDelete(false);
      setErrorMsg(null);
    }
  }, [expense]);

  if (!isOpen || !expense) return null;

  const isSettlement = expense.description.startsWith('Settlement:');
  const dateStr = new Date(expense.created_at).toLocaleDateString('en-US', {
    weekday: 'short', month: 'long', day: 'numeric', year: 'numeric',
  });
  const amount = parseFloat(amountStr) || 0;
  const exactSum = Object.values(exactAmounts).reduce((s, v) => s + (parseFloat(v) || 0), 0);

  const getMemberName = (userId: string) =>
    group.members.find((m) => m.user_id === userId)?.user.name || userId;

  const toggleUserEqual = (userId: string) => {
    if (selectedUserIds.includes(userId)) {
      if (selectedUserIds.length > 1) setSelectedUserIds(selectedUserIds.filter((id) => id !== userId));
    } else {
      setSelectedUserIds([...selectedUserIds, userId]);
    }
  };

  const handleDelete = async () => {
    setLoading(true);
    try {
      await onDelete(expense.id);
      onClose();
    } finally {
      setLoading(false);
    }
  };

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    if (!description.trim()) { setErrorMsg('Description is required.'); return; }
    if (amount <= 0) { setErrorMsg('Amount must be greater than zero.'); return; }

    let splits: SplitItem[] = [];

    if (splitStrategy === 'EQUAL') {
      if (selectedUserIds.length === 0) { setErrorMsg('Select at least one person.'); return; }
      const count = selectedUserIds.length;
      const base = Math.floor((amount / count) * 100) / 100;
      const rem = Math.round((amount - base * count) * 100) / 100;
      selectedUserIds.forEach((uid, i) => {
        splits.push({ user_id: uid, amount: i < rem * 100 ? base + 0.01 : base });
      });
    } else if (splitStrategy === 'EXACT') {
      if (Math.abs(exactSum - amount) > 0.01) {
        setErrorMsg(`Split amounts ($${exactSum.toFixed(2)}) must equal total ($${amount.toFixed(2)}).`);
        return;
      }
      group.members.forEach((m) => {
        const amt = parseFloat(exactAmounts[m.user_id]) || 0;
        if (amt > 0) splits.push({ user_id: m.user_id, amount: amt });
      });
    }

    setLoading(true);
    try {
      await onUpdate(expense.id, { description, amount, paid_by_id: paidById, split_strategy: splitStrategy, splits });
      setMode('view');
    } catch {
      setErrorMsg('Failed to update expense. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-content"
        onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: '520px', padding: 0, overflow: 'hidden' }}
      >
        {/* Header bar */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '20px 24px 16px',
          borderBottom: '1px solid var(--color-hairline)',
          background: isSettlement ? 'rgba(93,184,114,0.06)' : 'var(--color-surface-soft)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: '36px', height: '36px', borderRadius: 'var(--radius-md)',
              backgroundColor: isSettlement ? 'rgba(93,184,114,0.15)' : 'rgba(204,120,92,0.12)',
              color: isSettlement ? 'var(--color-success)' : 'var(--color-primary)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              {isSettlement ? <CreditCard size={18} /> : <Receipt size={18} />}
            </div>
            <div>
              <div style={{ fontSize: '11px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '1px', color: 'var(--color-muted)', marginBottom: '1px' }}>
                {isSettlement ? 'Settlement' : 'Expense'} · {group.name}
              </div>
              <div style={{ fontSize: '15px', fontWeight: 600, color: 'var(--color-ink)' }}>
                {mode === 'edit' ? 'Edit Expense' : expense.description}
              </div>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            {!isSettlement && mode === 'view' && (
              <button
                onClick={() => setMode('edit')}
                className="btn-icon-circular"
                title="Edit expense"
                style={{ color: 'var(--color-primary)' }}
              >
                <Pencil size={15} />
              </button>
            )}
            <button onClick={onClose} className="btn-icon-circular" title="Close">
              <X size={16} />
            </button>
          </div>
        </div>

        <div style={{ padding: '24px', maxHeight: '75vh', overflowY: 'auto' }}>
          {/* VIEW MODE */}
          {mode === 'view' && (
            <>
              {/* Big amount */}
              <div style={{ textAlign: 'center', marginBottom: '28px', padding: '20px 0' }}>
                <div className="font-mono" style={{
                  fontSize: '42px', fontWeight: 700, letterSpacing: '-1px',
                  color: isSettlement ? 'var(--color-success)' : 'var(--color-ink)',
                }}>
                  ${expense.amount.toFixed(2)}
                </div>
                <div style={{ fontSize: '13px', color: 'var(--color-muted)', marginTop: '4px' }}>
                  {expense.currency}
                </div>
              </div>

              {/* Meta row */}
              <div style={{
                display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '24px',
              }}>
                <div style={{
                  padding: '14px 16px', borderRadius: 'var(--radius-md)',
                  backgroundColor: 'var(--color-surface-soft)', border: '1px solid var(--color-hairline)',
                }}>
                  <div style={{ fontSize: '11px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.8px', color: 'var(--color-muted)', marginBottom: '6px' }}>
                    Paid by
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <div style={{
                      width: '24px', height: '24px', borderRadius: '50%',
                      backgroundColor: 'var(--color-primary)', color: '#fff',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: '11px', fontWeight: 700, flexShrink: 0,
                    }}>
                      {(expense.paid_by?.name || 'U').charAt(0)}
                    </div>
                    <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--color-ink)' }}>
                      {expense.paid_by?.name || getMemberName(expense.paid_by_id)}
                    </span>
                  </div>
                </div>

                <div style={{
                  padding: '14px 16px', borderRadius: 'var(--radius-md)',
                  backgroundColor: 'var(--color-surface-soft)', border: '1px solid var(--color-hairline)',
                }}>
                  <div style={{ fontSize: '11px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.8px', color: 'var(--color-muted)', marginBottom: '6px' }}>
                    Date
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Calendar size={14} style={{ color: 'var(--color-muted)' }} />
                    <span style={{ fontSize: '13px', color: 'var(--color-ink)' }}>{dateStr}</span>
                  </div>
                </div>
              </div>

              {/* Split strategy badge */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                <Users size={14} style={{ color: 'var(--color-muted)' }} />
                <span style={{ fontSize: '12px', color: 'var(--color-muted)' }}>Split method:</span>
                <span style={{
                  display: 'inline-flex', alignItems: 'center', padding: '3px 10px',
                  borderRadius: 'var(--radius-pill)', fontSize: '11px', fontWeight: 700,
                  textTransform: 'uppercase', letterSpacing: '0.8px',
                  backgroundColor: 'var(--color-surface-cream-strong)', color: 'var(--color-ink)',
                  border: '1px solid var(--color-hairline)',
                }}>
                  {expense.split_strategy}
                </span>
              </div>

              {/* Splits breakdown */}
              <div style={{ marginBottom: '24px' }}>
                <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-muted)', textTransform: 'uppercase', letterSpacing: '0.8px', marginBottom: '10px' }}>
                  Split Breakdown
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {expense.splits.map((split, idx) => {
                    const name = getMemberName(split.user_id);
                    const isPayer = split.user_id === expense.paid_by_id;
                    const pct = expense.amount > 0 ? ((split.amount || 0) / expense.amount * 100).toFixed(0) : '0';
                    return (
                      <div key={idx} style={{
                        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                        padding: '10px 14px', borderRadius: 'var(--radius-sm)',
                        backgroundColor: isPayer ? 'rgba(204,120,92,0.06)' : 'var(--color-canvas)',
                        border: `1px solid ${isPayer ? 'rgba(204,120,92,0.2)' : 'var(--color-hairline)'}`,
                      }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <div style={{
                            width: '28px', height: '28px', borderRadius: '50%',
                            backgroundColor: isPayer ? 'var(--color-primary)' : 'var(--color-surface-card)',
                            color: isPayer ? '#fff' : 'var(--color-ink)',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            fontSize: '11px', fontWeight: 700,
                          }}>
                            {name.charAt(0)}
                          </div>
                          <div>
                            <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-ink)' }}>{name}</span>
                            {isPayer && (
                              <span style={{ fontSize: '10px', color: 'var(--color-primary)', marginLeft: '6px', fontWeight: 600 }}>paid</span>
                            )}
                          </div>
                        </div>
                        <div style={{ textAlign: 'right' }}>
                          <div className="font-mono" style={{ fontSize: '14px', fontWeight: 700, color: 'var(--color-ink)' }}>
                            ${(split.amount || 0).toFixed(2)}
                          </div>
                          <div style={{ fontSize: '10px', color: 'var(--color-muted)' }}>{pct}%</div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Arrow from payer to others */}
              {!isSettlement && (
                <div style={{
                  display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap',
                  padding: '12px 14px', borderRadius: 'var(--radius-md)',
                  backgroundColor: 'rgba(204,120,92,0.06)', border: '1px solid rgba(204,120,92,0.15)',
                  marginBottom: '24px', fontSize: '13px', color: 'var(--color-muted)',
                }}>
                  <span style={{ fontWeight: 600, color: 'var(--color-ink)' }}>
                    {expense.paid_by?.name || getMemberName(expense.paid_by_id)}
                  </span>
                  <ArrowRight size={13} style={{ color: 'var(--color-primary)' }} />
                  <span>
                    will collect from {expense.splits.filter(s => s.user_id !== expense.paid_by_id).length} other{expense.splits.length > 2 ? 's' : ''}
                  </span>
                </div>
              )}

              {/* Delete section */}
              {!isSettlement && (
                confirmDelete ? (
                  <div style={{
                    padding: '16px', borderRadius: 'var(--radius-md)',
                    backgroundColor: 'rgba(198,69,69,0.06)', border: '1px solid rgba(198,69,69,0.2)',
                  }}>
                    <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--color-error)', marginBottom: '12px' }}>
                      Delete this expense permanently?
                    </div>
                    <p style={{ fontSize: '13px', color: 'var(--color-body)', marginBottom: '14px' }}>
                      This will remove <strong>"{expense.description}"</strong> and recalculate all balances.
                    </p>
                    <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                      <button onClick={() => setConfirmDelete(false)} className="btn btn-secondary" style={{ height: '32px' }}>
                        Keep it
                      </button>
                      <button
                        onClick={handleDelete}
                        disabled={loading}
                        className="btn"
                        style={{
                          height: '32px', backgroundColor: 'var(--color-error)',
                          color: '#fff', border: 'none',
                        }}
                      >
                        {loading ? 'Deleting…' : 'Yes, Delete'}
                      </button>
                    </div>
                  </div>
                ) : (
                  <button
                    onClick={() => setConfirmDelete(true)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: '6px',
                      width: '100%', padding: '10px 14px',
                      borderRadius: 'var(--radius-md)', cursor: 'pointer',
                      background: 'none', border: '1px dashed rgba(198,69,69,0.3)',
                      color: 'var(--color-error)', fontSize: '13px', fontWeight: 500,
                      transition: 'all 0.15s ease',
                    }}
                    onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'rgba(198,69,69,0.06)'; }}
                    onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'transparent'; }}
                  >
                    <Trash2 size={14} />
                    Delete this expense
                  </button>
                )
              )}
            </>
          )}

          {/* EDIT MODE */}
          {mode === 'edit' && (
            <form onSubmit={handleUpdate}>
              {errorMsg && (
                <div style={{
                  display: 'flex', alignItems: 'center', gap: '8px',
                  backgroundColor: 'rgba(198,69,69,0.1)', border: '1px solid var(--color-error)',
                  color: 'var(--color-error)', padding: '10px 14px',
                  borderRadius: 'var(--radius-md)', fontSize: '13px', marginBottom: '18px',
                }}>
                  <AlertCircle size={15} />
                  <span>{errorMsg}</span>
                </div>
              )}

              {/* Description */}
              <div className="form-group">
                <label className="form-label">Description</label>
                <input
                  type="text"
                  className="text-input"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  autoFocus
                />
              </div>

              {/* Amount & Paid By */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.4fr', gap: '14px', marginBottom: '18px' }}>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label">Amount ({group.currency})</label>
                  <div style={{ position: 'relative' }}>
                    <span style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--color-muted)', fontFamily: 'var(--font-mono)' }}>$</span>
                    <input
                      type="number" step="0.01" min="0.01"
                      className="text-input font-mono"
                      style={{ paddingLeft: '26px' }}
                      value={amountStr}
                      onChange={(e) => setAmountStr(e.target.value)}
                    />
                  </div>
                </div>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label">Paid by</label>
                  <select className="select-input" value={paidById} onChange={(e) => setPaidById(e.target.value)}>
                    {group.members.map((m) => (
                      <option key={m.user_id} value={m.user_id}>{m.user.name}</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Split Strategy */}
              <div style={{ marginBottom: '16px' }}>
                <label className="form-label" style={{ marginBottom: '8px', display: 'block' }}>Split Strategy</label>
                <div style={{
                  display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '4px',
                  backgroundColor: 'var(--color-surface-soft)', padding: '3px',
                  borderRadius: 'var(--radius-md)',
                }}>
                  {(['EQUAL', 'EXACT', 'PERCENTAGE', 'SHARE'] as SplitStrategy[]).map((strat) => (
                    <button
                      key={strat} type="button"
                      onClick={() => setSplitStrategy(strat)}
                      style={{
                        padding: '7px 4px', fontSize: '11px', fontWeight: 600,
                        border: 'none', borderRadius: 'var(--radius-sm)', cursor: 'pointer',
                        backgroundColor: splitStrategy === strat ? 'var(--color-canvas)' : 'transparent',
                        color: splitStrategy === strat ? 'var(--color-primary)' : 'var(--color-muted)',
                        boxShadow: splitStrategy === strat ? '0 1px 3px rgba(0,0,0,0.08)' : 'none',
                      }}
                    >
                      {strat}
                    </button>
                  ))}
                </div>
              </div>

              {/* Split sub-form */}
              <div style={{
                backgroundColor: 'var(--color-surface-card)', border: '1px solid var(--color-hairline)',
                borderRadius: 'var(--radius-md)', padding: '14px', marginBottom: '22px',
              }}>
                {splitStrategy === 'EQUAL' && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '7px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                      <span className="caption" style={{ color: 'var(--color-muted)' }}>Select who splits equally:</span>
                      {amount > 0 && selectedUserIds.length > 0 && (
                        <span className="caption font-mono" style={{ color: 'var(--color-primary)', fontWeight: 600 }}>
                          ${(amount / selectedUserIds.length).toFixed(2)} / person
                        </span>
                      )}
                    </div>
                    {group.members.map((m) => {
                      const isSelected = selectedUserIds.includes(m.user_id);
                      return (
                        <div
                          key={m.user_id}
                          onClick={() => toggleUserEqual(m.user_id)}
                          style={{
                            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                            padding: '8px 12px', borderRadius: 'var(--radius-sm)', cursor: 'pointer',
                            backgroundColor: 'var(--color-canvas)',
                            border: `1px solid ${isSelected ? 'var(--color-primary)' : 'var(--color-hairline)'}`,
                          }}
                        >
                          <span style={{ fontSize: '13px', fontWeight: 500 }}>{m.user.name}</span>
                          {isSelected
                            ? <CheckCircle2 size={16} style={{ color: 'var(--color-primary)' }} />
                            : <div style={{ width: '16px', height: '16px', borderRadius: '50%', border: '1.5px solid var(--color-hairline)' }} />
                          }
                        </div>
                      );
                    })}
                  </div>
                )}

                {splitStrategy === 'EXACT' && (
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                      <span className="caption" style={{ color: 'var(--color-muted)' }}>Exact amount per member:</span>
                      <span className="caption font-mono" style={{ color: Math.abs(exactSum - amount) <= 0.01 ? 'var(--color-success)' : 'var(--color-error)', fontWeight: 600 }}>
                        Remaining: ${(amount - exactSum).toFixed(2)}
                      </span>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {group.members.map((m) => (
                        <div key={m.user_id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                          <span style={{ fontSize: '13px' }}>{m.user.name}</span>
                          <div style={{ position: 'relative', width: '110px' }}>
                            <span style={{ position: 'absolute', left: '8px', top: '50%', transform: 'translateY(-50%)', color: 'var(--color-muted)', fontSize: '12px' }}>$</span>
                            <input
                              type="number" step="0.01" placeholder="0.00"
                              className="text-input font-mono"
                              style={{ height: '32px', paddingLeft: '20px', fontSize: '12px' }}
                              value={exactAmounts[m.user_id] || ''}
                              onChange={(e) => setExactAmounts({ ...exactAmounts, [m.user_id]: e.target.value })}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {(splitStrategy === 'PERCENTAGE' || splitStrategy === 'SHARE') && (
                  <p style={{ fontSize: '13px', color: 'var(--color-muted)', textAlign: 'center', padding: '8px 0' }}>
                    Switch to <strong>EQUAL</strong> or <strong>EXACT</strong> to edit splits interactively.
                  </p>
                )}
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px' }}>
                <button type="button" onClick={() => { setMode('view'); setErrorMsg(null); }} className="btn btn-secondary">
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={loading}>
                  {loading ? 'Saving…' : 'Save Changes'}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
