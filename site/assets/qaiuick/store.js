/** qAIUIck Store: one tiny CRUD contract with local, memory, and HTTP drivers. */
function clone(value) { return JSON.parse(JSON.stringify(value)); }
function keyOf(item) { return String(item?.id ?? ''); }
function generateId() {
  return typeof globalThis.crypto?.randomUUID === 'function'
    ? globalThis.crypto.randomUUID()
    : `local-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export function createStore({ type = 'local', namespace = 'qaiuick', resource = 'items', baseUrl = '/api', storage } = {}) {
  if (!/^[A-Za-z0-9_-]{1,60}$/.test(resource)) throw new Error('Invalid resource name');
  if (!/^[A-Za-z0-9_.-]{1,100}$/.test(namespace)) throw new Error('Invalid namespace');
  const key = `qaiuick:${namespace}:${resource}`;
  const memory = [];
  const localStorageProvider = type === 'local' ? (storage ?? globalThis.localStorage) : null;
  if (type === 'local' && !localStorageProvider) throw new Error('localStorage unavailable; use type="memory"');
  if (!['local', 'memory', 'remote'].includes(type)) throw new Error(`Unsupported store type: ${type}`);

  function readLocal() {
    if (type === 'memory') return clone(memory);
    const raw = localStorageProvider.getItem(key);
    const data = raw == null ? [] : JSON.parse(raw);
    if (!Array.isArray(data)) throw new Error(`Invalid stored data for ${key}`);
    return data;
  }
  function writeLocal(items) {
    if (type === 'memory') memory.splice(0, memory.length, ...clone(items));
    else localStorageProvider.setItem(key, JSON.stringify(items));
  }
  async function request(method, id, body) {
    const endpoint = `${baseUrl.replace(/\/$/, '')}/${resource}${id != null ? `/${encodeURIComponent(id)}` : ''}`;
    const response = await fetch(endpoint, {
      method,
      headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    });
    if (!response.ok) {
      let detail = response.statusText;
      try { detail = (await response.json()).error || detail; } catch (_) { /* non-JSON */ }
      throw new Error(`Store HTTP ${response.status}: ${detail}`);
    }
    return response.status === 204 ? null : response.json();
  }

  return {
    type,
    async list() { return type === 'remote' ? request('GET') : readLocal(); },
    async get(id) {
      if (type === 'remote') return request('GET', id);
      return readLocal().find((x) => keyOf(x) === String(id)) ?? null;
    },
    async save(item) {
      if (!item || typeof item !== 'object' || Array.isArray(item)) throw new Error('save expects an object');
      const record = clone({ ...item, id: item.id || generateId() });
      if (type === 'remote') return request('POST', undefined, record);
      const items = readLocal();
      const index = items.findIndex((x) => keyOf(x) === keyOf(record));
      if (index === -1) items.push(record); else items[index] = record;
      writeLocal(items);
      return clone(record);
    },
    async remove(id) {
      if (type === 'remote') { await request('DELETE', id); return; }
      writeLocal(readLocal().filter((x) => keyOf(x) !== String(id)));
    },
  };
}
