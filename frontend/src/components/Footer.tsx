import React from 'react';

interface FooterProps {
  onOpenNewExpense: () => void;
}

export const Footer: React.FC<FooterProps> = ({ onOpenNewExpense }) => {
  return (
    <>
      {/* Pre-footer Coral Callout Card */}
      <section className="app-container" style={{ marginBottom: '64px' }}>
        <div
          className="callout-coral"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '24px',
            padding: '48px',
          }}
        >
          <div>
            <h2
              style={{
                fontFamily: 'var(--font-display)',
                fontSize: '32px',
                lineHeight: 1.15,
                color: '#ffffff',
                marginBottom: '8px',
              }}
            >
              Simplify balances with zero friction.
            </h2>
            <p style={{ color: 'rgba(255, 255, 255, 0.9)', fontSize: '16px', maxWidth: '540px' }}>
              Built with Python FastAPI, SQLAlchemy asyncpg, Redis write-invalidate caching, and exact decimal arithmetic.
            </p>
          </div>
          <button
            onClick={onOpenNewExpense}
            className="btn"
            style={{
              backgroundColor: 'var(--color-canvas)',
              color: 'var(--color-ink)',
              fontWeight: 600,
              padding: '12px 24px',
              height: '44px',
              border: 'none',
            }}
          >
            Add an Expense Now
          </button>
        </div>
      </section>

      {/* Footer in Dark Navy */}
      <footer
        style={{
          backgroundColor: 'var(--color-surface-dark)',
          color: 'var(--color-on-dark-soft)',
          padding: '64px 0 48px',
          borderTop: '1px solid rgba(255, 255, 255, 0.08)',
        }}
      >
        <div className="app-container">
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: '40px',
              marginBottom: '48px',
            }}
          >
            {/* Column 1: Brand */}
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
                <svg
                  width="20"
                  height="20"
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
                <span
                  style={{
                    fontFamily: 'var(--font-display)',
                    fontSize: '22px',
                    color: 'var(--color-on-dark)',
                    fontWeight: 600,
                  }}
                >
                  FairSplit
                </span>
              </div>
              <p style={{ fontSize: '13px', lineHeight: 1.6, color: 'var(--color-on-dark-soft)' }}>
                A warm-canvas editorial interface engineered for financial clarity and clean debt graph reduction.
              </p>
            </div>

            {/* Column 2: System Features */}
            <div>
              <h4 style={{ color: 'var(--color-on-dark)', fontSize: '14px', fontWeight: 600, marginBottom: '14px' }}>
                Engineering Core
              </h4>
              <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '13px' }}>
                <li>Modular Monolith Design</li>
                <li>Strategy Pattern Splits</li>
                <li>Write-Invalidate Redis Caching</li>
                <li>Greedy Net-Flow Solver</li>
              </ul>
            </div>

            {/* Column 3: Architecture */}
            <div>
              <h4 style={{ color: 'var(--color-on-dark)', fontSize: '14px', fontWeight: 600, marginBottom: '14px' }}>
                Stack
              </h4>
              <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '13px' }}>
                <li>FastAPI & Pydantic v2</li>
                <li>PostgreSQL & SQLAlchemy asyncpg</li>
                <li>React & Vite Frontend</li>
                <li>JWT Security Layer</li>
              </ul>
            </div>

            {/* Column 4: Status */}
            <div>
              <h4 style={{ color: 'var(--color-on-dark)', fontSize: '14px', fontWeight: 600, marginBottom: '14px' }}>
                Status
              </h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '13px' }}>
                <span style={{ color: 'var(--color-success)' }}>● 57/57 Backend Tests Passed</span>
                <span>● Clean Architectural Boundaries</span>
                <span>● Portfolio Ready</span>
              </div>
            </div>
          </div>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              paddingTop: '24px',
              borderTop: '1px solid rgba(255, 255, 255, 0.06)',
              fontSize: '12px',
              color: 'var(--color-on-dark-soft)',
            }}
          >
            <span>Splitwise Editorial System — Claude Design Analysis Implementation</span>
            <span>Anthropic Warm-Canvas Editorial Specification</span>
          </div>
        </div>
      </footer>
    </>
  );
};
