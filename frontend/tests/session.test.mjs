import { test, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import ts from 'typescript';
let storage;
beforeEach(() => {
  storage = new Map([['sw_token', 'old'], ['sw_refresh_token', 'refresh']]);
  globalThis.localStorage = { getItem: k => storage.get(k) ?? null, setItem: (k,v) => storage.set(k,v), removeItem: k => storage.delete(k) };
  globalThis.window = new EventTarget();
});
async function loadClient() {
  let source = fs.readFileSync(new URL('../src/api/client.ts', import.meta.url), 'utf8');
  source = source.replaceAll('import.meta.env.VITE_API_URL', JSON.stringify('http://api.test'));
  const js = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } }).outputText;
  return (await import(`data:text/javascript;base64,${Buffer.from(js).toString('base64')}#${Math.random()}`)).api;
}
const json = (data, status = 200) => new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } });
test('concurrent expired requests share one refresh and retry with new credentials', async () => {
  let refreshes = 0;
  globalThis.fetch = async (url, options = {}) => {
    if (url.endsWith('/healthz')) return json({});
    if (url.endsWith('/auth/refresh')) {
      refreshes++; await new Promise(resolve => setTimeout(resolve, 20));
      return json({ access_token: 'new', refresh_token: 'new-refresh' });
    }
    return new Headers(options.headers).get('Authorization') === 'Bearer new' ? json([]) : json({}, 401);
  };
  const api = await loadClient();
  const result = await Promise.all([api.getNotifications('g'), api.getNotifications('g')]);
  assert.deepEqual(result, [[], []]); assert.equal(refreshes, 1);
  assert.equal(storage.get('sw_token'), 'new'); assert.equal(storage.get('sw_refresh_token'), 'new-refresh');
});
test('rejected refresh clears session and asks user to sign in', async () => {
  globalThis.fetch = async url => url.endsWith('/healthz') ? json({}) : json({}, 401);
  let expired = false; window.addEventListener('fairsplit:session-expired', () => { expired = true; });
  const api = await loadClient();
  await assert.rejects(api.getNotifications('g'));
  assert.equal(storage.has('sw_token'), false); assert.equal(storage.has('sw_refresh_token'), false); assert.equal(expired, true);
});
test('logout during renewal cannot restore the old session', async () => {
  let release;
  globalThis.fetch = async url => {
    if (url.endsWith('/healthz')) return json({});
    if (url.endsWith('/auth/refresh')) { await new Promise(resolve => { release = resolve; }); return json({ access_token: 'new', refresh_token: 'new-refresh' }); }
    return json({}, 401);
  };
  const api = await loadClient();
  const pending = api.getNotifications('g').catch(() => {});
  while (!release) await new Promise(resolve => setImmediate(resolve));
  api.clearToken(); release(); await pending;
  assert.equal(storage.has('sw_token'), false);
});

test('late renewal does not overwrite or clear a newly signed-in account', async () => {
  let release;
  globalThis.fetch = async url => {
    if (url.endsWith('/healthz')) return json({});
    if (url.endsWith('/auth/refresh')) { await new Promise(resolve => { release = resolve; }); return json({ access_token: 'old-session-renewed', refresh_token: 'old-refresh' }); }
    return json({}, 401);
  };
  const api = await loadClient();
  const pending = api.getNotifications('g').catch(() => {});
  while (!release) await new Promise(resolve => setImmediate(resolve));
  api.setToken('different-account', 'different-refresh'); release(); await pending;
  assert.equal(storage.get('sw_token'), 'different-account'); assert.equal(storage.get('sw_refresh_token'), 'different-refresh');
});
test('temporary renewal outage keeps saved session for retry', async () => {
  globalThis.fetch = async url => url.endsWith('/healthz') ? json({}) : json({}, url.endsWith('/auth/refresh') ? 503 : 401);
  const api = await loadClient(); await assert.rejects(api.getNotifications('g'), /temporarily unavailable/);
  assert.equal(storage.get('sw_token'), 'old'); assert.equal(storage.get('sw_refresh_token'), 'refresh');
});
