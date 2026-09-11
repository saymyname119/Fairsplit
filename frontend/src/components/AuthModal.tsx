import React, { useState } from 'react';
import { X, Key, Shield } from 'lucide-react';
import { type User, SEED_USERS } from '../api/client';

interface AuthModalProps {
  isOpen: boolean;
  currentUser: User | null;
  onClose: () => void;
  onSelectUser: (user: User) => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({
  isOpen,
  currentUser,
  onClose,
  onSelectUser,
}) => {
  if (!isOpen) return null;

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleManualLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;
    const existing = SEED_USERS.find((u) => u.email.toLowerCase() === email.toLowerCase());
    if (existing) {
      onSelectUser(existing);
    } else {
      const newUser: User = {
        id: 'usr_' + Math.random().toString(36).substring(2, 7),
        name: email.split('@')[0],
        email,
      };
      onSelectUser(newUser);
    }
    onClose();
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ padding: '32px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Shield size={14} style={{ color: 'var(--color-primary)' }} />
              <span className="caption-uppercase" style={{ color: 'var(--color-primary)' }}>
                JWT Authentication
              </span>
            </div>
            <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '26px', marginTop: '2px' }}>
              Identity & Session
            </h2>
          </div>
          <button onClick={onClose} className="btn-icon-circular" aria-label="Close modal">
            <X size={18} />
          </button>
        </div>

        {/* Fast profile switcher */}
        <div style={{ marginBottom: '24px' }}>
          <label className="form-label" style={{ marginBottom: '10px', display: 'block' }}>
            Switch Active Persona (Instant Demo)
          </label>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
            {SEED_USERS.map((user) => {
              const isSelected = currentUser?.id === user.id;
              return (
                <button
                  key={user.id}
                  type="button"
                  onClick={() => {
                    onSelectUser(user);
                    onClose();
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    padding: '10px',
                    borderRadius: 'var(--radius-md)',
                    border: isSelected ? '2px solid var(--color-primary)' : '1px solid var(--color-hairline)',
                    backgroundColor: isSelected ? 'var(--color-surface-soft)' : 'var(--color-canvas)',
                    cursor: 'pointer',
                    textAlign: 'left',
                  }}
                >
                  <div
                    style={{
                      width: '28px',
                      height: '28px',
                      borderRadius: '50%',
                      backgroundColor: isSelected ? 'var(--color-primary)' : 'var(--color-surface-card)',
                      color: isSelected ? '#ffffff' : 'var(--color-ink)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '12px',
                      fontWeight: 600,
                    }}
                  >
                    {user.name.charAt(0)}
                  </div>
                  <div>
                    <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-ink)' }}>
                      {user.name}
                    </div>
                    <div className="caption" style={{ color: 'var(--color-muted-soft)', fontSize: '11px' }}>
                      {user.email}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        <div style={{ position: 'relative', textAlign: 'center', margin: '20px 0' }}>
          <hr style={{ border: 'none', borderTop: '1px solid var(--color-hairline)' }} />
          <span
            style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              backgroundColor: 'var(--color-canvas)',
              padding: '0 12px',
              fontSize: '12px',
              color: 'var(--color-muted)',
            }}
          >
            or sign in with password
          </span>
        </div>

        {/* Standard credentials form */}
        <form onSubmit={handleManualLogin}>
          <div className="form-group">
            <label className="form-label">Email</label>
            <input
              type="email"
              className="text-input"
              placeholder="claude@anthropic.internal"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>

          <div className="form-group" style={{ marginBottom: '24px' }}>
            <label className="form-label">Password</label>
            <input
              type="password"
              className="text-input"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
            <button type="button" onClick={onClose} className="btn btn-secondary">
              Cancel
            </button>
            <button type="submit" className="btn btn-primary">
              <Key size={14} />
              <span>Authenticate</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
