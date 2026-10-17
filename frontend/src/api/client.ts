/**
 * frontend/src/api/client.ts
 * FairSplit Production API Client with typed domain interfaces and live FastAPI integration.
 */

export type SplitStrategy = 'EQUAL' | 'EXACT' | 'PERCENTAGE' | 'SHARE';

export interface ExpensePreview {
  amount: string; description: string; paid_by_id: string; paid_by_name: string;
  participant_ids: string[]; participant_names: string[];
  split_type: 'equal' | 'exact' | 'percent';
  splits: Array<{ name: string; value: string }>;
}

export interface User {
  id: string;
  name: string;
  email: string;
  phone?: string;
  avatar_url?: string;
}

export interface GroupMember {
  user_id: string;
  user: User;
  joined_at: string;
}

export interface Group {
  id: string;
  name: string;
  currency: string;
  created_by: string;
  created_at: string;
  members: GroupMember[];
}

export interface SplitItem {
  user_id: string;
  amount?: number;
  percentage?: number;
  share?: number;
}

export interface Expense {
  id: string;
  group_id: string;
  description: string;
  amount: number;
  currency: string;
  paid_by_id: string;
  paid_by?: User;
  split_strategy: SplitStrategy;
  splits: SplitItem[];
  created_at: string;
}

export interface SettlementTransaction {
  version: number;
  from_user_id: string;
  from_user_name: string;
  to_user_id: string;
  to_user_name: string;
  amount: number;
  currency: string;
}

export interface GroupBalances {
  group_id: string;
  currency: string;
  balances: Record<string, number>;
  cached?: boolean;
}

export interface Invitation {
  id: string;
  group_id: string;
  group_name: string;
  invited_by_id: string;
  invited_by_name: string;
  email: string;
  status: 'pending' | 'accepted' | 'expired' | 'cancelled';
  token?: string;
  invite_url?: string;
  email_dispatched?: boolean;
  delivery_status?: string;
  created_at: string;
  expires_at: string;
}

export interface InvitationInfo {
  id: string;
  group_name: string;
  invited_by_name: string;
  email: string;
  status: string;
  is_expired: boolean;
}

// Live API and configuration state
export const API_BASE = (
  import.meta.env.VITE_API_URL || 'https://fairsplit-api-mhgt.onrender.com'
).replace(/\/$/, '');

export class ApiClient {
  private token: string | null = localStorage.getItem('sw_token');

  constructor() {
    this.checkLiveBackend();
  }

  async checkLiveBackend(): Promise<boolean> {
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 5000);
      const res = await this.request(`${API_BASE}/healthz`, {
        method: 'GET',
        signal: controller.signal,
      });
      clearTimeout(timeout);
      const data = await res.json().catch(() => null);
      return res.ok || data?.services?.database === 'ok';
    } catch {
      return false;
    }
  }

  async syncOAuthUser(accessToken: string, signal?: AbortSignal): Promise<User> {
    const res = await this.request(`${API_BASE}/auth/oauth-sync`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${accessToken}` },
      signal,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'OAuth synchronization failed' }));
      throw new Error(err.message || err.detail || 'OAuth synchronization failed');
    }
    const data = await res.json();
    signal?.throwIfAborted();
    this.setToken(data.tokens.access_token, data.tokens.refresh_token);
    return data.user as User;
  }

  setToken(token: string, refreshToken?: string) {
    this.sessionGeneration++;
    this.storeTokens(token, refreshToken);
  }

  private storeTokens(token: string, refreshToken?: string) {
    if (refreshToken) localStorage.setItem('sw_refresh_token', refreshToken);
    this.token = token;
    localStorage.setItem('sw_token', token);
  }

  clearToken() {
    this.sessionGeneration++;
    this.token = null;
    localStorage.removeItem('sw_refresh_token');
    localStorage.removeItem('sw_token');
  }

  hasToken(): boolean {
    return !!this.token;
  }

  private refreshing: Promise<boolean> | null = null;
  private sessionGeneration = 0;

  private async renewSession(): Promise<boolean> {
    if (this.refreshing) return this.refreshing;
    const generation = this.sessionGeneration;
    const refreshToken = localStorage.getItem('sw_refresh_token');
    if (!refreshToken) return false;
    this.refreshing = (async () => {
      const response = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (response.status >= 500) throw new Error('Session renewal is temporarily unavailable. Please try again.');
      if (!response.ok) return false;
      const tokens = await response.json();
      if (generation !== this.sessionGeneration) return false;
      this.storeTokens(tokens.access_token, tokens.refresh_token);
      return true;
    })().finally(() => { this.refreshing = null; });
    return this.refreshing;
  }

  private async request(url: string, options: RequestInit = {}): Promise<Response> {
    const headers = new Headers(options.headers);
    const usedToken = this.token;
    const generation = this.sessionGeneration;
    const authenticated = headers.get('Authorization') === `Bearer ${usedToken}` && !!usedToken;
    const response = await fetch(url, options);
    if (response.status !== 401 || !authenticated || generation !== this.sessionGeneration) return response;
    const renewed = this.token !== usedToken || await this.renewSession();
    if (generation !== this.sessionGeneration) return response;
    if (renewed) {
      headers.set('Authorization', `Bearer ${this.token}`);
      const retry = await fetch(url, { ...options, headers });
      if (retry.status !== 401 || generation !== this.sessionGeneration) return retry;
    }
    this.clearToken();
    localStorage.removeItem('sw_current_user');
    window.dispatchEvent(new Event('fairsplit:session-expired'));
    return response;
  }

  async parseExpense(groupId: string, text: string): Promise<ExpensePreview> {
    const response = await this.request(`${API_BASE}/groups/${groupId}/expenses/parse`, {
      method: 'POST', headers: { 'Content-Type': 'application/json', ...this.authHeaders() },
      body: JSON.stringify({ text }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.message || data.detail || 'Could not parse expense');
    return data.preview;
  }

  private authHeaders(): HeadersInit {
    return this.token ? { Authorization: `Bearer ${this.token}` } : {};
  }

  async getGroups(): Promise<Group[]> {
    try {
      const res = await this.request(`${API_BASE}/groups/`, {
        headers: this.authHeaders(),
      });
      if (!res.ok) return [];
      const rawGroups = await res.json();
      return rawGroups.map((g: any) => ({
        id: g.id,
        name: g.name,
        currency: g.currency || 'USD',
        created_by: g.created_by_id || g.created_by || '',
        created_at: g.created_at,
        members: (g.members || []).map((m: any) => ({
          user_id: m.user_id,
          user: m.user || {
            id: m.user_id,
            name: m.user_name || 'Member',
            email: m.user_email || '',
          },
          joined_at: m.joined_at,
        })),
      }));
    } catch (err) {
      console.error('Failed to fetch groups:', err);
      return [];
    }
  }

  async createGroup(name: string, currency: string, createdBy: string): Promise<Group> {
    const res = await this.request(`${API_BASE}/groups/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...this.authHeaders(),
      },
      body: JSON.stringify({ name, currency }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to create group' }));
      throw new Error(err.detail || 'Failed to create group');
    }
    const g = await res.json();
    return {
      id: g.id,
      name: g.name,
      currency,
      created_by: g.created_by_id || createdBy,
      created_at: g.created_at,
      members: (g.members || []).map((m: any) => ({
        user_id: m.user_id,
        user: m.user || {
          id: m.user_id,
          name: m.user_name || 'Member',
          email: m.user_email || '',
        },
        joined_at: m.joined_at,
      })),
    };
  }

  async getExpenses(groupId: string): Promise<Expense[]> {
    try {
      const res = await this.request(`${API_BASE}/groups/${groupId}/expenses`, {
        headers: this.authHeaders(),
      });
      if (!res.ok) return [];
      const data = await res.json();
      return data.map((exp: any) => ({
        id: exp.id,
        group_id: exp.group_id,
        description: exp.description,
        amount: parseFloat(exp.amount) || 0,
        currency: exp.currency || 'USD',
        paid_by_id: exp.paid_by_id,
        split_strategy: (exp.split_type === 'percent' ? 'PERCENTAGE' : exp.split_type === 'exact' ? 'EXACT' : 'EQUAL') as SplitStrategy,
        splits: (exp.splits || []).map((s: any) => ({
          user_id: s.user_id,
          amount: parseFloat(s.owed_amount) || 0,
          percentage: s.percentage ? parseFloat(s.percentage) : undefined,
        })),
        created_at: exp.created_at || new Date().toISOString(),
      }));
    } catch (err) {
      console.error('Failed to fetch expenses:', err);
      return [];
    }
  }

  async createExpense(expense: Omit<Expense, 'id' | 'created_at'>): Promise<Expense> {
    const splitTypeMap: Record<SplitStrategy, 'equal' | 'percent' | 'exact'> = {
      EQUAL: 'equal',
      PERCENTAGE: 'percent',
      EXACT: 'exact',
      SHARE: 'equal',
    };
    const split_type = splitTypeMap[expense.split_strategy] || 'equal';
    const participants = Array.from(
      new Set(expense.splits.map((s) => s.user_id))
    );
    const backendSplits = expense.splits.map((s) => ({
      user_id: s.user_id,
      value: s.percentage ?? s.amount ?? 1,
    }));

    const backendPayload = {
      paid_by_id: expense.paid_by_id,
      amount: expense.amount,
      description: expense.description,
      split_type,
      participants,
      splits: split_type === 'equal' ? undefined : backendSplits,
    };

    const res = await this.request(`${API_BASE}/groups/${expense.group_id}/expenses`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...this.authHeaders(),
      },
      body: JSON.stringify(backendPayload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to create expense' }));
      throw new Error(err.detail || 'Failed to create expense');
    }
    const data = await res.json();
    return {
      id: data.id,
      group_id: data.group_id,
      description: data.description,
      amount: parseFloat(data.amount) || expense.amount,
      currency: data.currency || expense.currency || 'USD',
      paid_by_id: data.paid_by_id,
      split_strategy: expense.split_strategy,
      splits: Array.isArray(data.splits)
        ? data.splits.map((s: any) => ({ user_id: s.user_id, amount: parseFloat(s.owed_amount) || 0 }))
        : expense.splits,
      created_at: data.created_at || new Date().toISOString(),
    };
  }

  async deleteExpense(expenseId: string, groupId: string): Promise<void> {
    const res = await this.request(`${API_BASE}/groups/${groupId}/expenses/${expenseId}`, {
      method: 'DELETE',
      headers: this.authHeaders(),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to delete expense' }));
      throw new Error(err.detail || 'Failed to delete expense');
    }
  }

  async updateExpense(expenseId: string, groupId: string, updates: {
    description?: string;
    amount?: number;
    paid_by_id?: string;
    split_strategy?: SplitStrategy;
    splits?: SplitItem[];
  }): Promise<Expense> {
    const res = await this.request(`${API_BASE}/groups/${groupId}/expenses/${expenseId}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        ...this.authHeaders(),
      },
      body: JSON.stringify({
        description: updates.description,
        amount: updates.amount,
        paid_by_id: updates.paid_by_id,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to update expense' }));
      throw new Error(err.detail || 'Failed to update expense');
    }
    const data = await res.json();
    return {
      ...updates,
      id: data.id,
      group_id: data.group_id || groupId,
      description: data.description || updates.description || '',
      amount: parseFloat(data.amount) || updates.amount || 0,
      currency: data.currency || 'USD',
      paid_by_id: data.paid_by_id || updates.paid_by_id || '',
      split_strategy: updates.split_strategy || 'EQUAL',
      splits: updates.splits || [],
      created_at: data.created_at || new Date().toISOString(),
    };
  }

  async getBalances(groupId: string): Promise<Record<string, number>> {
    try {
      const res = await this.request(`${API_BASE}/groups/${groupId}/balances`, {
        headers: this.authHeaders(),
      });
      if (res.ok) {
        const raw = await res.json();
        if (Array.isArray(raw)) {
          const map: Record<string, number> = {};
          raw.forEach((b: any) => {
            const amt = parseFloat(b.net_amount) || 0;
            map[b.creditor_id] = (map[b.creditor_id] || 0) + amt;
            map[b.debtor_id] = (map[b.debtor_id] || 0) - amt;
          });
          return map;
        } else if (typeof raw === 'object' && raw !== null) {
          return raw;
        }
      }
    } catch (err) {
      console.error('Failed to fetch balances:', err);
    }
    return {};
  }

  async getSimplifiedDebts(groupId: string): Promise<SettlementTransaction[]> {
    try {
      const res = await this.request(`${API_BASE}/groups/${groupId}/balances/simplified`, {
        headers: this.authHeaders(),
      });
      if (res.ok) {
        const raw = await res.json();
        const list = Array.isArray(raw) ? raw : (raw.simplified || []);
        return list.map((item: any) => ({
          version: raw.version,
          from_user_id: item.from_user_id,
          from_user_name: item.from_user_name || item.from_user_id,
          to_user_id: item.to_user_id,
          to_user_name: item.to_user_name || item.to_user_id,
          amount: parseFloat(item.amount) || 0,
          currency: raw.currency || 'USD',
        }));
      }
    } catch (err) {
      console.error('Failed to fetch simplified debts:', err);
    }
    return [];
  }

  async recordSettlement(groupId: string, payerId: string, payeeId: string, amount: number, _currency: string, version: number, key: string) {
    const res = await this.request(`${API_BASE}/groups/${groupId}/settle`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...this.authHeaders(),
      },
      body: JSON.stringify({
        from_user_id: payerId,
        to_user_id: payeeId,
        amount,
        notes: 'Settlement payment',
        expected_version: version,
        idempotency_key: key,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to record settlement' }));
      throw new Error(err.detail || 'Failed to record settlement');
    }
    return await res.json();
  }

  async getNotifications(groupId: string): Promise<Array<{ id: string; title: string; body: string }>> {
    const res = await this.request(`${API_BASE}/groups/${groupId}/notifications`, { headers: this.authHeaders() });
    if (!res.ok) throw new Error('Could not load notifications');
    return res.json();
  }

  async getSettlementHistory(groupId: string): Promise<Array<{ id: string; from_user_id: string; to_user_id: string; amount: string; reversal_of: string | null }>> {
    const res = await this.request(`${API_BASE}/groups/${groupId}/settlements`, { headers: this.authHeaders() });
    if (!res.ok) throw new Error('Could not load payment history');
    return res.json();
  }

  async reverseSettlement(groupId: string, id: string, version: number, key: string) {
    const res = await this.request(`${API_BASE}/groups/${groupId}/settlements/${id}/reverse`, {
      method: 'POST', headers: { 'Content-Type': 'application/json', ...this.authHeaders() },
      body: JSON.stringify({ expected_version: version, idempotency_key: key }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Could not reverse payment');
    }
    return res.json();
  }

  async getBalanceVersion(groupId: string): Promise<number> {
    const res = await this.request(`${API_BASE}/groups/${groupId}/balances/simplified`, { headers: this.authHeaders() });
    if (!res.ok) throw new Error('Could not load current balances');
    return (await res.json()).version;
  }

  async addMember(groupId: string, name: string, email: string): Promise<Group | null> {
    const res = await this.request(`${API_BASE}/groups/${groupId}/members`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...this.authHeaders(),
      },
      body: JSON.stringify({ user_id: email, name }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to add member' }));
      throw new Error(err.detail || 'Failed to add member');
    }
    const g = await res.json();
    return {
      id: g.id,
      name: g.name,
      currency: g.currency || 'USD',
      created_by: g.created_by_id || g.created_by || '',
      created_at: g.created_at,
      members: (g.members || []).map((m: any) => ({
        user_id: m.user_id,
        user: m.user || { id: m.user_id, name: m.user_name || name || 'Member', email: m.user_email || email || '' },
        joined_at: m.joined_at,
      })),
    };
  }

  async removeMember(groupId: string, userId: string): Promise<boolean> {
    const res = await this.request(`${API_BASE}/groups/${groupId}/members/${userId}`, {
      method: 'DELETE',
      headers: this.authHeaders(),
    });
    return res.ok || res.status === 204;
  }

  async sendInvitation(groupId: string, email: string): Promise<Invitation> {
    const normalizedEmail = email.trim().toLowerCase();
    const res = await this.request(`${API_BASE}/groups/${groupId}/invitations`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...this.authHeaders(),
      },
      body: JSON.stringify({ email: normalizedEmail }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to send invitation' }));
      throw new Error(err.detail || 'Failed to send invitation');
    }

    return await res.json();
  }

  async getPendingInvitations(groupId: string): Promise<Invitation[]> {
    const res = await this.request(`${API_BASE}/groups/${groupId}/invitations`, {
      headers: this.authHeaders(),
    });
    if (!res.ok) return [];
    return await res.json();
  }

  async getInvitationInfo(token: string): Promise<InvitationInfo> {
    const res = await this.request(`${API_BASE}/invitations/info/${token}`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Invitation not found or expired' }));
      throw new Error(err.detail || 'Invitation not found');
    }
    return await res.json();
  }

  async acceptInvitation(token: string): Promise<{
    group_id: string;
    user_id: string;
    group_name?: string;
    message?: string;
    access_token?: string;
    refresh_token?: string;
    user?: { id: string; name: string; email: string };
  }> {
    const res = await this.request(`${API_BASE}/invitations/accept`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to accept invitation' }));
      throw new Error(err.detail || 'Failed to accept invitation');
    }

    return await res.json();
  }

  async cancelInvitation(invitationId: string): Promise<boolean> {
    const res = await this.request(`${API_BASE}/invitations/${invitationId}`, {
      method: 'DELETE',
      headers: this.authHeaders(),
    });
    return res.ok || res.status === 204;
  }
}

export const api = new ApiClient();
