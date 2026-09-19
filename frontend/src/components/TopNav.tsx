import React from 'react';
import { UserCheck, Sun, Moon } from 'lucide-react';
import type { User } from '../api/client';

interface TopNavProps {
  currentUser: User | null;
  isDark: boolean;
  onToggleDark: () => void;
  onOpenAuth: () => void;
  onOpenNewGroup: () => void;
  onOpenNewExpense: () => void;
}

export const TopNav: React.FC<TopNavProps> = ({
  currentUser,
  isDark,
  onToggleDark,
  onOpenAuth,
  onOpenNewGroup,
  onOpenNewExpense,
}) => {
  return (
    <header
      style={{
        backgroundColor: 'var(--color-nav-bg)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        borderBottom: '1px solid var(--color-nav-border)',
        position: 'sticky',
        top: 0,
        zIndex: 100,
        height: '58px',
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
        {/* Brand: Radial Spike Glyphs + Wordmark */}
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
              FairSplit
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

        {/* Right: controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>

          {/* New Group — text/ghost style */}
          <button
            onClick={onOpenNewGroup}
            className="btn-text-link"
            style={{
              fontSize: '14px',
              fontWeight: 500,
              color: 'var(--color-body-strong)',
              padding: '6px 12px',
            }}
          >
            + Group
          </button>

          {/* Add Expense — pill CTA */}
          <button
            onClick={onOpenNewExpense}
            className="btn btn-primary"
            style={{ height: '34px', padding: '0 18px', fontSize: '13.5px' }}
          >
            + Add Expense
          </button>

          {/* Dark Mode Toggle */}
          <button
            onClick={onToggleDark}
            aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
            title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
            className="btn-icon-circular"
            style={{
              color: 'var(--color-muted)',
              marginLeft: '2px',
            }}
          >
            {isDark ? <Sun size={15} /> : <Moon size={15} />}
          </button>

          {/* User avatar pill */}
          <button
            onClick={onOpenAuth}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '7px',
              padding: '4px 10px 4px 4px',
              borderRadius: 'var(--radius-pill)',
              border: '1px solid var(--color-hairline)',
              background: 'var(--color-surface-card)',
              cursor: 'pointer',
              fontSize: '13px',
              fontFamily: 'var(--font-sans)',
              fontWeight: 500,
              color: 'var(--color-ink)',
              transition: 'all 0.15s ease',
              boxShadow: '0 1px 2px rgba(20,20,19,0.04)',
              marginLeft: '4px',
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--color-surface-cream-strong)';
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--color-surface-card)';
            }}
          >
            {currentUser?.avatar_url ? (
              <img
                src={currentUser.avatar_url}
                alt={currentUser.name}
                style={{
                  width: '26px', height: '26px', borderRadius: '50%',
                  objectFit: 'cover', border: '1.5px solid var(--color-primary)',
                }}
                referrerPolicy="no-referrer"
              />
            ) : (
              <div style={{
                width: '26px', height: '26px', borderRadius: '50%',
                backgroundColor: 'var(--color-primary)',
                color: '#fff', display: 'flex', alignItems: 'center',
                justifyContent: 'center', fontSize: '11px', fontWeight: 700,
                flexShrink: 0,
              }}>
                {currentUser ? currentUser.name.charAt(0).toUpperCase() : <UserCheck size={13} />}
              </div>
            )}
            <span>{currentUser ? currentUser.name.split(' ')[0] : 'Sign In'}</span>
          </button>
        </div>
      </div>
    </header>
  );
};
