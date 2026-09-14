import React from 'react';
import { Terminal, Database, Activity, Server } from 'lucide-react';
import type { ActivityEvent } from '../api/client';

interface ActivityMockupProps {
  events: ActivityEvent[];
}

export const ActivityMockup: React.FC<ActivityMockupProps> = ({ events }) => {
  return (
    <div style={{ marginBottom: '48px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Terminal size={18} style={{ color: 'var(--color-primary)' }} />
          <h2
            style={{
              fontFamily: 'var(--font-display)',
              fontSize: '22px',
              fontWeight: 500,
              color: 'var(--color-ink)',
            }}
          >
            System Chrome & Ledger Event Bus
          </h2>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span className="badge badge-teal font-mono" style={{ fontSize: '11px' }}>
            <Database size={11} />
            REDIS WRITE-INVALIDATE
          </span>
          <span className="badge badge-amber font-mono" style={{ fontSize: '11px' }}>
            <Activity size={11} />
            IN-PROCESS BUS
          </span>
        </div>
      </div>

      {/* Code window card in dark navy */}
      <div
        className="card-dark"
        style={{
          padding: '24px',
          borderRadius: 'var(--radius-lg)',
          boxShadow: '0 8px 24px rgba(20, 20, 19, 0.25)',
        }}
      >
        {/* Terminal Header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
            paddingBottom: '14px',
            marginBottom: '16px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: '#ff5f56' }} />
            <div style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: '#ffbd2e' }} />
            <div style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: '#27c93f' }} />
            <span
              className="font-mono"
              style={{
                fontSize: '12px',
                color: 'var(--color-on-dark-soft)',
                marginLeft: '8px',
              }}
            >
              fairsplit-ledger.telemetry ~ asyncpg + redis
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '14px', fontSize: '12px' }}>
            <span style={{ color: 'var(--color-accent-teal)', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Server size={12} />
              <span>FastAPI v0.2.0</span>
            </span>
          </div>
        </div>

        {/* Stream Entries */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
            maxHeight: '220px',
            overflowY: 'auto',
            fontFamily: 'var(--font-mono)',
            fontSize: '13px',
          }}
        >
          {events.map((evt) => {
            const isDel = evt.method === 'DEL';
            const isPost = evt.method === 'POST';

            return (
              <div
                key={evt.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '6px 10px',
                  backgroundColor: 'var(--color-surface-dark-soft)',
                  borderRadius: 'var(--radius-xs)',
                  borderLeft: isDel
                    ? '3px solid var(--color-accent-amber)'
                    : isPost
                    ? '3px solid var(--color-primary)'
                    : '3px solid var(--color-accent-teal)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ color: 'var(--color-on-dark-soft)', fontSize: '11px' }}>
                    {evt.timestamp}
                  </span>
                  <span
                    style={{
                      padding: '2px 6px',
                      borderRadius: '4px',
                      fontSize: '11px',
                      fontWeight: 600,
                      backgroundColor: isDel
                        ? 'rgba(232, 165, 90, 0.2)'
                        : isPost
                        ? 'rgba(204, 120, 92, 0.25)'
                        : 'rgba(93, 184, 166, 0.2)',
                      color: isDel
                        ? 'var(--color-accent-amber)'
                        : isPost
                        ? 'var(--color-primary)'
                        : 'var(--color-accent-teal)',
                    }}
                  >
                    {evt.method}
                  </span>
                  <span style={{ color: '#ffffff', fontWeight: 500 }}>
                    {evt.endpoint}
                  </span>
                  <span style={{ color: 'var(--color-on-dark-soft)', fontSize: '12px' }}>
                    — {evt.summary}
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  {evt.cache_hit && (
                    <span style={{ color: 'var(--color-accent-teal)', fontSize: '11px' }}>
                      CACHE_HIT
                    </span>
                  )}
                  <span style={{ color: '#27c93f', fontSize: '12px' }}>{evt.status}</span>
                  <span style={{ color: 'var(--color-on-dark-soft)', fontSize: '11px' }}>
                    {evt.latency_ms}ms
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
