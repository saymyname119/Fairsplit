import React from 'react';
import { ShieldCheck, Database, RefreshCw, UserCheck } from 'lucide-react';
import type { User } from '../api/client';

interface TopNavProps {
  currentUser: User | null;
  isDemoMode: boolean;
  onToggleDemo: () => void;
  onOpenAuth: () => void;
  onOpenNewGroup: () => void;
  onOpenNewExpense: () => void;
}

export const TopNav: React.FC<TopNavProps> = ({
  currentUser,
  isDemoMode,
  onToggleDemo,
  onOpenAuth,
  onOpenNewGroup,
  onOpenNewExpense,
}) => {
  return (
    <header
      style={{
        backgroundColor: 'var(--color-canvas)',
        borderBottom: '1px solid var(--color-hairline)',
        position: 'sticky',
        top: 0,
        zIndex: 100,
        height: '64px',
        display: 'flex',
        alignItems: 'center',
      }}
    >
      <div
        className="app-container"
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        {/* Brand: Anthropic Radial Spike Glyphs + Wordmark */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div
            style={{
              width: '28px',
              height: '28px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            {/* 4-spoke radial spike glyph in warm coral */}
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="var(--color-primary)"
              strokeWidth="2.7"
              strokeLinecap="round"
            >
              <line x1="12" y1="2" x2="12" y2="22" />
              <line x1="2" y1="12" x2="22" y2="12" />
              <line x1="4.93" y1="4.93" x2="19.07" y2="19.07" />
              <line x1="4.93" y1="19.07" x2="19.07" y2="4.93" />
            </svg>
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
            <span
              style={{
                fontFamily: 'var(--font-display)',
                fontSize: '24px',
                fontWeight: 600,
                letterSpacing: '-0.5px',
                color: 'var(--color-ink)',
              }}
            >
              Splitwise
            </span>
            <span
              className="caption-uppercase"
              style={{
                color: 'var(--color-muted)',
                backgroundColor: 'var(--color-surface-card)',
                padding: '2px 6px',
                borderRadius: 'var(--radius-xs)',
              }}
            >
              Editorial
            </span>
          </div>
        </div>

        {/* Center / Right controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {/* Mode Badge / Switcher */}
          <button
            onClick={onToggleDemo}
            title="Toggle between Live FastAPI backend & Mock Demo store"
            className="badge badge-cream"
            style={{
              cursor: 'pointer',
              border: '1px solid var(--color-hairline)',
              background: isDemoMode ? 'var(--color-surface-soft)' : '#e8f5e9',
              color: isDemoMode ? 'var(--color-body)' : '#2e7d32',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
            }}
          >
            {isDemoMode ? (
              <>
                <Database size={13} style={{ color: 'var(--color-primary)' }} />
                <span>Demo Sandbox</span>
              </>
            ) : (
              <>
                <ShieldCheck size={13} style={{ color: '#2e7d32' }} />
                <span>FastAPI Live</span>
              </>
            )}
            <RefreshCw size={11} style={{ opacity: 0.6, marginLeft: '2px' }} />
          </button>

          {/* Action Buttons */}
          <button onClick={onOpenNewGroup} className="btn btn-secondary" style={{ height: '36px', padding: '0 14px' }}>
            + Group
          </button>
          <button onClick={onOpenNewExpense} className="btn btn-primary" style={{ height: '36px', padding: '0 16px' }}>
            + Add Expense
          </button>

          {/* User Profile / Auth */}
          <button
            onClick={onOpenAuth}
            className="btn btn-text-link"
            style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px' }}
          >
            {currentUser?.avatar_url ? (
              <img
                src={currentUser.avatar_url}
                alt={currentUser.name}
                style={{
                  width: '24px', height: '24px', borderRadius: '50%',
                  objectFit: 'cover', border: '1.5px solid var(--color-primary)',
                }}
                referrerPolicy="no-referrer"
              />
            ) : (
              <UserCheck size={15} style={{ color: 'var(--color-primary)' }} />
            )}
            <span>{currentUser ? currentUser.name.split(' ')[0] : 'Sign In'}</span>
          </button>
        </div>
      </div>
    </header>
  );
};
