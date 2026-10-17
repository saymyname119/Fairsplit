import React, { useState } from 'react';
import { API_BASE } from '../api/client';

export function PasswordRecovery({ token, onClose }: { token: string | null; onClose: () => void }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [done, setDone] = useState(false);
  const submit = async (event: React.FormEvent) => {
    event.preventDefault(); setError(''); setMessage('');
    if (token && password !== confirmation) { setError('Passwords must match.'); return; }
    setBusy(true);
    try {
      const response = await fetch(`${API_BASE}/auth/${token ? 'reset-password' : 'forgot-password'}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(token ? { token, password } : { email }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || (typeof data.detail === 'string' ? data.detail : 'Unable to reset password. Please try again.'));
      setMessage(data.message); setDone(true); setPassword(''); setConfirmation('');
    } catch (err) { setError(err instanceof Error ? err.message : 'Please try again.'); }
    finally { setBusy(false); }
  };
  return <div className="modal-overlay"><div className="modal-content" role="dialog" aria-modal="true" aria-label="Password recovery" style={{ padding: 32 }}>
    <h2>{token ? 'Choose a new password' : 'Forgot password?'}</h2>
    {error && <p role="alert" style={{ color: 'var(--color-error)' }}>{error}</p>}
    {message && <p role="status">{message}</p>}
    {!done && <form onSubmit={submit}>
      {token ? <>
        <label className="form-label" htmlFor="reset-password">New password</label>
        <input id="reset-password" className="text-input" type="password" autoComplete="new-password" minLength={8} maxLength={72} required value={password} onChange={e => setPassword(e.target.value)} />
        <label className="form-label" htmlFor="confirm-password">Confirm password</label>
        <input id="confirm-password" className="text-input" type="password" autoComplete="new-password" required value={confirmation} onChange={e => setConfirmation(e.target.value)} />
      </> : <>
        <p>Enter your account email to receive a reset link.</p>
        <label className="form-label" htmlFor="recovery-email">Email</label>
        <input id="recovery-email" className="text-input" type="email" autoComplete="email" required value={email} onChange={e => setEmail(e.target.value)} />
      </>}
      <button className="btn btn-primary" type="submit" disabled={busy}>{busy ? 'Please wait...' : token ? 'Update password' : 'Send reset link'}</button>
    </form>}
    <button className="btn btn-secondary" onClick={onClose} disabled={busy}>{done ? 'Back to sign in' : 'Cancel'}</button>
  </div></div>;
}
