import React, { useState } from 'react';
import { ArrowRight, CheckCircle, RefreshCw, Zap } from 'lucide-react';
import type { Group, SettlementTransaction } from '../api/client';

interface BalanceViewProps {
  group: Group;
  balances: Record<string, number>;
  simplifiedDebts: SettlementTransaction[];
  onSettle: (payerId: string, payeeId: string, amount: number) => void;
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

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 1.3fr', gap: '24px', marginBottom: '32px' }}>
      {/* Column 1: Net Ledger Balances */}
      <div className="card-cream" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div>
            <span className="caption-uppercase" style={{ color: 'var(--color-muted)' }}>
              Group Net Flow
            </span>
            <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '22px', marginTop: '2px' }}>
              Individual Balances
            </h3>
          </div>
          <button
            onClick={onRefresh}
            className="btn-icon-circular"
            title="Refresh Ledger Cache"
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
                    {m.user.name.charAt(0)}
                  </div>
                  <div>
                    <div style={{ fontSize: '14px', fontWeight: 500, color: 'var(--color-ink)' }}>
                      {m.user.name}
                    </div>
                    <div className="caption" style={{ color: 'var(--color-muted-soft)' }}>
                      {m.user.email}
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
                    {isOwed ? `+$${bal.toFixed(2)}` : owes ? `-$${Math.abs(bal).toFixed(2)}` : '$0.00'}
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
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
              <span className="badge badge-amber font-mono" style={{ fontSize: '10px' }}>
                <Zap size={11} />
                GREEDY NET-FLOW
              </span>
              <span className="caption" style={{ color: 'var(--color-muted)', fontSize: '12px' }}>
                O(N log N)
              </span>
            </div>
            <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '22px', marginTop: '4px' }}>
              Simplified Settlement Plan
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
                    ${tx.amount.toFixed(2)}
                  </span>
                  <button
                    onClick={() => setSelectedSettlement(tx)}
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
          💡 <strong>Why simplification?</strong> Instead of everyone paying everyone back for each individual receipt,
          our algorithm collapses all cyclic debts into the absolute minimum number of direct wire transfers.
        </div>
      </div>

      {/* Settle Up Confirmation Modal */}
      {selectedSettlement && (
        <div className="modal-overlay" onClick={() => setSelectedSettlement(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ padding: '28px' }}>
            <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '24px', marginBottom: '8px' }}>
              Confirm Settlement
            </h3>
            <p className="body-md" style={{ color: 'var(--color-body)', marginBottom: '20px' }}>
              Record transfer of{' '}
              <strong className="font-mono">${selectedSettlement.amount.toFixed(2)}</strong> from{' '}
              <strong>{selectedSettlement.from_user_name}</strong> to{' '}
              <strong>{selectedSettlement.to_user_name}</strong>?
            </p>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button onClick={() => setSelectedSettlement(null)} className="btn btn-secondary">
                Cancel
              </button>
              <button
                onClick={() => {
                  onSettle(
                    selectedSettlement.from_user_id,
                    selectedSettlement.to_user_id,
                    selectedSettlement.amount
                  );
                  setSelectedSettlement(null);
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
