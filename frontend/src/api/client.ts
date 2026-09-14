/**
 * frontend/src/api/client.ts
 * FairSplit Production API Client with typed domain interfaces and live FastAPI integration.
 */

export type SplitStrategy = 'EQUAL' | 'EXACT' | 'PERCENTAGE' | 'SHARE';

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
export const API_BASE = (import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '');

export class ApiClient {
  private token: string | null = localStorage.getItem('sw_token');

  constructor() {
    this.checkLiveBackend();
  }

  async checkLiveBackend(): Promise<boolean> {
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 5000);
      const res = await fetch(`${API_BASE}/healthz`, {
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

  setToken(token: string) {
    this.token = token;
    localStorage.setItem('sw_token', token);
  }

  clearToken() {
    this.token = null;
    localStorage.removeItem('sw_token');
  }

  hasToken(): boolean {
    return !!this.token;
  }

  private authHeaders(): HeadersInit {
    return this.token ? { Authorization: `Bearer ${this.token}` } : {};
  }

  async getGroups(): Promise<Group[]> {
    try {
      const res = await fetch(`${API_BASE}/groups/`, {
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
    const res = await fetch(`${API_BASE}/groups/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...this.authHeaders(),
      },
      body: JSON.stringify({ name, description: `Currency: ${currency}` }),
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
      const res = await fetch(`${API_BASE}/groups/${groupId}/expenses`, {
        headers: this.authHeaders(),
      });
      if (!res.ok) return [];
      const data = await res.json();
      return data.map((exp: any) => ({
        id: exp.id,
        group_id: exp.group_id,
        description: exp.description,
        amount: parseFloat(exp.amount) || 0,
        currency: 'USD',
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
      new Set([expense.paid_by_id, ...expense.splits.map((s) => s.user_id)])
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

    const res = await fetch(`${API_BASE}/groups/${expense.group_id}/expenses`, {
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
      currency: expense.currency || 'USD',
      paid_by_id: data.paid_by_id,
      split_strategy: expense.split_strategy,
      splits: Array.isArray(data.splits)
        ? data.splits.map((s: any) => ({ user_id: s.user_id, amount: parseFloat(s.owed_amount) || 0 }))
        : expense.splits,
      created_at: data.created_at || new Date().toISOString(),
    };
  }

  async deleteExpense(expenseId: string, groupId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/groups/${groupId}/expenses/${expenseId}`, {
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
    const res = await fetch(`${API_BASE}/groups/${groupId}/expenses/${expenseId}`, {
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
      currency: 'USD',
      paid_by_id: data.paid_by_id || updates.paid_by_id || '',
      split_strategy: updates.split_strategy || 'EQUAL',
      splits: updates.splits || [],
      created_at: data.created_at || new Date().toISOString(),
    };
  }

  async getBalances(groupId: string): Promise<Record<string, number>> {
    try {
      const res = await fetch(`${API_BASE}/groups/${groupId}/balances`, {
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
      const res = await fetch(`${API_BASE}/groups/${groupId}/balances/simplified`, {
        headers: this.authHeaders(),
      });
      if (res.ok) {
        const raw = await res.json();
        const list = Array.isArray(raw) ? raw : (raw.simplified || []);
        return list.map((item: any) => ({
          from_user_id: item.from_user_id,
          from_user_name: item.from_user_name || item.from_user_id,
          to_user_id: item.to_user_id,
          to_user_name: item.to_user_name || item.to_user_id,
          amount: parseFloat(item.amount) || 0,
          currency: 'USD',
        }));
      }
    } catch (err) {
      console.error('Failed to fetch simplified debts:', err);
    }
    return [];
  }

  async recordSettlement(groupId: string, payerId: string, payeeId: string, amount: number, _currency: string) {
    const res = await fetch(`${API_BASE}/groups/${groupId}/settle`, {
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
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to record settlement' }));
      throw new Error(err.detail || 'Failed to record settlement');
    }
    return await res.json();
  }

  async addMember(groupId: string, name: string, email: string): Promise<Group | null> {
    const res = await fetch(`${API_BASE}/groups/${groupId}/members`, {
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
    const res = await fetch(`${API_BASE}/groups/${groupId}/members/${userId}`, {
      method: 'DELETE',
      headers: this.authHeaders(),
    });
    return res.ok || res.status === 204;
  }

  async sendInvitation(groupId: string, email: string): Promise<Invitation> {
    const normalizedEmail = email.trim().toLowerCase();
    const res = await fetch(`${API_BASE}/groups/${groupId}/invitations`, {
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
    const res = await fetch(`${API_BASE}/groups/${groupId}/invitations`, {
      headers: this.authHeaders(),
    });
    if (!res.ok) return [];
    return await res.json();
  }

  async getInvitationInfo(token: string): Promise<InvitationInfo> {
    const res = await fetch(`${API_BASE}/invitations/info/${token}`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Invitation not found or expired' }));
      throw new Error(err.detail || 'Invitation not found');
    }
    return await res.json();
  }

  async acceptInvitation(token: string): Promise<{ group_id: string; user_id: string; group_name?: string; message?: string }> {
    const res = await fetch(`${API_BASE}/invitations/accept`, {
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
    const res = await fetch(`${API_BASE}/invitations/${invitationId}`, {
      method: 'DELETE',
      headers: this.authHeaders(),
    });
    return res.ok || res.status === 204;
  }
}

export const api = new ApiClient();
