import React, { useState } from 'react';
import { X, Key, Shield, UserPlus, LogIn, AlertCircle, CheckCircle2, Zap } from 'lucide-react';
import { api, type User, API_BASE } from '../api/client';
import { signInWithGoogle, signOutSupabase, isSupabaseConfigured } from '../utils/supabase';

interface AuthModalProps {
  isOpen: boolean;
  currentUser: User | null;
  supabaseSession?: import('../utils/supabase').Session | null;
  onClose: () => void;
  onSelectUser: (user: User | null) => void;
  onSupabaseLogout?: () => void;
}

type AuthMode = 'login' | 'signup';

export const AuthModal: React.FC<AuthModalProps> = ({
  isOpen,
  currentUser,
  supabaseSession,
  onClose,
  onSelectUser,
  onSupabaseLogout,
}) => {
  const [mode, setMode] = useState<AuthMode>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  if (!isOpen) return null;

  const resetForm = () => {
    setEmail('');
    setPassword('');
    setName('');
    setError('');
    setSuccess('');
  };

  const switchMode = (newMode: AuthMode) => {
    resetForm();
    setMode(newMode);
  };

  const loginWithCredentials = async (userEmail: string, userPass: string, userName?: string) => {
    setError('');
    setSuccess('');
    setLoading(true);
    try {
      let res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: userEmail, password: userPass }),
      });

      // If user doesn't exist yet, auto-register them
      if (!res.ok && res.status === 401 && userName) {
        const signupRes = await fetch(`${API_BASE}/users/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: userEmail, name: userName, password: userPass }),
        });
        if (signupRes.ok) {
          res = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: userEmail, password: userPass }),
          });
        }
      }

      if (!res.ok) {
        const errBody = await res.json().catch(() => null);
        throw new Error(errBody?.detail || `Login failed (${res.status})`);
      }

      const tokens = await res.json();
      api.setToken(tokens.access_token);
      localStorage.setItem('sw_refresh_token', tokens.refresh_token);

      const payload = JSON.parse(atob(tokens.access_token.split('.')[1]));
      let displayName = userName || userEmail.split('@')[0];

      try {
        const profileRes = await fetch(`${API_BASE}/users/${payload.sub}`, {
          headers: { Authorization: `Bearer ${tokens.access_token}` },
        });
        if (profileRes.ok) {
          const profile = await profileRes.json();
          if (profile?.name) displayName = profile.name;
        }
      } catch {
        // Fallback
      }

      const userData: User = {
        id: payload.sub,
        name: displayName,
        email: payload.email,
      };
      localStorage.setItem('sw_current_user', JSON.stringify(userData));
      onSelectUser(userData);

      setSuccess(`Signed in as ${displayName}!`);
      setTimeout(() => {
        resetForm();
        onClose();
      }, 500);
    } catch (err: any) {
      setError(err.message || 'Authentication failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!email || !password) {
      setError('Email and password are required.');
      return;
    }
    if (mode === 'signup' && !name) {
      setError('Name is required for registration.');
      return;
    }
    if (mode === 'signup' && password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }

    if (mode === 'signup') {
      setLoading(true);
      try {
        const signupRes = await fetch(`${API_BASE}/users/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, name, password }),
        });

        if (!signupRes.ok) {
          const errBody = await signupRes.json().catch(() => null);
          throw new Error(errBody?.detail || `Registration failed (${signupRes.status})`);
        }

        // Immediately log in
        await loginWithCredentials(email, password, name);
      } catch (err: any) {
        setError(err.message || 'Registration failed.');
        setLoading(false);
      }
    } else {
      await loginWithCredentials(email, password);
    }
  };

  const handleLogout = async () => {
    api.clearToken();
    localStorage.removeItem('sw_refresh_token');
    localStorage.removeItem('sw_current_user');
    if (supabaseSession) {
      try {
        await signOutSupabase();
      } catch (err) {
        console.warn('Supabase sign-out error:', err);
      }
      onSupabaseLogout?.();
    }
    onSelectUser(null);
    resetForm();
    onClose();
  };

  const isLoggedIn = api.hasToken() || !!supabaseSession;
  const hasSupabase = isSupabaseConfigured();

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ padding: '32px', maxWidth: '460px' }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Shield size={14} style={{ color: 'var(--color-primary)' }} />
              <span className="caption-uppercase" style={{ color: 'var(--color-primary)' }}>
                {isLoggedIn ? 'Active Session' : 'Authentication'}
              </span>
            </div>
            <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '26px', marginTop: '2px' }}>
              {isLoggedIn ? 'Account' : mode === 'login' ? 'Sign In' : 'Create Account'}
            </h2>
          </div>
          <button onClick={onClose} className="btn-icon-circular" aria-label="Close modal">
            <X size={18} />
          </button>
        </div>

        {/* If already logged in, show session info */}
        {isLoggedIn && currentUser && (
          <div style={{ marginBottom: '24px' }}>
            <div style={{
              padding: '16px',
              borderRadius: 'var(--radius-md)',
              backgroundColor: 'var(--color-surface-soft)',
              border: '1px solid var(--color-hairline)',
              marginBottom: '16px',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div style={{
                  width: '40px', height: '40px', borderRadius: '50%',
                  overflow: 'hidden',
                  backgroundColor: 'var(--color-primary)', color: '#fff',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: '16px', fontWeight: 700,
                }}>
                  {currentUser.avatar_url ? (
                    <img
                      src={currentUser.avatar_url}
                      alt={currentUser.name}
                      style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                      referrerPolicy="no-referrer"
                    />
                  ) : (
                    currentUser.name.charAt(0).toUpperCase()
                  )}
                </div>
                <div>
                  <div style={{ fontWeight: 600, fontSize: '15px', color: 'var(--color-ink)' }}>
                    {currentUser.name}
                  </div>
                  <div style={{ fontSize: '13px', color: 'var(--color-muted)' }}>
                    {currentUser.email}
                  </div>
                </div>
                <CheckCircle2 size={18} style={{ marginLeft: 'auto', color: '#22c55e' }} />
              </div>
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button onClick={onClose} className="btn btn-secondary">Close</button>
              <button
                onClick={() => {
                  if (supabaseSession && onSupabaseLogout) {
                    onSupabaseLogout();
                  } else {
                    handleLogout();
                  }
                }}
                className="btn btn-primary"
                style={{ backgroundColor: '#dc2626' }}
              >
                <LogIn size={14} />
                <span>Sign Out</span>
              </button>
            </div>
          </div>
        )}

        {/* Auth Form (only when not logged in) */}
        {!isLoggedIn && (
          <>
            {/* Quick 1-Click Demo Logins */}
            <div style={{
              marginBottom: '20px',
              padding: '12px 14px',
              borderRadius: 'var(--radius-md)',
              backgroundColor: 'var(--color-surface-card)',
              border: '1px dashed var(--color-hairline)',
            }}>
              <div style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                marginBottom: '8px',
              }}>
                <span className="caption-uppercase" style={{ color: 'var(--color-primary)', fontSize: '11px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Zap size={13} /> Quick Demo Login
                </span>
                <span style={{ fontSize: '11px', color: 'var(--color-muted)' }}>
                  1-click instant access
                </span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px' }}>
                <button
                  type="button"
                  disabled={loading}
                  onClick={() => loginWithCredentials('tanay@example.com', 'password123', 'Tanay')}
                  className="btn btn-secondary"
                  style={{ height: '32px', padding: '0 8px', fontSize: '12px', fontWeight: 600 }}
                  title="Sign in as Tanay"
                >
                  Tanay
                </button>
                <button
                  type="button"
                  disabled={loading}
                  onClick={() => loginWithCredentials('alex@example.com', 'password123', 'Alex')}
                  className="btn btn-secondary"
                  style={{ height: '32px', padding: '0 8px', fontSize: '12px', fontWeight: 600 }}
                  title="Sign in as Alex"
                >
                  Alex
                </button>
                <button
                  type="button"
                  disabled={loading}
                  onClick={() => loginWithCredentials('sam@example.com', 'password123', 'Sam')}
                  className="btn btn-secondary"
                  style={{ height: '32px', padding: '0 8px', fontSize: '12px', fontWeight: 600 }}
                  title="Sign in as Sam"
                >
                  Sam
                </button>
              </div>
            </div>

            {/* Google Sign-In Button */}
            <button
              type="button"
              disabled={googleLoading || loading}
              onClick={async () => {
                if (!hasSupabase) {
                  setError(
                    'Google Sign-In requires Supabase credentials in frontend/.env. Please use the Quick Demo buttons above or email sign-in / sign-up below.'
                  );
                  return;
                }
                setGoogleLoading(true);
                setError('');
                try {
                  await signInWithGoogle();
                } catch (err: any) {
                  setError(err.message || 'Google sign-in failed. Please try again.');
                  setGoogleLoading(false);
                }
              }}
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '12px',
                padding: '11px 20px',
                marginBottom: '16px',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--color-hairline)',
                backgroundColor: 'var(--color-canvas)',
                cursor: googleLoading ? 'wait' : 'pointer',
                fontSize: '13.5px',
                fontWeight: 600,
                fontFamily: 'var(--font-sans)',
                color: 'var(--color-ink)',
                transition: 'all 0.2s ease',
                boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
                opacity: googleLoading ? 0.7 : hasSupabase ? 1 : 0.85,
              }}
            >
              {googleLoading ? (
                <span style={{
                  width: '16px', height: '16px',
                  border: '2px solid var(--color-hairline)',
                  borderTop: '2px solid var(--color-primary)',
                  borderRadius: '50%',
                  animation: 'spin 0.8s linear infinite',
                  display: 'inline-block',
                }} />
              ) : (
                <svg width="17" height="17" viewBox="0 0 48 48">
                  <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
                  <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
                  <path fill="#FBBC05" d="M10.53 28.59a14.5 14.5 0 0 1 0-9.18l-7.98-6.19a24.08 24.08 0 0 0 0 21.56l7.98-6.19z"/>
                  <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
                </svg>
              )}
              <span>
                {googleLoading ? 'Redirecting to Google…' : hasSupabase ? 'Sign in with Google' : 'Sign in with Google (Requires Supabase)'}
              </span>
            </button>

            {/* Divider: or continue with email */}
            <div style={{ position: 'relative', textAlign: 'center', margin: '0 0 16px' }}>
              <hr style={{ border: 'none', borderTop: '1px solid var(--color-hairline)' }} />
              <span style={{
                position: 'absolute', top: '50%', left: '50%',
                transform: 'translate(-50%, -50%)',
                backgroundColor: 'var(--color-canvas)',
                padding: '0 12px', fontSize: '11px', color: 'var(--color-muted)',
                textTransform: 'uppercase', letterSpacing: '0.05em',
              }}>
                or email & password
              </span>
            </div>

            {/* Mode Tabs */}
            <div style={{
              display: 'flex', gap: '4px', marginBottom: '16px',
              backgroundColor: 'var(--color-surface-soft)',
              borderRadius: 'var(--radius-md)', padding: '4px',
            }}>
              <button
                type="button"
                onClick={() => switchMode('login')}
                style={{
                  flex: 1, padding: '8px 0', borderRadius: 'var(--radius-sm)',
                  border: 'none', cursor: 'pointer', fontSize: '13px', fontWeight: 600,
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
                  backgroundColor: mode === 'login' ? 'var(--color-canvas)' : 'transparent',
                  color: mode === 'login' ? 'var(--color-ink)' : 'var(--color-muted)',
                  boxShadow: mode === 'login' ? '0 1px 3px rgba(0,0,0,0.08)' : 'none',
                  transition: 'all 0.2s ease',
                }}
              >
                <LogIn size={14} /> Sign In
              </button>
              <button
                type="button"
                onClick={() => switchMode('signup')}
                style={{
                  flex: 1, padding: '8px 0', borderRadius: 'var(--radius-sm)',
                  border: 'none', cursor: 'pointer', fontSize: '13px', fontWeight: 600,
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
                  backgroundColor: mode === 'signup' ? 'var(--color-canvas)' : 'transparent',
                  color: mode === 'signup' ? 'var(--color-ink)' : 'var(--color-muted)',
                  boxShadow: mode === 'signup' ? '0 1px 3px rgba(0,0,0,0.08)' : 'none',
                  transition: 'all 0.2s ease',
                }}
              >
                <UserPlus size={14} /> Create Account
              </button>
            </div>

            {/* Error / Success messages */}
            {error && (
              <div style={{
                display: 'flex', alignItems: 'center', gap: '8px',
                padding: '10px 14px', marginBottom: '16px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'rgba(220, 38, 38, 0.08)',
                border: '1px solid rgba(220, 38, 38, 0.2)',
                color: '#dc2626', fontSize: '13px',
              }}>
                <AlertCircle size={16} />
                <span>{error}</span>
              </div>
            )}
            {success && (
              <div style={{
                display: 'flex', alignItems: 'center', gap: '8px',
                padding: '10px 14px', marginBottom: '16px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'rgba(34, 197, 94, 0.08)',
                border: '1px solid rgba(34, 197, 94, 0.2)',
                color: '#16a34a', fontSize: '13px',
              }}>
                <CheckCircle2 size={16} />
                <span>{success}</span>
              </div>
            )}

            {/* Form */}
            <form onSubmit={handleSubmit}>
              {mode === 'signup' && (
                <div className="form-group">
                  <label className="form-label">Full Name</label>
                  <input
                    type="text"
                    className="text-input"
                    placeholder="e.g. Tanay"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    disabled={loading}
                    autoComplete="name"
                  />
                </div>
              )}

              <div className="form-group">
                <label className="form-label">Email</label>
                <input
                  type="email"
                  className="text-input"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={loading}
                  autoComplete="email"
                />
              </div>

              <div className="form-group" style={{ marginBottom: '20px' }}>
                <label className="form-label">Password</label>
                <input
                  type="password"
                  className="text-input"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={loading}
                  autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
                />
                {mode === 'signup' && (
                  <span style={{ fontSize: '11px', color: 'var(--color-muted-soft)', marginTop: '4px', display: 'block' }}>
                    Minimum 8 characters
                  </span>
                )}
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                <button type="button" onClick={onClose} className="btn btn-secondary" disabled={loading}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={loading}>
                  {loading ? (
                    <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span className="spinner" style={{
                        width: '14px', height: '14px', border: '2px solid rgba(255,255,255,0.3)',
                        borderTop: '2px solid #fff', borderRadius: '50%',
                        animation: 'spin 0.8s linear infinite', display: 'inline-block',
                      }} />
                      {mode === 'signup' ? 'Creating…' : 'Signing in…'}
                    </span>
                  ) : (
                    <>
                      <Key size={14} />
                      <span>{mode === 'signup' ? 'Create Account' : 'Sign In'}</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </>
        )}
      </div>
    </div>
  );
};
