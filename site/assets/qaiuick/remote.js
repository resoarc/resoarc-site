/** SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
 *  SPDX-License-Identifier: MIT
 *  Same-origin loopback-only storage adapter for qAIUIck's Python SQLite server.
 */
export function sqliteStore({ base = '/api/apps' } = {}) {
  if (typeof window === 'undefined') throw new Error('SQLite adapter needs a browser');
  if (typeof base !== 'string' || base !== '/api/apps')
    throw new Error('SQLite API URL must remain same-origin at /api/apps');
  if (!['localhost', '127.0.0.1'].includes(window.location.hostname) ||
      window.location.protocol !== 'http:')
    throw new Error('SQLite server is only supported over local loopback HTTP');
  let session = null;
  async function token() {
    if (session) return session;
    const response = await fetch('/api/session', {
      cache: 'no-store', credentials: 'omit', mode: 'same-origin',
    });
    if (!response.ok) throw new Error('SQLite service is unavailable on this origin');
    const payload = await response.json();
    if (!payload?.token || payload.mode !== 'local-sqlite')
      throw new Error('Invalid SQLite service handshake');
    session = payload.token;
    return session;
  }
  async function request(method, path, body) {
    const secret = await token();
    const segments = path.split('/');
    if (!segments.length || segments.length > 2 ||
        !/^[A-Za-z0-9][A-Za-z0-9_.-]{1,99}$/.test(segments[0]) ||
        (segments.length === 2 && !['init', 'export'].includes(segments[1])))
      throw new Error('Invalid qAIUIck SQLite API path');
    const url = base + '/' + segments.map(encodeURIComponent).join('/');
    const response = await fetch(url, {
      method,
      mode: 'same-origin', credentials: 'omit', cache: 'no-store',
      headers: {
        'X-QAIUIck-Token': secret,
        ...(body ? { 'Content-Type': 'application/json' } : {}),
      },
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
    const result = await response.json().catch(() => null);
    if (!response.ok) {
      const error = new Error(result?.message || 'SQLite保存中にエラーが発生しました');
      error.code = result?.error || 'storage_error';
      error.status = response.status;
      throw error;
    }
    return result;
  }
  return {
    load: ({ key, schema, sample }) =>
      request('POST', key + '/init', { schema, sample }),
    save: ({ key, schema, items, revision }) =>
      request('PUT', key, { schema, items, revision }),
    exportData: ({ key }) => request('GET', key + '/export'),
  };
}
