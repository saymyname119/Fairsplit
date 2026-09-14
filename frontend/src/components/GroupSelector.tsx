import React, { useState } from 'react';
import { Users, Plus, Check, UserPlus, UserMinus } from 'lucide-react';
import type { Group } from '../api/client';

interface GroupSelectorProps {
  groups: Group[];
  selectedGroupId: string;
  onSelectGroup: (groupId: string) => void;
  onOpenNewGroup: () => void;
  onAddMember: (groupId: string) => void;
  onRemoveMember: (groupId: string, userId: string, userName: string) => void;
}

export const GroupSelector: React.FC<GroupSelectorProps> = ({
  groups,
  selectedGroupId,
  onSelectGroup,
  onOpenNewGroup,
  onAddMember,
  onRemoveMember,
}) => {
  const [hoveredMember, setHoveredMember] = useState<string | null>(null);

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
          style={{ height: '30px', padding: '0 14px', fontSize: '12.5px' }}
        >
          <Plus size={13} />
          <span>New Group</span>
        </button>
      </div>

      {groups.length === 0 ? (
        <div
          className="card-white"
          style={{
            padding: '36px 24px',
            textAlign: 'center',
            borderRadius: 'var(--radius-lg)',
            border: '1px dashed var(--color-hairline)',
          }}
        >
          <Users size={32} style={{ color: 'var(--color-muted)', margin: '0 auto 12px' }} />
          <h3 style={{ fontSize: '16px', fontFamily: 'var(--font-display)', marginBottom: '6px', color: 'var(--color-ink)' }}>
            No groups created yet
          </h3>
          <p style={{ fontSize: '13px', color: 'var(--color-muted)', maxWidth: '420px', margin: '0 auto 16px' }}>
            Create your first group for travel, housemates, or dinners to start splitting expenses.
          </p>
          <button
            onClick={onOpenNewGroup}
            className="btn btn-primary"
            style={{ height: '34px', padding: '0 18px', fontSize: '13px' }}
          >
            <Plus size={14} />
            <span>Create First Group</span>
          </button>
        </div>
      ) : (
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
                {group.members.slice(0, 5).map((m, idx) => {
                  const name = m.user?.name || 'Member';
                  const isMemberHovered = isSelected && hoveredMember === m.user_id;
                  return (
                    <div
                      key={idx}
                      title={name}
                      style={{
                        width: '28px',
                        height: '28px',
                        borderRadius: 'var(--radius-pill)',
                        backgroundColor: isMemberHovered
                          ? 'rgba(198,69,69,0.15)'
                          : isSelected
                          ? 'var(--color-surface-cream-strong)'
                          : 'var(--color-surface-card)',
                        border: isMemberHovered
                          ? '1px solid var(--color-error)'
                          : '1px solid var(--color-hairline)',
                        fontSize: '11px',
                        fontWeight: 600,
                        color: isMemberHovered ? 'var(--color-error)' : 'var(--color-ink)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        cursor: isSelected ? 'pointer' : 'default',
                        transition: 'all 0.15s ease',
                        position: 'relative',
                      }}
                      onMouseEnter={() => isSelected && setHoveredMember(m.user_id)}
                      onMouseLeave={() => setHoveredMember(null)}
                      onClick={(e) => {
                        if (isSelected && isMemberHovered) {
                          e.stopPropagation();
                          onRemoveMember(group.id, m.user_id, name);
                        }
                      }}
                    >
                      {isMemberHovered ? (
                        <UserMinus size={12} />
                      ) : (
                        name.charAt(0).toUpperCase()
                      )}
                    </div>
                  );
                })}
                {group.members.length > 5 && (
                  <span className="caption" style={{ color: 'var(--color-muted)', fontSize: '11px' }}>
                    +{group.members.length - 5}
                  </span>
                )}

                {/* Add Member button — visible only on selected group */}
                {isSelected && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onAddMember(group.id);
                    }}
                    title="Add member to this group"
                    style={{
                      width: '28px',
                      height: '28px',
                      borderRadius: 'var(--radius-pill)',
                      border: '1.5px dashed var(--color-primary)',
                      backgroundColor: 'transparent',
                      color: 'var(--color-primary)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease',
                      padding: 0,
                      flexShrink: 0,
                    }}
                    onMouseEnter={(e) => {
                      (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'rgba(204,120,92,0.1)';
                    }}
                    onMouseLeave={(e) => {
                      (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'transparent';
                    }}
                  >
                    <UserPlus size={12} />
                  </button>
                )}
              </div>
            </div>
          );
        })}
        </div>
      )}
    </div>
  );
};
