import React from 'react';
import { Users, Plus, Check } from 'lucide-react';
import type { Group } from '../api/client';

interface GroupSelectorProps {
  groups: Group[];
  selectedGroupId: string;
  onSelectGroup: (groupId: string) => void;
  onOpenNewGroup: () => void;
}

export const GroupSelector: React.FC<GroupSelectorProps> = ({
  groups,
  selectedGroupId,
  onSelectGroup,
  onOpenNewGroup,
}) => {
  return (
    <div style={{ marginBottom: '28px' }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '14px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Users size={18} style={{ color: 'var(--color-primary)' }} />
          <h2
            style={{
              fontFamily: 'var(--font-display)',
              fontSize: '22px',
              fontWeight: 500,
              color: 'var(--color-ink)',
            }}
          >
            Your Active Ledgers
          </h2>
        </div>
        <button
          onClick={onOpenNewGroup}
          className="btn btn-secondary"
          style={{ height: '32px', padding: '0 12px', fontSize: '13px' }}
        >
          <Plus size={14} />
          <span>New Group</span>
        </button>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
          gap: '16px',
        }}
      >
        {groups.map((group) => {
          const isSelected = group.id === selectedGroupId;
          return (
            <div
              key={group.id}
              onClick={() => onSelectGroup(group.id)}
              className={isSelected ? 'card-cream' : 'card-white'}
              style={{
                cursor: 'pointer',
                padding: '18px 20px',
                borderRadius: 'var(--radius-lg)',
                border: isSelected ? '2px solid var(--color-primary)' : '1px solid var(--color-hairline)',
                position: 'relative',
                transition: 'all 0.15s ease',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                <h4
                  style={{
                    fontFamily: 'var(--font-display)',
                    fontSize: '19px',
                    fontWeight: 500,
                    color: 'var(--color-ink)',
                  }}
                >
                  {group.name}
                </h4>
                {isSelected && (
                  <span
                    style={{
                      width: '20px',
                      height: '20px',
                      borderRadius: 'var(--radius-pill)',
                      backgroundColor: 'var(--color-primary)',
                      color: '#ffffff',
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    <Check size={12} strokeWidth={3} />
                  </span>
                )}
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--color-muted)', fontSize: '13px' }}>
                <span>{group.members.length} members</span>
                <span>•</span>
                <span className="font-mono">{group.currency}</span>
              </div>

              {/* Members preview row */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '12px' }}>
                {group.members.slice(0, 4).map((m, idx) => (
                  <div
                    key={idx}
                    title={m.user.name}
                    style={{
                      width: '24px',
                      height: '24px',
                      borderRadius: 'var(--radius-pill)',
                      backgroundColor: isSelected ? 'var(--color-surface-cream-strong)' : 'var(--color-surface-card)',
                      border: '1px solid var(--color-hairline)',
                      fontSize: '11px',
                      fontWeight: 600,
                      color: 'var(--color-ink)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    {m.user.name.charAt(0)}
                  </div>
                ))}
                {group.members.length > 4 && (
                  <span className="caption" style={{ color: 'var(--color-muted)', fontSize: '11px' }}>
                    +{group.members.length - 4}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
