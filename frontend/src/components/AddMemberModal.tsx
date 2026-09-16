import React, { useState, useEffect } from 'react';
import {
  X,
  UserPlus,
  AlertCircle,
  Mail,
  User as UserIcon,
  Send,
  Clock,
  Trash2,
  CheckCircle2,
  Sparkles,
  Copy,
  Check,
  AlertTriangle,
} from 'lucide-react';
import { api, type Invitation } from '../api/client';

interface AddMemberModalProps {
  isOpen: boolean;
  groupId: string;
  groupName: string;
  onClose: () => void;
  onSubmit: (name: string, email: string) => Promise<void>;
}

export const AddMemberModal: React.FC<AddMemberModalProps> = ({
  isOpen,
  groupId,
  groupName,
  onClose,
  onSubmit,
}) => {
  const [activeTab, setActiveTab] = useState<'invite' | 'quick'>('invite');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [sandboxNotice, setSandboxNotice] = useState<string | null>(null);
  const [recentInvite, setRecentInvite] = useState<Invitation | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [pendingInvites, setPendingInvites] = useState<Invitation[]>([]);

  const fetchPending = async () => {
    if (!groupId) return;
    try {
      const list = await api.getPendingInvitations(groupId);
      setPendingInvites(list);
    } catch {
      // ignore
    }
  };

  const copyToClipboard = async (text: string, id: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2500);
    } catch {
      // Fallback if browser permission is denied
    }
  };

  useEffect(() => {
    if (isOpen) {
      setName('');
      setEmail('');
      setErrorMsg(null);
      setSuccessMsg(null);
      setSandboxNotice(null);
      setRecentInvite(null);
      setCopiedId(null);
      setIsSubmitting(false);
      fetchPending();
    }
  }, [isOpen, groupId]);

  const handleSendInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setSuccessMsg(null);
    setSandboxNotice(null);

    if (!email.trim() || !email.includes('@')) {
      setErrorMsg('Please enter a valid email address.');
      return;
    }

    setIsSubmitting(true);
    try {
      const inv = await api.sendInvitation(groupId, email.trim().toLowerCase());
      setRecentInvite(inv);
      if (inv.email_dispatched) {
        setSuccessMsg(`Invitation email dispatched via Resend to ${inv.email}!`);
      } else {
        const notice =
          inv.delivery_status ||
          'Resend Sandbox Notice: Deliveries to unverified domains are restricted. Use the direct invite link below.';
        setSandboxNotice(notice);
      }
      setEmail('');
      await fetchPending();
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to send invitation.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleQuickAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setSuccessMsg(null);

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

  const handleCancelInvite = async (invitationId: string) => {
    try {
      await api.cancelInvitation(invitationId);
      setPendingInvites(pendingInvites.filter((i) => i.id !== invitationId));
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to cancel invitation.');
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-content"
        onClick={(e) => e.stopPropagation()}
        style={{ padding: '32px', maxWidth: '500px' }}
      >
        {/* Header */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '16px',
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
              Add Members
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

        {/* Tab Selector */}
        <div
          style={{
            display: 'flex',
            background: 'var(--color-surface-subtle, rgba(0,0,0,0.04))',
            padding: '4px',
            borderRadius: 'var(--radius-md, 12px)',
            marginBottom: '22px',
            gap: '4px',
          }}
        >
          <button
            type="button"
            onClick={() => { setActiveTab('invite'); setErrorMsg(null); setSuccessMsg(null); }}
            style={{
              flex: 1,
              padding: '8px 12px',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '13px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              background: activeTab === 'invite' ? 'var(--color-surface, #ffffff)' : 'transparent',
              color: activeTab === 'invite' ? 'var(--color-text)' : 'var(--color-text-secondary)',
              boxShadow: activeTab === 'invite' ? '0 2px 8px rgba(0,0,0,0.08)' : 'none',
              transition: 'all 0.15s ease',
            }}
          >
            <Send size={14} />
            <span>Email Invite (Resend)</span>
          </button>
          <button
            type="button"
            onClick={() => { setActiveTab('quick'); setErrorMsg(null); setSuccessMsg(null); }}
            style={{
              flex: 1,
              padding: '8px 12px',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '13px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              background: activeTab === 'quick' ? 'var(--color-surface, #ffffff)' : 'transparent',
              color: activeTab === 'quick' ? 'var(--color-text)' : 'var(--color-text-secondary)',
              boxShadow: activeTab === 'quick' ? '0 2px 8px rgba(0,0,0,0.08)' : 'none',
              transition: 'all 0.15s ease',
            }}
          >
            <UserPlus size={14} />
            <span>Instant Add</span>
          </button>
        </div>

        {/* Success Banner */}
        {successMsg && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              backgroundColor: 'rgba(52, 199, 89, 0.1)',
              border: '1px solid rgba(52, 199, 89, 0.3)',
              color: '#34c759',
              padding: '10px 14px',
              borderRadius: 'var(--radius-md)',
              fontSize: '14px',
              marginBottom: '18px',
            }}
          >
            <CheckCircle2 size={16} />
            <span>{successMsg}</span>
          </div>
        )}

        {/* Sandbox Notice Banner */}
        {sandboxNotice && (
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
              backgroundColor: 'rgba(255, 149, 0, 0.1)',
              border: '1px solid rgba(255, 149, 0, 0.3)',
              color: '#d97706',
              padding: '12px 14px',
              borderRadius: 'var(--radius-md)',
              fontSize: '13px',
              marginBottom: '18px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600 }}>
              <AlertTriangle size={16} />
              <span>Resend Testing Sandbox Active</span>
            </div>
            <p style={{ margin: 0, fontSize: '12px', lineHeight: 1.45, color: 'var(--color-text-secondary)' }}>
              {sandboxNotice.includes('tanaysinghyt119@gmail.com')
                ? 'Resend testing tier only delivers outbound emails to tanaysinghyt119@gmail.com until a custom domain is verified at resend.com/domains. You can share the instant direct invite link below!'
                : sandboxNotice}
            </p>
          </div>
        )}

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
              marginBottom: '18px',
            }}
          >
            <AlertCircle size={16} />
            <span>{errorMsg}</span>
          </div>
        )}

        {activeTab === 'invite' ? (
          /* Email Invite Tab */
          <div>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '8px 12px',
                borderRadius: '8px',
                background: 'rgba(0, 113, 227, 0.06)',
                border: '1px solid rgba(0, 113, 227, 0.15)',
                marginBottom: '18px',
              }}
            >
              <span style={{ fontSize: '13px', color: 'var(--color-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Sparkles size={14} />
                <span>Invites sent via <strong>Resend</strong></span>
              </span>
              <span style={{ fontSize: '11px', color: 'var(--color-text-secondary)' }}>Valid for 7 days</span>
            </div>

            <form onSubmit={handleSendInvite}>
              <div className="form-group" style={{ marginBottom: '22px' }}>
                <label className="form-label">
                  <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Mail size={14} />
                    Friend's Email Address
                  </span>
                </label>
                <input
                  type="email"
                  className="text-input"
                  placeholder="e.g. friend@gmail.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoFocus
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginBottom: recentInvite ? '16px' : '24px' }}>
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
                  <Send size={15} />
                  <span>{isSubmitting ? 'Sending…' : 'Send Invitation'}</span>
                </button>
              </div>
            </form>

            {/* Direct Link Card for Recent Invite */}
            {recentInvite && (
              <div
                style={{
                  background: 'var(--color-surface-subtle, rgba(0,0,0,0.03))',
                  border: '1px solid var(--color-border)',
                  borderRadius: 'var(--radius-md, 12px)',
                  padding: '14px',
                  marginBottom: '20px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.6px' }}>
                    Direct Invite Link
                  </span>
                  <span
                    style={{
                      fontSize: '11px',
                      fontWeight: 600,
                      padding: '2px 8px',
                      borderRadius: '999px',
                      backgroundColor: recentInvite.email_dispatched ? 'rgba(52, 199, 89, 0.15)' : 'rgba(255, 149, 0, 0.15)',
                      color: recentInvite.email_dispatched ? '#34c759' : '#d97706',
                    }}
                  >
                    {recentInvite.email_dispatched ? '✓ Emailed & Ready' : '📋 Link Ready'}
                  </span>
                </div>

                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <input
                    type="text"
                    readOnly
                    value={
                      recentInvite.invite_url ||
                      `${window.location.origin}/invite/accept?token=${recentInvite.token || ''}`
                    }
                    style={{
                      flex: 1,
                      fontSize: '12px',
                      padding: '8px 10px',
                      borderRadius: '8px',
                      border: '1px solid var(--color-border)',
                      background: 'var(--color-surface, #fff)',
                      color: 'var(--color-text)',
                      outline: 'none',
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => {
                      const link =
                        recentInvite.invite_url ||
                        `${window.location.origin}/invite/accept?token=${recentInvite.token || ''}`;
                      copyToClipboard(link, 'recent');
                    }}
                    className="btn btn-secondary"
                    style={{
                      padding: '8px 14px',
                      fontSize: '12px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      whiteSpace: 'nowrap',
                      backgroundColor: copiedId === 'recent' ? '#34c759' : undefined,
                      color: copiedId === 'recent' ? '#fff' : undefined,
                      borderColor: copiedId === 'recent' ? '#34c759' : undefined,
                      transition: 'all 0.15s ease',
                    }}
                  >
                    {copiedId === 'recent' ? <Check size={14} /> : <Copy size={14} />}
                    <span>{copiedId === 'recent' ? 'Copied!' : 'Copy Link'}</span>
                  </button>
                </div>
                <p style={{ margin: '8px 0 0 0', fontSize: '11px', color: 'var(--color-text-secondary)', lineHeight: 1.4 }}>
                  Anyone with this link can join <strong>{groupName}</strong> without waiting for an email.
                </p>
              </div>
            )}

            {/* Pending Invitations Section */}
            {pendingInvites.length > 0 && (
              <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: '18px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '10px' }}>
                  <Clock size={14} color="var(--color-text-secondary)" />
                  <span style={{ fontSize: '12px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px', color: 'var(--color-text-secondary)' }}>
                    Pending Invitations ({pendingInvites.length})
                  </span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '160px', overflowY: 'auto' }}>
                  {pendingInvites.map((inv) => (
                    <div
                      key={inv.id}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '8px 12px',
                        background: 'var(--color-surface-subtle, rgba(0,0,0,0.02))',
                        border: '1px solid var(--color-border)',
                        borderRadius: 'var(--radius-sm, 8px)',
                        fontSize: '13px',
                      }}
                    >
                      <div>
                        <div style={{ fontWeight: 500 }}>{inv.email}</div>
                        <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)' }}>
                          Sent {new Date(inv.created_at).toLocaleDateString()}
                        </div>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <button
                          type="button"
                          onClick={() => {
                            const link =
                              inv.invite_url ||
                              `${window.location.origin}/invite/accept?token=${inv.token || ''}`;
                            copyToClipboard(link, inv.id);
                          }}
                          className="btn-icon-circular"
                          style={{
                            width: '28px',
                            height: '28px',
                            color: copiedId === inv.id ? '#34c759' : 'var(--color-text-secondary)',
                          }}
                          title="Copy invitation link"
                          aria-label="Copy invitation link"
                        >
                          {copiedId === inv.id ? <Check size={13} /> : <Copy size={13} />}
                        </button>
                        <button
                          type="button"
                          onClick={() => handleCancelInvite(inv.id)}
                          className="btn-icon-circular"
                          style={{ width: '28px', height: '28px', color: 'var(--color-error)' }}
                          title="Revoke invitation"
                          aria-label="Revoke invitation"
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          /* Instant Add Tab */
          <form onSubmit={handleQuickAdd}>
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
        )}
      </div>
    </div>
  );
};
