import React, { useState, useEffect } from 'react';
import { X, CheckCircle2, AlertCircle } from 'lucide-react';
import type { Group, SplitStrategy, SplitItem } from '../api/client';

interface ExpenseModalProps {
  group: Group;
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (expenseData: {
    description: string;
    amount: number;
    currency: string;
    paid_by_id: string;
    split_strategy: SplitStrategy;
    splits: SplitItem[];
  }) => Promise<void> | void;
}

export const ExpenseModal: React.FC<ExpenseModalProps> = ({
  group,
  isOpen,
  onClose,
  onSubmit,
}) => {
  const [description, setDescription] = useState('');
  const [amountStr, setAmountStr] = useState('');
  const [paidById, setPaidById] = useState(group.members[0]?.user_id || '');
  const [splitStrategy, setSplitStrategy] = useState<SplitStrategy>('EQUAL');

  // Equal strategy state: array of selected user IDs
  const [selectedUserIds, setSelectedUserIds] = useState<string[]>(
    group.members.map((m) => m.user_id)
  );

  // Exact amounts mapping
  const [exactAmounts, setExactAmounts] = useState<Record<string, string>>({});

  // Percentages mapping
  const [percentages, setPercentages] = useState<Record<string, string>>({});

  // Shares mapping
  const [shares, setShares] = useState<Record<string, string>>({});

  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Reset form fields when modal opens
  useEffect(() => {
    if (isOpen) {
      setDescription('');
      setAmountStr('');
      setIsSubmitting(false);
      setPaidById(group.members[0]?.user_id || '');
      setSplitStrategy('EQUAL');
      setSelectedUserIds(group.members.map((m) => m.user_id));
      setExactAmounts({});
      setPercentages({});
      setShares({});
      setErrorMsg(null);
    }
  }, [isOpen, group]);

  const amount = parseFloat(amountStr) || 0;

  // Sync default values when splitStrategy changes
  useEffect(() => {
    if (splitStrategy === 'PERCENTAGE') {
      const count = group.members.length;
      const initial: Record<string, string> = {};
      const share = (100 / count).toFixed(1);
      group.members.forEach((m) => {
        initial[m.user_id] = share;
      });
      setPercentages(initial);
    } else if (splitStrategy === 'SHARE') {
      const initial: Record<string, string> = {};
      group.members.forEach((m) => {
        initial[m.user_id] = '1';
      });
      setShares(initial);
    }
  }, [splitStrategy, group.members]);


  const toggleUserEqual = (userId: string) => {
    if (selectedUserIds.includes(userId)) {
      if (selectedUserIds.length > 1) {
        setSelectedUserIds(selectedUserIds.filter((id) => id !== userId));
      }
    } else {
      setSelectedUserIds([...selectedUserIds, userId]);
    }
  };

  const handleExactChange = (userId: string, val: string) => {
    setExactAmounts({ ...exactAmounts, [userId]: val });
  };

  const handlePercentageChange = (userId: string, val: string) => {
    setPercentages({ ...percentages, [userId]: val });
  };

  const handleShareChange = (userId: string, val: string) => {
    setShares({ ...shares, [userId]: val });
  };

  // Validation calculation
  const exactSum = Object.values(exactAmounts).reduce(
    (sum, v) => sum + (parseFloat(v) || 0),
    0
  );
  const percentageSum = Object.values(percentages).reduce(
    (sum, v) => sum + (parseFloat(v) || 0),
    0
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    if (!description.trim()) {
      setErrorMsg('Please enter an expense description.');
      return;
    }
    if (amount <= 0) {
      setErrorMsg('Please enter a valid amount greater than zero.');
      return;
    }

    const splits: SplitItem[] = [];

    if (splitStrategy === 'EQUAL') {
      if (selectedUserIds.length === 0) {
        setErrorMsg('Please select at least one person to split with.');
        return;
      }
      const count = selectedUserIds.length;
      const baseSplit = Math.floor((amount / count) * 100) / 100;
      let remainder = Math.round((amount - baseSplit * count) * 100) / 100;

      selectedUserIds.forEach((uid, index) => {
        // distribute 1-cent remainder to the first debtors
        const itemAmount = index < remainder * 100 ? baseSplit + 0.01 : baseSplit;
        splits.push({ user_id: uid, amount: itemAmount });
      });
    } else if (splitStrategy === 'EXACT') {
      if (Math.abs(exactSum - amount) > 0.01) {
        setErrorMsg(`Sum of split amounts ($${exactSum.toFixed(2)}) must equal total ($${amount.toFixed(2)}).`);
        return;
      }
      group.members.forEach((m) => {
        const amt = parseFloat(exactAmounts[m.user_id]) || 0;
        if (amt > 0) {
          splits.push({ user_id: m.user_id, amount: amt });
        }
      });
    } else if (splitStrategy === 'PERCENTAGE') {
      if (Math.abs(percentageSum - 100) > 0.1) {
        setErrorMsg(`Percentages must sum to 100% (currently ${percentageSum.toFixed(1)}%).`);
        return;
      }
      group.members.forEach((m) => {
        const pct = parseFloat(percentages[m.user_id]) || 0;
        if (pct > 0) {
          const itemAmt = Math.round(((amount * pct) / 100) * 100) / 100;
          splits.push({ user_id: m.user_id, amount: itemAmt, percentage: pct });
        }
      });
    } else if (splitStrategy === 'SHARE') {
      const totalShares = Object.values(shares).reduce((sum, v) => sum + (parseFloat(v) || 0), 0);
      if (totalShares <= 0) {
        setErrorMsg('Total shares must be greater than zero.');
        return;
      }
      group.members.forEach((m) => {
        const sh = parseFloat(shares[m.user_id]) || 0;
        if (sh > 0) {
          const itemAmt = Math.round(((amount * sh) / totalShares) * 100) / 100;
          splits.push({ user_id: m.user_id, amount: itemAmt, share: sh });
        }
      });
    }

    setIsSubmitting(true);
    try {
      await onSubmit({
        description,
        amount,
        currency: group.currency,
        paid_by_id: paidById,
        split_strategy: splitStrategy,
        splits,
      });
      onClose();
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to record expense. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ padding: '32px' }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
          <div>
            <span className="caption-uppercase" style={{ color: 'var(--color-primary)' }}>
              {group.name}
            </span>
            <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '26px', marginTop: '2px' }}>
              Add an Expense
            </h2>
          </div>
          <button onClick={onClose} className="btn-icon-circular" aria-label="Close modal">
            <X size={18} />
          </button>
        </div>

        {errorMsg && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              backgroundColor: 'rgba(198, 69, 69, 0.1)',
              border: '1px solid var(--color-error)',
              color: 'var(--color-error)',
              padding: '10px 14px',
              borderRadius: 'var(--radius-md)',
              fontSize: '14px',
              marginBottom: '20px',
            }}
          >
            <AlertCircle size={16} />
            <span>{errorMsg}</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          {/* Description */}
          <div className="form-group">
            <label className="form-label">Expense Description</label>
            <input
              type="text"
              className="text-input"
              placeholder="e.g. Dinner, Groceries, Hotel booking"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              autoFocus
            />
          </div>

          {/* Amount & Paid By Row */}
          <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1.5fr', gap: '16px', marginBottom: '20px' }}>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label">Total Amount ({group.currency})</label>
              <div style={{ position: 'relative' }}>
                <span
                  style={{
                    position: 'absolute',
                    left: '12px',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    color: 'var(--color-muted)',
                    fontFamily: 'var(--font-mono)',
                  }}
                >
                  $
                </span>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  className="text-input font-mono"
                  placeholder="0.00"
                  style={{ paddingLeft: '28px' }}
                  value={amountStr}
                  onChange={(e) => setAmountStr(e.target.value)}
                />
              </div>
            </div>

            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label">Paid by</label>
              <select
                className="select-input"
                value={paidById}
                onChange={(e) => setPaidById(e.target.value)}
              >
                {group.members.map((m) => (
                  <option key={m.user_id} value={m.user_id}>
                    {m.user.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Split Strategy Tabs */}
          <div style={{ marginBottom: '18px' }}>
            <label className="form-label" style={{ marginBottom: '8px', display: 'block' }}>
              Split Strategy
            </label>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(4, 1fr)',
                gap: '6px',
                backgroundColor: 'var(--color-surface-soft)',
                padding: '4px',
                borderRadius: 'var(--radius-md)',
              }}
            >
              {(['EQUAL', 'EXACT', 'PERCENTAGE', 'SHARE'] as SplitStrategy[]).map((strat) => (
                <button
                  key={strat}
                  type="button"
                  onClick={() => setSplitStrategy(strat)}
                  style={{
                    padding: '8px 4px',
                    fontSize: '12px',
                    fontWeight: 600,
                    border: 'none',
                    borderRadius: 'var(--radius-sm)',
                    cursor: 'pointer',
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

          {/* Dynamic Strategy Sub-Forms */}
          <div
            style={{
              backgroundColor: 'var(--color-surface-card)',
              border: '1px solid var(--color-hairline)',
              borderRadius: 'var(--radius-md)',
              padding: '16px',
              marginBottom: '24px',
            }}
          >
            {splitStrategy === 'EQUAL' && (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                  <span className="caption" style={{ color: 'var(--color-body)' }}>
                    Split equally among ({selectedUserIds.length} people):
                  </span>
                  <span className="caption font-mono" style={{ color: 'var(--color-primary)', fontWeight: 600 }}>
                    {amount > 0 && selectedUserIds.length > 0
                      ? `$${(amount / selectedUserIds.length).toFixed(2)} / person`
                      : '$0.00 / person'}
                  </span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {group.members.map((m) => {
                    const isSelected = selectedUserIds.includes(m.user_id);
                    return (
                      <div
                        key={m.user_id}
                        onClick={() => toggleUserEqual(m.user_id)}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          padding: '8px 12px',
                          backgroundColor: 'var(--color-canvas)',
                          borderRadius: 'var(--radius-sm)',
                          cursor: 'pointer',
                          border: isSelected ? '1px solid var(--color-primary)' : '1px solid var(--color-hairline)',
                        }}
                      >
                        <span style={{ fontSize: '14px', fontWeight: 500, color: 'var(--color-ink)' }}>
                          {m.user.name}
                        </span>
                        {isSelected ? (
                          <CheckCircle2 size={18} style={{ color: 'var(--color-primary)' }} />
                        ) : (
                          <div
                            style={{
                              width: '18px',
                              height: '18px',
                              borderRadius: '50%',
                              border: '1px solid var(--color-hairline)',
                            }}
                          />
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {splitStrategy === 'EXACT' && (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
                  <span className="caption" style={{ color: 'var(--color-body)' }}>
                    Specify exact amount per member:
                  </span>
                  <span
                    className="caption font-mono"
                    style={{
                      color: Math.abs(exactSum - amount) <= 0.01 ? 'var(--color-success)' : 'var(--color-error)',
                      fontWeight: 600,
                    }}
                  >
                    Remaining: ${(amount - exactSum).toFixed(2)}
                  </span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {group.members.map((m) => (
                    <div
                      key={m.user_id}
                      style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
                    >
                      <span style={{ fontSize: '14px', color: 'var(--color-ink)' }}>{m.user.name}</span>
                      <div style={{ position: 'relative', width: '120px' }}>
                        <span
                          style={{
                            position: 'absolute',
                            left: '8px',
                            top: '50%',
                            transform: 'translateY(-50%)',
                            color: 'var(--color-muted)',
                            fontSize: '13px',
                          }}
                        >
                          $
                        </span>
                        <input
                          type="number"
                          step="0.01"
                          placeholder="0.00"
                          className="text-input font-mono"
                          style={{ height: '34px', paddingLeft: '22px', fontSize: '13px' }}
                          value={exactAmounts[m.user_id] || ''}
                          onChange={(e) => handleExactChange(m.user_id, e.target.value)}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {splitStrategy === 'PERCENTAGE' && (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
                  <span className="caption" style={{ color: 'var(--color-body)' }}>
                    Specify percentage per member:
                  </span>
                  <span
                    className="caption font-mono"
                    style={{
                      color: Math.abs(percentageSum - 100) < 0.1 ? 'var(--color-success)' : 'var(--color-error)',
                      fontWeight: 600,
                    }}
                  >
                    Total: {percentageSum.toFixed(1)}% / 100%
                  </span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {group.members.map((m) => (
                    <div
                      key={m.user_id}
                      style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
                    >
                      <span style={{ fontSize: '14px', color: 'var(--color-ink)' }}>{m.user.name}</span>
                      <div style={{ position: 'relative', width: '100px' }}>
                        <input
                          type="number"
                          step="0.1"
                          placeholder="0.0"
                          className="text-input font-mono"
                          style={{ height: '34px', paddingRight: '22px', fontSize: '13px' }}
                          value={percentages[m.user_id] || ''}
                          onChange={(e) => handlePercentageChange(m.user_id, e.target.value)}
                        />
                        <span
                          style={{
                            position: 'absolute',
                            right: '8px',
                            top: '50%',
                            transform: 'translateY(-50%)',
                            color: 'var(--color-muted)',
                            fontSize: '13px',
                          }}
                        >
                          %
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {splitStrategy === 'SHARE' && (
              <div>
                <div style={{ marginBottom: '12px' }}>
                  <span className="caption" style={{ color: 'var(--color-body)' }}>
                    Enter proportion share ratios (e.g., 1 share, 2 shares):
                  </span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {group.members.map((m) => (
                    <div
                      key={m.user_id}
                      style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
                    >
                      <span style={{ fontSize: '14px', color: 'var(--color-ink)' }}>{m.user.name}</span>
                      <div style={{ width: '80px' }}>
                        <input
                          type="number"
                          step="1"
                          min="0"
                          className="text-input font-mono"
                          style={{ height: '34px', fontSize: '13px' }}
                          value={shares[m.user_id] || '1'}
                          onChange={(e) => handleShareChange(m.user_id, e.target.value)}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
            <button type="button" onClick={onClose} disabled={isSubmitting} className="btn btn-secondary">
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={isSubmitting}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}
            >
              {isSubmitting ? (
                <>
                  <span
                    style={{
                      width: '14px',
                      height: '14px',
                      border: '2px solid rgba(255,255,255,0.4)',
                      borderTop: '2px solid #fff',
                      borderRadius: '50%',
                      animation: 'spin 0.8s linear infinite',
                      display: 'inline-block',
                    }}
                  />
                  <span>Saving...</span>
                </>
              ) : (
                <span>Confirm & Save Expense</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
