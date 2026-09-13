/**
 * frontend/src/api/client.ts
 * API Client with typed interfaces, live FastAPI integration, and mock demo fallback.
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
  balances: Record<string, number>; // user_id -> net balance (positive = owed to them, negative = they owe)
  cached?: boolean;
}

export interface ActivityEvent {
  id: string;
  timestamp: string;
  method: string;
  endpoint: string;
  status: number;
  summary: string;
  cache_hit?: boolean;
  latency_ms: number;
}

// Initial sample seed data for warm first-impression demo
export const SEED_USERS: User[] = [
  { id: 'usr_claude', name: 'Claude Vance', email: 'claude@anthropic.internal', phone: '+1 555-0101' },
  { id: 'usr_elena', name: 'Elena Rostova', email: 'elena@arch.studio', phone: '+1 555-0102' },
  { id: 'usr_marcus', name: 'Marcus Chen', email: 'marcus@mit.edu', phone: '+1 555-0103' },
  { id: 'usr_sophia', name: 'Sophia Miller', email: 'sophia@editorial.co', phone: '+1 555-0104' },
];

export const SEED_GROUPS: Group[] = [
  {
    id: 'grp_kyoto',
    name: 'Kyoto Architecture Trip',
    currency: 'USD',
    created_by: 'usr_claude',
    created_at: new Date(Date.now() - 86400000 * 5).toISOString(),
    members: SEED_USERS.map((u) => ({ user_id: u.id, user: u, joined_at: new Date().toISOString() })),
  },
  {
    id: 'grp_flatshare',
    name: 'Loft Flatmates 402',
    currency: 'USD',
    created_by: 'usr_elena',
    created_at: new Date(Date.now() - 86400000 * 20).toISOString(),
    members: [
      { user_id: 'usr_claude', user: SEED_USERS[0], joined_at: new Date().toISOString() },
      { user_id: 'usr_elena', user: SEED_USERS[1], joined_at: new Date().toISOString() },
      { user_id: 'usr_marcus', user: SEED_USERS[2], joined_at: new Date().toISOString() },
    ],
  },
];

export const SEED_EXPENSES: Expense[] = [
  {
    id: 'exp_01',
    group_id: 'grp_kyoto',
    description: 'Ryokan Machiya Lodging (3 nights)',
    amount: 1200.0,
    currency: 'USD',
    paid_by_id: 'usr_claude',
    paid_by: SEED_USERS[0],
    split_strategy: 'EQUAL',
    splits: SEED_USERS.map((u) => ({ user_id: u.id, amount: 300.0 })),
    created_at: new Date(Date.now() - 86400000 * 3).toISOString(),
  },
  {
    id: 'exp_02',
    group_id: 'grp_kyoto',
    description: 'Kaiseki Dinner at Gion',
    amount: 480.0,
    currency: 'USD',
    paid_by_id: 'usr_elena',
    paid_by: SEED_USERS[1],
    split_strategy: 'EQUAL',
    splits: SEED_USERS.map((u) => ({ user_id: u.id, amount: 120.0 })),
    created_at: new Date(Date.now() - 86400000 * 2).toISOString(),
  },
  {
    id: 'exp_03',
    group_id: 'grp_kyoto',
    description: 'Shinkansen Bullet Train Tickets',
    amount: 640.0,
    currency: 'USD',
    paid_by_id: 'usr_marcus',
    paid_by: SEED_USERS[2],
    split_strategy: 'EQUAL',
    splits: SEED_USERS.map((u) => ({ user_id: u.id, amount: 160.0 })),
    created_at: new Date(Date.now() - 86400000 * 1).toISOString(),
  },
];

// In-memory demo store stored in localStorage for continuity
class DemoStore {
  users: User[] = SEED_USERS;
  groups: Group[] = SEED_GROUPS;
  expenses: Expense[] = SEED_EXPENSES;
  events: ActivityEvent[] = [];

  constructor() {
    this.load();
    if (this.events.length === 0) {
      this.logEvent('GET', '/healthz', 200, 'Infrastructure healthy (Postgres + Redis)', false, 4);
      this.logEvent('GET', '/groups/grp_kyoto/balances', 200, 'Read group balances', true, 2);
    }
  }

  private load() {
    try {
      const savedUsers = localStorage.getItem('sw_users');
      const savedGroups = localStorage.getItem('sw_groups');
      const savedExpenses = localStorage.getItem('sw_expenses');
      if (savedUsers) this.users = JSON.parse(savedUsers);
      if (savedGroups) this.groups = JSON.parse(savedGroups);
      if (savedExpenses) this.expenses = JSON.parse(savedExpenses);
    } catch {
      // ignore
    }
  }

  save() {
    try {
      localStorage.setItem('sw_users', JSON.stringify(this.users));
      localStorage.setItem('sw_groups', JSON.stringify(this.groups));
      localStorage.setItem('sw_expenses', JSON.stringify(this.expenses));
    } catch {
      // ignore
    }
  }

  logEvent(method: string, endpoint: string, status: number, summary: string, cache_hit = false, latency_ms = 12) {
    const event: ActivityEvent = {
      id: 'evt_' + Math.random().toString(36).substring(2, 9),
      timestamp: new Date().toLocaleTimeString(),
      method,
      endpoint,
      status,
      summary,
      cache_hit,
      latency_ms,
    };
    this.events = [event, ...this.events.slice(0, 19)];
  }

  computeBalances(groupId: string): Record<string, number> {
    const groupExpenses = this.expenses.filter((e) => e.group_id === groupId);
    const balances: Record<string, number> = {};

    // Initialize all members with 0
    const group = this.groups.find((g) => g.id === groupId);
    if (group) {
      group.members.forEach((m) => {
        balances[m.user_id] = 0;
      });
    }

    for (const exp of groupExpenses) {
      // Payer gets credited
      balances[exp.paid_by_id] = (balances[exp.paid_by_id] || 0) + exp.amount;

      // Each borrower gets debited according to splits
      exp.splits.forEach((s) => {
        balances[s.user_id] = (balances[s.user_id] || 0) - (s.amount || 0);
      });
    }

    // Round to 2 decimals
    for (const k of Object.keys(balances)) {
      balances[k] = Math.round(balances[k] * 100) / 100;
    }

    return balances;
  }

  simplifyDebts(groupId: string): SettlementTransaction[] {
    const balances = this.computeBalances(groupId);
    const debtors: { id: string; amount: number }[] = [];
    const creditors: { id: string; amount: number }[] = [];

    for (const [userId, bal] of Object.entries(balances)) {
      if (bal < -0.009) {
        debtors.push({ id: userId, amount: -bal });
      } else if (bal > 0.009) {
        creditors.push({ id: userId, amount: bal });
      }
    }

    // Sort descending by magnitude (Greedy Net-Flow)
    debtors.sort((a, b) => b.amount - a.amount);
    creditors.sort((a, b) => b.amount - a.amount);

    const transactions: SettlementTransaction[] = [];
    let i = 0;
    let j = 0;

    const group = this.groups.find((g) => g.id === groupId);
    const currency = group?.currency || 'USD';

    while (i < debtors.length && j < creditors.length) {
      const debtor = debtors[i];
      const creditor = creditors[j];
      const settleAmount = Math.min(debtor.amount, creditor.amount);

      if (settleAmount > 0.009) {
        const debtorUser = this.users.find((u) => u.id === debtor.id);
        const creditorUser = this.users.find((u) => u.id === creditor.id);

        transactions.push({
          from_user_id: debtor.id,
          from_user_name: debtorUser?.name || debtor.id,
          to_user_id: creditor.id,
          to_user_name: creditorUser?.name || creditor.id,
          amount: Math.round(settleAmount * 100) / 100,
          currency,
        });
      }

      debtor.amount -= settleAmount;
      creditor.amount -= settleAmount;

      if (debtor.amount <= 0.009) i++;
      if (creditor.amount <= 0.009) j++;
    }

    return transactions;
  }
}

export const demoStore = new DemoStore();

// Live API and configuration state
const API_BASE = '/api';

export class ApiClient {
  private token: string | null = localStorage.getItem('sw_token');
  public isDemoMode: boolean = true; // Defaults to high-fidelity demo, auto checks live backend on load

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
      // Accept 200 (ok or degraded) — DB is alive, Redis is optional
      if (res.ok || data?.services?.database === 'ok') {
        this.isDemoMode = false;
        const dbStatus = data?.status || 'ok';
        demoStore.logEvent('GET', '/healthz', 200, `Live FastAPI (${dbStatus}) — Supabase PostgreSQL`, false, 5);
        return true;
      }
    } catch {
      // Backend not running or timed out; stay in demo mode
    }
    this.isDemoMode = true;
    return false;
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

  async getGroups(): Promise<Group[]> {
    if (this.isDemoMode) {
      demoStore.logEvent('GET', '/groups/', 200, 'Loaded groups (in-memory demo store)', true, 3);
      return [...demoStore.groups];
    }
    try {
      const res = await fetch(`${API_BASE}/groups/`, {
        headers: this.token ? { Authorization: `Bearer ${this.token}` } : {},
      });
      if (res.ok) {
        demoStore.logEvent('GET', '/groups/', res.status, 'Retrieved live groups list', false, 15);
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
      }
    } catch (err) {
      console.warn('Backend unavailable, fallback to demo groups', err);
    }
    return [...demoStore.groups];
  }

  async createGroup(name: string, currency: string, createdBy: string): Promise<Group> {
    if (this.isDemoMode) {
      const newGroup: Group = {
        id: 'grp_' + Math.random().toString(36).substring(2, 8),
        name,
        currency,
        created_by: createdBy,
        created_at: new Date().toISOString(),
        members: demoStore.users.map((u) => ({ user_id: u.id, user: u, joined_at: new Date().toISOString() })),
      };
      demoStore.groups.unshift(newGroup);
      demoStore.save();
      demoStore.logEvent('POST', '/groups/', 201, `Created group: "${name}"`, false, 6);
      return newGroup;
    }
    const res = await fetch(`${API_BASE}/groups/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}),
      },
      body: JSON.stringify({ name, description: `Currency: ${currency}` }),
    });
    const g = await res.json();
    demoStore.logEvent('POST', '/groups/', res.status, `Created group: "${name}"`, false, 28);
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
    if (this.isDemoMode) {
      const list = demoStore.expenses.filter((e) => e.group_id === groupId);
      demoStore.logEvent('GET', `/groups/${groupId}/expenses`, 200, `Fetched ${list.length} expenses`, true, 2);
      return list;
    }
    try {
      const res = await fetch(`${API_BASE}/groups/${groupId}/expenses`, {
        headers: this.token ? { Authorization: `Bearer ${this.token}` } : {},
      });
      if (res.ok) {
        demoStore.logEvent('GET', `/groups/${groupId}/expenses`, 200, 'Loaded live expenses', false, 18);
        const data = await res.json();
        return data.map((exp: any) => ({
          id: exp.id,
          group_id: exp.group_id,
          description: exp.description,
          amount: parseFloat(exp.amount) || 0,
          currency: 'USD',
          paid_by_id: exp.paid_by_id,
          paid_by: demoStore.users.find((u) => u.id === exp.paid_by_id),
          split_strategy: (exp.split_type === 'percent' ? 'PERCENTAGE' : exp.split_type === 'exact' ? 'EXACT' : 'EQUAL') as SplitStrategy,
          splits: (exp.splits || []).map((s: any) => ({
            user_id: s.user_id,
            amount: parseFloat(s.owed_amount) || 0,
            percentage: s.percentage ? parseFloat(s.percentage) : undefined,
          })),
          created_at: exp.created_at || new Date().toISOString(),
        }));
      }
    } catch (err) {
      console.warn('API error, fallback to demo expenses', err);
    }
    return demoStore.expenses.filter((e) => e.group_id === groupId);
  }

  async createExpense(expense: Omit<Expense, 'id' | 'created_at'>): Promise<Expense> {
    if (this.isDemoMode) {
      const newExp: Expense = {
        ...expense,
        id: 'exp_' + Math.random().toString(36).substring(2, 8),
        created_at: new Date().toISOString(),
        paid_by: demoStore.users.find((u) => u.id === expense.paid_by_id),
      };
      demoStore.expenses.unshift(newExp);
      demoStore.save();
      demoStore.logEvent('POST', `/groups/${expense.group_id}/expenses`, 201, `Added "${newExp.description}" ($${newExp.amount})`, false, 7);
      demoStore.logEvent('DEL', `cache:balance:${expense.group_id}`, 200, 'Invalidated Redis balance cache (Write-Invalidate)', false, 1);
      return newExp;
    }

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
        ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}),
      },
      body: JSON.stringify(backendPayload),
    });
    const data = await res.json();
    demoStore.logEvent('POST', `/groups/${expense.group_id}/expenses`, res.status, `Added expense`, false, 32);

    return {
      id: data.id,
      group_id: data.group_id,
      description: data.description,
      amount: parseFloat(data.amount) || expense.amount,
      currency: expense.currency || 'USD',
      paid_by_id: data.paid_by_id,
      paid_by: demoStore.users.find((u) => u.id === data.paid_by_id),
      split_strategy: expense.split_strategy,
      splits: Array.isArray(data.splits)
        ? data.splits.map((s: any) => ({ user_id: s.user_id, amount: parseFloat(s.owed_amount) || 0 }))
        : expense.splits,
      created_at: data.created_at || new Date().toISOString(),
    };
  }

  async deleteExpense(expenseId: string, groupId: string): Promise<void> {
    if (this.isDemoMode) {
      const idx = demoStore.expenses.findIndex((e) => e.id === expenseId);
      if (idx !== -1) {
        const exp = demoStore.expenses[idx];
        demoStore.expenses.splice(idx, 1);
        demoStore.save();
        demoStore.logEvent('DELETE', `/groups/${groupId}/expenses/${expenseId}`, 200, `Deleted "${exp.description}"`, false, 5);
        demoStore.logEvent('DEL', `cache:balance:${groupId}`, 200, 'Invalidated Redis balance cache', false, 1);
      }
      return;
    }
    const res = await fetch(`${API_BASE}/groups/${groupId}/expenses/${expenseId}`, {
      method: 'DELETE',
      headers: this.token ? { Authorization: `Bearer ${this.token}` } : {},
    });
    demoStore.logEvent('DELETE', `/groups/${groupId}/expenses/${expenseId}`, res.status, 'Deleted expense', false, 20);
  }

  async updateExpense(expenseId: string, groupId: string, updates: {
    description?: string;
    amount?: number;
    paid_by_id?: string;
    split_strategy?: SplitStrategy;
    splits?: SplitItem[];
  }): Promise<Expense> {
    if (this.isDemoMode) {
      const idx = demoStore.expenses.findIndex((e) => e.id === expenseId);
      if (idx === -1) throw new Error('Expense not found');
      const updated: Expense = {
        ...demoStore.expenses[idx],
        ...updates,
        paid_by: updates.paid_by_id
          ? demoStore.users.find((u) => u.id === updates.paid_by_id)
          : demoStore.expenses[idx].paid_by,
      };
      demoStore.expenses[idx] = updated;
      demoStore.save();
      demoStore.logEvent('PATCH', `/groups/${groupId}/expenses/${expenseId}`, 200, `Updated "${updated.description}"`, false, 8);
      demoStore.logEvent('DEL', `cache:balance:${groupId}`, 200, 'Invalidated Redis balance cache', false, 1);
      return updated;
    }
    const res = await fetch(`${API_BASE}/groups/${groupId}/expenses/${expenseId}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}),
      },
      body: JSON.stringify({
        description: updates.description,
        amount: updates.amount,
        paid_by_id: updates.paid_by_id,
      }),
    });
    const data = await res.json();
    demoStore.logEvent('PATCH', `/groups/${groupId}/expenses/${expenseId}`, res.status, 'Updated expense', false, 28);
    return {
      ...updates,
      id: data.id,
      group_id: data.group_id || groupId,
      description: data.description || updates.description || '',
      amount: parseFloat(data.amount) || updates.amount || 0,
      currency: 'USD',
      paid_by_id: data.paid_by_id || updates.paid_by_id || '',
      paid_by: demoStore.users.find((u) => u.id === (data.paid_by_id || updates.paid_by_id)),
      split_strategy: updates.split_strategy || 'EQUAL',
      splits: updates.splits || [],
      created_at: data.created_at || new Date().toISOString(),
    };
  }

  async getBalances(groupId: string): Promise<Record<string, number>> {
    if (this.isDemoMode) {
      const b = demoStore.computeBalances(groupId);
      demoStore.logEvent('GET', `/groups/${groupId}/balances`, 200, 'Retrieved computed group ledger balances', true, 1);
      return b;
    }
    try {
      const res = await fetch(`${API_BASE}/groups/${groupId}/balances`, {
        headers: this.token ? { Authorization: `Bearer ${this.token}` } : {},
      });
      if (res.ok) {
        demoStore.logEvent('GET', `/groups/${groupId}/balances`, 200, 'Loaded live balances (cached in Redis)', true, 6);
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
    } catch {
      // fallback
    }
    return demoStore.computeBalances(groupId);
  }

  async getSimplifiedDebts(groupId: string): Promise<SettlementTransaction[]> {
    if (this.isDemoMode) {
      const txs = demoStore.simplifyDebts(groupId);
      demoStore.logEvent('GET', `/groups/${groupId}/balances/simplified`, 200, `Greedy Net-Flow: ${txs.length} minimum settlements`, false, 4);
      return txs;
    }
    try {
      const res = await fetch(`${API_BASE}/groups/${groupId}/balances/simplified`, {
        headers: this.token ? { Authorization: `Bearer ${this.token}` } : {},
      });
      if (res.ok) {
        demoStore.logEvent('GET', `/groups/${groupId}/balances/simplified`, 200, 'Computed simplified settlement graph', false, 12);
        const raw = await res.json();
        const list = Array.isArray(raw) ? raw : (raw.simplified || []);
        const group = demoStore.groups.find((g) => g.id === groupId);
        return list.map((item: any) => ({
          from_user_id: item.from_user_id,
          from_user_name:
            group?.members.find((m) => m.user_id === item.from_user_id)?.user.name ||
            demoStore.users.find((u) => u.id === item.from_user_id)?.name ||
            item.from_user_id,
          to_user_id: item.to_user_id,
          to_user_name:
            group?.members.find((m) => m.user_id === item.to_user_id)?.user.name ||
            demoStore.users.find((u) => u.id === item.to_user_id)?.name ||
            item.to_user_id,
          amount: parseFloat(item.amount) || 0,
          currency: group?.currency || 'USD',
        }));
      }
    } catch {
      // fallback
    }
    return demoStore.simplifyDebts(groupId);
  }

  async recordSettlement(groupId: string, payerId: string, payeeId: string, amount: number, currency: string) {
    if (this.isDemoMode) {
      // Settle creates an offsetting expense/transfer
      const payer = demoStore.users.find((u) => u.id === payerId);
      const payee = demoStore.users.find((u) => u.id === payeeId);
      const settleExpense: Expense = {
        id: 'settle_' + Math.random().toString(36).substring(2, 8),
        group_id: groupId,
        description: `Settlement: ${payer?.name || payerId} paid ${payee?.name || payeeId}`,
        amount,
        currency,
        paid_by_id: payerId,
        paid_by: payer,
        split_strategy: 'EXACT',
        splits: [{ user_id: payeeId, amount }],
        created_at: new Date().toISOString(),
      };
      demoStore.expenses.unshift(settleExpense);
      demoStore.save();
      demoStore.logEvent('POST', `/groups/${groupId}/settle`, 201, `Recorded settlement of $${amount}`, false, 8);
      demoStore.logEvent('DEL', `cache:balance:${groupId}`, 200, 'Invalidated Redis cache on settlement', false, 1);
      return settleExpense;
    }
    const res = await fetch(`${API_BASE}/groups/${groupId}/settle`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}),
      },
      body: JSON.stringify({
        from_user_id: payerId,
        to_user_id: payeeId,
        amount,
        notes: 'Settlement payment',
      }),
    });
    demoStore.logEvent('POST', `/groups/${groupId}/settle`, res.status, `Settlement recorded`, false, 24);
    return await res.json();
  }

  async addMember(groupId: string, name: string, email: string): Promise<Group | null> {
    if (this.isDemoMode) {
      const group = demoStore.groups.find((g) => g.id === groupId);
      if (!group) return null;

      // Check for duplicate email
      const existingUser = demoStore.users.find((u) => u.email === email);
      if (existingUser && group.members.some((m) => m.user_id === existingUser.id)) {
        throw new Error('This person is already a member of this group.');
      }

      // Create or reuse user
      const user: User = existingUser || {
        id: 'usr_' + Math.random().toString(36).substring(2, 8),
        name,
        email,
      };

      if (!existingUser) {
        demoStore.users.push(user);
      }

      group.members.push({
        user_id: user.id,
        user,
        joined_at: new Date().toISOString(),
      });

      demoStore.save();
      demoStore.logEvent('POST', `/groups/${groupId}/members`, 200, `Added member "${name}"`, false, 6);
      return { ...group };
    }

    const res = await fetch(`${API_BASE}/groups/${groupId}/members`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}),
      },
      body: JSON.stringify({ user_id: email }), // Backend expects user_id
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to add member' }));
      throw new Error(err.detail || 'Failed to add member');
    }
    demoStore.logEvent('POST', `/groups/${groupId}/members`, res.status, `Added member`, false, 18);
    const g = await res.json();
    return {
      id: g.id,
      name: g.name,
      currency: g.currency || 'USD',
      created_by: g.created_by_id || g.created_by || '',
      created_at: g.created_at,
      members: (g.members || []).map((m: any) => ({
        user_id: m.user_id,
        user: m.user || { id: m.user_id, name: m.user_name || 'Member', email: m.user_email || '' },
        joined_at: m.joined_at,
      })),
    };
  }

  async removeMember(groupId: string, userId: string): Promise<boolean> {
    if (this.isDemoMode) {
      const group = demoStore.groups.find((g) => g.id === groupId);
      if (!group) return false;

      const idx = group.members.findIndex((m) => m.user_id === userId);
      if (idx === -1) return false;

      const memberName = group.members[idx].user?.name || 'Member';
      group.members.splice(idx, 1);
      demoStore.save();
      demoStore.logEvent('DELETE', `/groups/${groupId}/members/${userId}`, 204, `Removed member "${memberName}"`, false, 5);
      return true;
    }

    const res = await fetch(`${API_BASE}/groups/${groupId}/members/${userId}`, {
      method: 'DELETE',
      headers: this.token ? { Authorization: `Bearer ${this.token}` } : {},
    });
    demoStore.logEvent('DELETE', `/groups/${groupId}/members/${userId}`, res.status, 'Removed member', false, 15);
    return res.ok || res.status === 204;
  }
}

export const api = new ApiClient();

