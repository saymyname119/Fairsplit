import React, { useState, useEffect } from 'react';
import { X, Users, AlertCircle, LogIn } from 'lucide-react';
import type { User } from '../api/client';

interface NewGroupModalProps {
  isOpen: boolean;
  currentUser?: User | null;
  onOpenAuth?: () => void;
  onClose: () => void;
  onSubmit: (name: string, currency: string) => Promise<void> | void;
}

export const NewGroupModal: React.FC<NewGroupModalProps> = ({
  isOpen,
  currentUser,
  onOpenAuth,
  onClose,
  onSubmit,
}) => {
  const [name, setName] = useState('');
  const [currency, setCurrency] = useState('USD');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setName('');
      setCurrency('USD');
      setErrorMsg(null);
      setIsSubmitting(false);
    }
  }, [isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setErrorMsg('Please enter a group name.');
      return;
    }
    if (!currentUser) {
      setErrorMsg('You must be signed in to create a group.');
      if (onOpenAuth) onOpenAuth();
      return;
    }

    setIsSubmitting(true);
    setErrorMsg(null);
    try {
      await onSubmit(name.trim(), currency);
      onClose();
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to create group. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ padding: '32px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <div>
            <span className="caption-uppercase" style={{ color: 'var(--color-primary)' }}>
              New Ledger
            </span>
            <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '26px', marginTop: '2px' }}>
              Create Shared Group
            </h2>
          </div>
          <button onClick={onClose} className="btn-icon-circular" aria-label="Close modal">
            <X size={18} />
          </button>
        </div>

        {/* Not logged in banner */}
        {!currentUser && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '12px',
              backgroundColor: 'rgba(217, 119, 6, 0.1)',
              border: '1px solid rgba(217, 119, 6, 0.3)',
              padding: '12px 14px',
              borderRadius: 'var(--radius-md)',
              marginBottom: '20px',
            }}
          >
            <div style={{ fontSize: '13px', color: '#b45309' }}>
              <strong>Sign in required:</strong> You must be signed in to create and manage group ledgers.
            </div>
            {onOpenAuth && (
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => {
                  onClose();
                  onOpenAuth();
                }}
                style={{ height: '30px', padding: '0 12px', fontSize: '12px', whiteSpace: 'nowrap' }}
              >
                <LogIn size={13} />
                <span>Sign In</span>
              </button>
            )}
          </div>
        )}

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
          <div className="form-group">
            <label className="form-label">Group Name</label>
            <input
              type="text"
              className="text-input"
              placeholder="e.g. Iceland Roadtrip, Apartment 3B, Dinner Club"
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={isSubmitting}
              autoFocus
            />
          </div>

          <div className="form-group" style={{ marginBottom: '28px' }}>
            <label className="form-label">Default Currency</label>
            <select
              className="select-input font-mono"
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
              disabled={isSubmitting}
            >
              <option value="USD">USD — United States Dollar ($)</option>
              <option value="EUR">EUR — Euro (€)</option>
              <option value="GBP">GBP — British Pound (£)</option>
              <option value="JPY">JPY — Japanese Yen (¥)</option>
              <option value="INR">INR — Indian Rupee (₹)</option>
            </select>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
            <button type="button" onClick={onClose} disabled={isSubmitting} className="btn btn-secondary">
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={isSubmitting || !name.trim()}
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
                  <span>Creating...</span>
                </>
              ) : (
                <>
                  <Users size={15} />
                  <span>Create Group</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
