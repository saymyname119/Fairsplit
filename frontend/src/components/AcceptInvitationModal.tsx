import React, { useState, useEffect } from 'react';
import { CheckCircle2, AlertCircle, Users, ArrowRight, Loader2, X } from 'lucide-react';
import { api, type InvitationInfo } from '../api/client';

interface AcceptInvitationModalProps {
  token: string;
  onClose: () => void;
  onAccepted: (groupId: string, joinedUser?: { id: string; name: string; email: string }) => void;
}

export const AcceptInvitationModal: React.FC<AcceptInvitationModalProps> = ({
  token,
  onClose,
  onAccepted,
}) => {
  const [info, setInfo] = useState<InvitationInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [acceptedMsg, setAcceptedMsg] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    const fetchInfo = async () => {
      setLoading(true);
      setErrorMsg(null);
      try {
        const data = await api.getInvitationInfo(token);
        if (isMounted) setInfo(data);
      } catch (err: any) {
        if (isMounted) setErrorMsg(err?.message || 'Failed to load invitation.');
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchInfo();
    return () => {
      isMounted = false;
    };
  }, [token]);

  const handleAccept = async () => {
    setSubmitting(true);
    setErrorMsg(null);
    try {
      const res = await api.acceptInvitation(token);
      if (res.access_token) {
        api.setToken(res.access_token);
        if (res.refresh_token) {
          localStorage.setItem('sw_refresh_token', res.refresh_token);
        }
        if (res.user) {
          localStorage.setItem('sw_current_user', JSON.stringify(res.user));
        }
      }
      setAcceptedMsg(res.message || "You've joined the group!");
      setTimeout(() => {
        onAccepted(res.group_id, res.user);
        onClose();
      }, 1200);
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to accept invitation.');
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-content"
        onClick={(e) => e.stopPropagation()}
        style={{ padding: '36px', maxWidth: '480px', textAlign: 'center' }}
      >
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '-12px', marginRight: '-12px' }}>
          <button onClick={onClose} className="btn-icon-circular" aria-label="Close">
            <X size={18} />
          </button>
        </div>

        {loading ? (
          <div style={{ padding: '40px 0', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
            <Loader2 className="animate-spin" size={32} color="var(--color-primary)" />
            <p style={{ color: 'var(--color-text-secondary)', fontSize: '15px' }}>Loading invitation details…</p>
          </div>
        ) : errorMsg && !info ? (
          <div style={{ padding: '24px 0' }}>
            <div style={{
              width: '56px',
              height: '56px',
              borderRadius: '50%',
              backgroundColor: 'rgba(198, 69, 69, 0.1)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 16px',
              color: 'var(--color-error)'
            }}>
              <AlertCircle size={28} />
            </div>
            <h2 style={{ fontSize: '22px', fontFamily: 'var(--font-display)', marginBottom: '8px' }}>Invitation Error</h2>
            <p style={{ color: 'var(--color-text-secondary)', fontSize: '14px', marginBottom: '24px' }}>{errorMsg}</p>
            <button onClick={onClose} className="btn btn-secondary">Close</button>
          </div>
        ) : (
          <div>
            <div style={{
              width: '64px',
              height: '64px',
              borderRadius: '18px',
              background: 'linear-gradient(135deg, #0071e3 0%, #0051a8 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 20px',
              color: '#ffffff',
              boxShadow: '0 8px 20px rgba(0, 113, 227, 0.3)'
            }}>
              <Users size={32} />
            </div>

            <span className="caption-uppercase" style={{ color: 'var(--color-primary)' }}>
              Group Invitation
            </span>
            <h2 style={{
              fontSize: '26px',
              fontFamily: 'var(--font-display)',
              marginTop: '4px',
              marginBottom: '10px'
            }}>
              Join {info?.group_name}
            </h2>

            <p style={{ color: 'var(--color-text-secondary)', fontSize: '15px', lineHeight: 1.5, marginBottom: '24px' }}>
              <strong>{info?.invited_by_name}</strong> has invited you to join this group on FairSplit to split and track shared expenses.
            </p>

            {acceptedMsg ? (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                backgroundColor: 'rgba(52, 199, 89, 0.12)',
                color: '#34c759',
                padding: '12px 16px',
                borderRadius: 'var(--radius-md)',
                fontSize: '15px',
                fontWeight: 600,
              }}>
                <CheckCircle2 size={18} />
                <span>{acceptedMsg}</span>
              </div>
            ) : (
              <div>
                {errorMsg && (
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    backgroundColor: 'rgba(198, 69, 69, 0.1)',
                    color: 'var(--color-error)',
                    padding: '10px 14px',
                    borderRadius: 'var(--radius-md)',
                    fontSize: '14px',
                    marginBottom: '18px',
                    textAlign: 'left'
                  }}>
                    <AlertCircle size={16} />
                    <span>{errorMsg}</span>
                  </div>
                )}

                <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
                  <button
                    onClick={onClose}
                    className="btn btn-secondary"
                    disabled={submitting}
                  >
                    Decline
                  </button>
                  <button
                    onClick={handleAccept}
                    className="btn btn-primary"
                    disabled={submitting || info?.is_expired}
                    style={{ minWidth: '160px' }}
                  >
                    {submitting ? (
                      <>
                        <Loader2 className="animate-spin" size={16} />
                        <span>Joining…</span>
                      </>
                    ) : (
                      <>
                        <span>Accept &amp; Join</span>
                        <ArrowRight size={16} />
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
