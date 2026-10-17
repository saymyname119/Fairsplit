import { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { Group, SettlementTransaction } from '../api/client';

type Payment = Awaited<ReturnType<typeof api.getSettlementHistory>>[number];
export function SettlementHistory({ group, revision, onRefresh }: {
  group: Group; revision: SettlementTransaction[]; onRefresh: () => void;
}) {
  const [payments, setPayments] = useState<Payment[]>([]);
  const [error, setError] = useState('');
  const [notices, setNotices] = useState<Awaited<ReturnType<typeof api.getNotifications>>>([]);
  const [noticeError, setNoticeError] = useState('');
  const [pending, setPending] = useState<{ payment: Payment; version: number; key: string } | null>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    let active = true;
    api.getSettlementHistory(group.id).then(data => { if (active) setPayments(data); })
      .catch(err => { if (active) setError(err.message); });
    return () => { active = false; };
  }, [group.id, revision]);
  useEffect(() => {
    let active = true;
    const load = () => api.getNotifications(group.id).then(data => {
      if (active) { setNotices(data); setNoticeError(''); }
    }).catch(() => { if (active) setNoticeError('Updates are temporarily unavailable.'); });
    void load();
    const timer = window.setInterval(load, 10000);
    return () => { active = false; window.clearInterval(timer); };
  }, [group.id]);
  const name = (id: string) => group.members.find(m => m.user_id === id)?.user?.name || id;
  return <section className="card-cream" style={{ padding: 24, gridColumn: '1 / -1' }}>
    <h3>Payment history</h3>
    {error && <p role="alert">{error}</p>}
    {!payments.length && <p>No payments recorded yet.</p>}
    {payments.map(p => <div key={p.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0' }}>
      <span>{name(p.from_user_id)} → {name(p.to_user_id)} · {group.currency} {Number(p.amount).toFixed(2)}
        {p.reversal_of ? ' · reversal' : payments.some(r => r.reversal_of === p.id) ? ' · reversed' : ''}</span>
      {!p.reversal_of && !payments.some(r => r.reversal_of === p.id) && <button className="btn btn-secondary" disabled={busy}
        onClick={async () => {
          setBusy(true); setError('');
          try { setPending({ payment: p, version: await api.getBalanceVersion(group.id), key: crypto.randomUUID() }); }
          catch (err) { setError(err instanceof Error ? err.message : 'Could not load balances'); }
          finally { setBusy(false); }
        }}>Reverse</button>}
    </div>)}
    <h4>Recent updates</h4>
    {noticeError && <p role="status">{noticeError}</p>}
    {!notices.length && !noticeError && <p>No updates yet.</p>}
    {notices.slice(0, 5).map(n => <p key={n.id}><strong>{n.title}</strong> · {n.body}</p>)}
    {pending && <div role="dialog" aria-label="Reverse payment">
      <p>Reverse this payment of {group.currency} {Number(pending.payment.amount).toFixed(2)}? This restores the debt and keeps the original record.</p>
      <button className="btn btn-secondary" disabled={busy} onClick={() => setPending(null)}>Cancel</button>
      <button className="btn btn-primary" disabled={busy} onClick={async () => {
        setBusy(true); setError('');
        try {
          await api.reverseSettlement(group.id, pending.payment.id, pending.version, pending.key);
          setPending(null); onRefresh();
        } catch (err) { setError(err instanceof Error ? err.message : 'Reversal failed'); }
        finally { setBusy(false); }
      }}>Confirm reversal</button>
    </div>}
  </section>;
}
