import React, { useState, useEffect } from 'react';
import { X, UserPlus, AlertCircle, Mail, User as UserIcon } from 'lucide-react';

interface AddMemberModalProps {
  isOpen: boolean;
  groupName: string;
  onClose: () => void;
  onSubmit: (name: string, email: string) => Promise<void>;
}

export const AddMemberModal: React.FC<AddMemberModalProps> = ({
  isOpen,
  groupName,
  onClose,
  onSubmit,
}) => {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setName('');
      setEmail('');
      setErrorMsg(null);
      setIsSubmitting(false);
    }
  }, [isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    if (!name.trim()) {
      setErrorMsg('Please enter a name.');
      return;
    }
    if (!email.trim() || !email.includes('@')) {
      setErrorMsg('Please enter a valid email address.');
      return;
    }

    setIsSubmitting(true);
    try {
      await onSubmit(name.trim(), email.trim().toLowerCase());
      onClose();
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to add member.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-content"
        onClick={(e) => e.stopPropagation()}
        style={{ padding: '32px', maxWidth: '460px' }}
      >
        {/* Header */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '20px',
          }}
        >
          <div>
            <span
              className="caption-uppercase"
              style={{ color: 'var(--color-primary)' }}
            >
              {groupName}
            </span>
            <h2
              style={{
                fontFamily: 'var(--font-display)',
                fontSize: '26px',
                marginTop: '2px',
              }}
            >
              Add New Member
            </h2>
          </div>
          <button
            onClick={onClose}
            className="btn-icon-circular"
            aria-label="Close modal"
          >
            <X size={18} />
          </button>
        </div>

        {/* Error Banner */}
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

        {/* Form */}
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">
              <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <UserIcon size={14} />
                Full Name
              </span>
            </label>
            <input
              type="text"
              className="text-input"
              placeholder="e.g. Alex Rivera"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoFocus
            />
          </div>

          <div className="form-group" style={{ marginBottom: '28px' }}>
            <label className="form-label">
              <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Mail size={14} />
                Email Address
              </span>
            </label>
            <input
              type="email"
              className="text-input"
              placeholder="e.g. alex@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
            <button
              type="button"
              onClick={onClose}
              className="btn btn-secondary"
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={isSubmitting}
              style={{ opacity: isSubmitting ? 0.7 : 1 }}
            >
              <UserPlus size={15} />
              <span>{isSubmitting ? 'Adding…' : 'Add Member'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
