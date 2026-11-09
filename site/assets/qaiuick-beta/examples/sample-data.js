/** SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
 *  SPDX-License-Identifier: MIT
 *  Demo data belongs to each browser, and is inserted only on first visit.
 */
export function storageKey(namespace) {
  return `qaiuick:${namespace}:items`;
}
export async function seedOnce(store, namespace, examples) {
  // Distinguish an empty saved list (user deleted everything) from no data.
  if (globalThis.localStorage.getItem(storageKey(namespace)) !== null) return store.list();
  for (const item of examples) await store.save(item);
  return store.list();
}
export async function resetSamples(store, examples) {
  for (const item of await store.list()) await store.remove(item.id);
  for (const item of examples) await store.save(item);
  return store.list();
}
