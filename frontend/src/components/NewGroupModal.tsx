import React, { useState } from 'react';
import { X, Users, AlertCircle } from 'lucide-react';

interface NewGroupModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (name: string, currency: string) => void;
}

export const NewGroupModal: React.FC<NewGroupModalProps> = ({ isOpen, onClose, onSubmit }) => {
  if (!isOpen) return null;

  const [name, setName] = useState('');
  const [currency, setCurrency] = useState('USD');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setErrorMsg('Please enter a group name.');
      return;
    }
    onSubmit(name.trim(), currency);
    onClose();
  };

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
              autoFocus
            />
          </div>

          <div className="form-group" style={{ marginBottom: '28px' }}>
            <label className="form-label">Default Currency</label>
            <select
              className="select-input font-mono"
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
            >
              <option value="USD">USD — United States Dollar ($)</option>
              <option value="EUR">EUR — Euro (€)</option>
              <option value="GBP">GBP — British Pound (£)</option>
              <option value="JPY">JPY — Japanese Yen (¥)</option>
              <option value="INR">INR — Indian Rupee (₹)</option>
            </select>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
            <button type="button" onClick={onClose} className="btn btn-secondary">
              Cancel
            </button>
            <button type="submit" className="btn btn-primary">
              <Users size={15} />
              <span>Create Group</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
