import { useState } from 'react';

export function accountName(user: { name?: string; email?: string }): string {
  return user.name?.trim() || user.email?.split('@')[0] || 'Account';
}

export function AccountAvatar({ user, size = 32 }: { user: { name?: string; email?: string; avatar_url?: string }; size?: number }) {
  const [failedUrl, setFailedUrl] = useState<string | null>(null);
  const name = accountName(user);
  const initials = name.split(/\s+/).slice(0, 2).map(part => part.charAt(0)).join('').toUpperCase();
  const url = user.avatar_url?.trim();
  return <span style={{ width: size, height: size, borderRadius: '50%', flexShrink: 0, overflow: 'hidden', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', backgroundColor: 'var(--color-primary)', color: '#fff', fontSize: size * 0.38, fontWeight: 700 }}>
    {url && failedUrl !== url ? <img src={url} alt={name} referrerPolicy="no-referrer" onError={() => setFailedUrl(url)} style={{ width: '100%', height: '100%', objectFit: 'cover' }} /> : <span aria-label={name}>{initials}</span>}
  </span>;
}
