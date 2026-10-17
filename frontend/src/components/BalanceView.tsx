import { formatMoney } from '../utils/currency';
import React, { useState } from 'react';
import { ArrowRight, CheckCircle, RefreshCw } from 'lucide-react';
import type { Group, SettlementTransaction } from '../api/client';
import { SettlementHistory } from './SettlementHistory';

interface BalanceViewProps {
  group: Group;
  balances: Record<string, number>;
  simplifiedDebts: SettlementTransaction[];
  onSettle: (payerId: string, payeeId: string, amount: number, version: number, key: string) => Promise<void>;
  onRefresh: () => void;
}

export const BalanceView: React.FC<BalanceViewProps> = ({
  group,
  balances,
  simplifiedDebts,
  onSettle,
  onRefresh,
}) => {
  const [selectedSettlement, setSelectedSettlement] = useState<SettlementTransaction | null>(null);

  const [paymentAmount, setPaymentAmount] = useState('');
  const [paymentKey, setPaymentKey] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 1.3fr', gap: '24px', marginBottom: '32px' }}>
      {/* Column 1: Net Ledger Balances */}
      <div className="card-cream" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div>
            <span className="caption-uppercase" style={{ color: 'var(--color-muted)' }}>
              Group balances
            </span>
            <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '22px', marginTop: '2px' }}>
              Individual Balances
            </h3>
          </div>
          <button
            onClick={onRefresh}
            className="btn-icon-circular"
            title="Refresh balances"
            aria-label="Refresh balances"
          >
            <RefreshCw size={14} />
          </button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {group.members.map((m) => {
            const bal = balances[m.user_id] || 0;
            const isOwed = bal > 0.009;
            const owes = bal < -0.009;

            return (
              <div
                key={m.user_id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '12px 14px',
                  backgroundColor: 'var(--color-canvas)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--color-hairline)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <div
                    style={{
                      width: '32px',
                      height: '32px',
                      borderRadius: 'var(--radius-pill)',
                      backgroundColor: 'var(--color-surface-soft)',
                      color: 'var(--color-ink)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontWeight: 600,
                      fontSize: '13px',
                    }}
                  >
                    {(m.user?.name || 'M').charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <div style={{ fontSize: '14px', fontWeight: 500, color: 'var(--color-ink)' }}>
                      {m.user?.name || 'Member'}
                    </div>
                    <div className="caption" style={{ color: 'var(--color-muted-soft)' }}>
                      {m.user?.email || ''}
                    </div>
                  </div>
                </div>

                <div style={{ textAlign: 'right' }}>
                  <div
                    className="font-mono"
                    style={{
                      fontSize: '15px',
                      fontWeight: 600,
                      color: isOwed ? 'var(--color-success)' : owes ? 'var(--color-primary)' : 'var(--color-muted)',
                    }}
                  >
                    {isOwed ? `+${formatMoney(bal, group.currency)}` : formatMoney(bal, group.currency)}
                  </div>
                  <div className="caption" style={{ color: 'var(--color-muted)', fontSize: '11px' }}>
                    {isOwed ? 'gets back' : owes ? 'owes into pool' : 'settled'}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Column 2: Debt Simplification Engine (Greedy Net-Flow) */}
      <div className="card-cream" style={{ padding: '24px', position: 'relative' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div>
            <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '22px', marginTop: '4px' }}>
              Suggested payments
            </h3>
          </div>
          <span className="badge badge-cream">
            {simplifiedDebts.length} {simplifiedDebts.length === 1 ? 'transaction' : 'transactions'}
          </span>
        </div>

        {simplifiedDebts.length === 0 ? (
          <div
            style={{
              padding: '36px 20px',
              textAlign: 'center',
              backgroundColor: 'var(--color-canvas)',
              borderRadius: 'var(--radius-md)',
              border: '1px dashed var(--color-hairline)',
            }}
          >
            <CheckCircle size={32} style={{ color: 'var(--color-success)', margin: '0 auto 10px' }} />
            <div style={{ fontFamily: 'var(--font-display)', fontSize: '18px', color: 'var(--color-ink)' }}>
              All balances are fully settled!
            </div>
            <div className="caption" style={{ color: 'var(--color-muted)', marginTop: '4px' }}>
              No outstanding transactions remain in {group.name}.
            </div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {simplifiedDebts.map((tx, idx) => (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '12px 14px',
                  backgroundColor: 'var(--color-canvas)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--color-hairline)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ fontSize: '14px', fontWeight: 500, color: 'var(--color-ink)' }}>
                    {tx.from_user_name}
                  </span>
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      color: 'var(--color-primary)',
                      padding: '2px 8px',
                      backgroundColor: 'rgba(204, 120, 92, 0.08)',
                      borderRadius: 'var(--radius-pill)',
                      fontSize: '12px',
                    }}
                  >
                    <span>pays</span>
                    <ArrowRight size={13} />
                  </div>
                  <span style={{ fontSize: '14px', fontWeight: 500, color: 'var(--color-ink)' }}>
                    {tx.to_user_name}
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <span className="font-mono" style={{ fontSize: '16px', fontWeight: 600, color: 'var(--color-ink)' }}>
                    {formatMoney(tx.amount, group.currency)}
                  </span>
                  <button
                    onClick={() => { setSelectedSettlement(tx); setPaymentAmount(String(tx.amount)); setPaymentKey(crypto.randomUUID()); setError(''); }}
                    className="btn btn-secondary"
                    style={{ height: '30px', padding: '0 10px', fontSize: '12px' }}
                  >
                    Settle Up
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        <div
          style={{
            marginTop: '18px',
            padding: '12px',
            backgroundColor: 'var(--color-surface-soft)',
            borderRadius: 'var(--radius-md)',
            fontSize: '12px',
            color: 'var(--color-muted)',
            lineHeight: 1.5,
          }}
        >
          Pay the suggested amounts to settle your group’s balances.
        </div>
      </div>

      <SettlementHistory group={group} revision={simplifiedDebts} onRefresh={onRefresh} />

      {/* Settle Up Confirmation Modal */}
      {selectedSettlement && (
        <div className="modal-overlay" onClick={() => { if (!saving) setSelectedSettlement(null); }}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ padding: '28px' }}>
            <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '24px', marginBottom: '8px' }}>
              Confirm Settlement
            </h3>
            <p className="body-md" style={{ color: 'var(--color-body)', marginBottom: '20px' }}>
              Record transfer of{' '}
              <strong className="font-mono">{formatMoney(selectedSettlement.amount, group.currency)}</strong> from{' '}
              <strong>{selectedSettlement.from_user_name}</strong> to{' '}
              <strong>{selectedSettlement.to_user_name}</strong>?
            </p>

            <label>Payment amount (partial payments supported)
              <input aria-label="Payment amount" type="number" min="0.0001" step="0.0001"
                max={selectedSettlement.amount} value={paymentAmount} disabled={saving}
                onChange={e => { setPaymentAmount(e.target.value); setPaymentKey(crypto.randomUUID()); }} />
            </label>
            {error && <p role="alert">{error}</p>}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button disabled={saving} onClick={() => setSelectedSettlement(null)} className="btn btn-secondary">
                Cancel
              </button>
              <button
                disabled={saving}
                onClick={async () => {
                  const amount = Number(paymentAmount);
                  if (!Number.isFinite(amount) || amount <= 0 || amount > selectedSettlement.amount) {
                    setError('Enter a positive amount within the outstanding payment.'); return;
                  }
                  setSaving(true); setError('');
                  try {
                    await onSettle(selectedSettlement.from_user_id, selectedSettlement.to_user_id,
                      amount, selectedSettlement.version, paymentKey);
                    setSelectedSettlement(null);
                  } catch (err) {
                    setError(err instanceof Error ? err.message : 'Payment failed. Please retry.');
                    onRefresh();
                  } finally { setSaving(false); }
                }}
                className="btn btn-primary"
              >
                Confirm Settlement
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
