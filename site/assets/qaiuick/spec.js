/** SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
 *  SPDX-License-Identifier: MIT
 *  qAIUIck Spec: declarative application contract and deterministic AI-friendly diffs.
 *  Pure module: usable both in a browser and in Node, without evaluating HTML.
 */
const NAME = /^[A-Za-z_$][\w$]*$/;
const ID = /^[a-zA-Z0-9][a-zA-Z0-9_.-]{1,99}$/;
const FORBIDDEN = new Set(['__proto__', 'constructor', 'prototype']);
const TYPES = new Set(['text', 'number', 'date', 'textarea', 'checkbox', 'select']);
const own = (obj, key) => Object.prototype.hasOwnProperty.call(obj, key);
const record = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const fail = message => { throw new Error('qAIUIck Spec: ' + message); };

function field(name, value) {
  if (!NAME.test(name) || FORBIDDEN.has(name) || name.startsWith('$') || name === 'id')
    fail('Invalid field name: ' + name);
  let input;
  if (typeof value === 'string') {
    input = { label: value.replace(/\*$/, ''), required: value.endsWith('*'), type: 'text' };
  } else if (Array.isArray(value)) {
    input = { label: name, type: 'select', options: value };
  } else if (record(value)) {
    input = { ...value };
    input.label ??= name;
    input.type ??= (Array.isArray(input.options) ? 'select' : 'text');
  } else fail('Field must be a label, options array, or descriptor: ' + name);
  if (!TYPES.has(input.type)) fail('Unsupported field type: ' + name);
  if (typeof input.label !== 'string' || !input.label.trim() || input.label.length > 100)
    fail('Field label required: ' + name);
  if (input.type === 'select' && (!Array.isArray(input.options) ||
    !input.options.length || input.options.length > 80 ||
    input.options.some(x => typeof x !== 'string' || !x || x.length > 100) ||
    new Set(input.options).size !== input.options.length))
    fail('Select needs distinct nonempty options: ' + name);
  if ('options' in input && input.type !== 'select') fail('options require select: ' + name);
  for (const bound of ['min', 'max']) {
    if (own(input, bound) && (input.type !== 'number' || !Number.isFinite(input[bound])))
      fail('min/max must be numeric for number fields: ' + name);
  }
  if (input.min != null && input.max != null && input.min > input.max)
    fail('min must be <= max: ' + name);
  if (input.type === 'number' && input.step != null && (!Number.isFinite(input.step) || input.step <= 0))
    fail('Invalid number step: ' + name);
  if (input.maxLength != null && (!Number.isInteger(input.maxLength) || input.maxLength < 1 || input.maxLength > 10000))
    fail('Invalid maxLength: ' + name);
  if (input.default !== undefined) {
    const v = input.default;
    if (input.type === 'checkbox' && typeof v !== 'boolean') fail('Checkbox default must be boolean: ' + name);
    if (input.type === 'number' && (typeof v !== 'number' || !Number.isFinite(v)))
      fail('Number default must be numeric: ' + name);
    if (input.type === 'select' && !input.options.includes(v)) fail('Invalid select default: ' + name);
  }
  return {
    name, label: input.label, type: input.type, required: Boolean(input.required),
    ...(input.options ? { options: [...input.options] } : {}),
    ...(input.min != null ? { min: input.min } : {}),
    ...(input.max != null ? { max: input.max } : {}),
    ...(input.step != null ? { step: input.step } : {}),
    ...(input.maxLength != null ? { maxLength: input.maxLength } : {}),
    ...(input.placeholder ? { placeholder: String(input.placeholder) } : {}),
    default: input.default ?? (input.type === 'checkbox' ? false : input.type === 'number' ? 0 : input.type === 'select' ? input.options[0] : ''),
  };
}

function names(list, available, label) {
  if (!Array.isArray(list) || !list.every(x => available.includes(x)) || new Set(list).size !== list.length)
    fail(label + ' must contain distinct, defined field names');
  return [...list];
}

export function normalizeSpec(spec) {
  if (!record(spec)) fail('Specification must be an object');
  if (!ID.test(spec.id ?? '')) fail('id must be a stable ASCII identifier (2-100 chars)');
  if (!Number.isInteger(spec.version) || spec.version < 1) fail('version must be a positive integer');
  if (typeof spec.title !== 'string' || !spec.title.trim()) fail('title required');
  if (!record(spec.fields) || !Object.keys(spec.fields).length || Object.keys(spec.fields).length > 30)
    fail('fields must contain 1 to 30 definitions');
  const fields = Object.entries(spec.fields).map(([key, value]) => field(key, value));
  const ids = fields.map(x => x.name);
  const ui = spec.ui ?? {};
  if (!record(ui)) fail('ui must be an object');
  const columns = names(ui.columns ?? ids, ids, 'ui.columns');
  const search = names(ui.search ?? [], ids, 'ui.search');
  if (!columns.length) fail('ui.columns cannot be empty');
  const sample = spec.sample ?? [];
  if (!Array.isArray(sample) || sample.length > 200 || sample.some(x => !record(x)))
    fail('sample must be a list of <=200 records');
  const seen = new Set();
  for (const [i, row] of sample.entries()) {
    const id = row.id;
    if (typeof id !== 'string' || !id || seen.has(id)) fail('sample needs unique string ids at row ' + i);
    seen.add(id);
    for (const key of Object.keys(row)) {
      if (key !== 'id' && !ids.includes(key)) fail('Unknown sample field: ' + key);
    }
  }
  const metrics = spec.metrics ?? {};
  const actions = spec.actions ?? {};
  if (!record(metrics) || !record(actions) || Object.keys(metrics).length > 12 || Object.keys(actions).length > 12)
    fail('metrics/actions must be small objects');
  for (const [key, value] of Object.entries(metrics)) {
    if (!NAME.test(key) || FORBIDDEN.has(key) || key.startsWith('$') ||
        ['items', 'count', 'empty', 'filtered', 'draft', 'query', 'editingId', 'error'].includes(key) ||
        ids.includes(key) || !record(value) ||
        typeof value.label !== 'string' || typeof value.calc !== 'function')
      fail('Invalid metric: ' + key);
  }
  for (const [key, value] of Object.entries(actions)) {
    if (!NAME.test(key) || FORBIDDEN.has(key) || key.startsWith('$') ||
        ['save', 'edit', 'remove', 'reset', 'cancel'].includes(key) ||
        !record(value) || typeof value.label !== 'string' || typeof value.run !== 'function')
      fail('Invalid action: ' + key);
  }
  if (spec.persist != null && !['local', 'memory'].includes(spec.persist))
    fail('persist must be local or memory');
  if (spec.theme != null && !['teal', 'rose', 'violet'].includes(spec.theme))
    fail('Unknown theme');
  return { ...spec, fields, columns, search, sample, metrics, actions };
}

/** Stable, serializable single-source design contract; changes include JS logic. */
export function specSnapshot(rawSpec) {
  const s = normalizeSpec(rawSpec);
  const actions = Object.fromEntries(Object.keys(s.actions).sort().map(name => {
    const action = s.actions[name];
    return [name, { label: action.label, description: action.description ?? '',
      logic: action.run.toString() }];
  }));
  const metrics = Object.fromEntries(Object.keys(s.metrics).sort().map(name => {
    const metric = s.metrics[name];
    return [name, { label: metric.label, logic: metric.calc.toString() }];
  }));
  return {
    format: 'qaiuick-spec-v1', id: s.id, version: s.version, title: s.title,
    description: s.description ?? '', persist: s.persist ?? 'local', theme: s.theme ?? 'teal',
    fields: Object.fromEntries(s.fields.map(({ name, ...rest }) => [name, rest])),
    ui: { columns: s.columns, search: s.search },
    sample: s.sample, metrics, actions,
  };
}

function flatten(value, key = '', out = {}) {
  if (Array.isArray(value)) { out[key] = JSON.stringify(value); return out; }
  if (record(value)) {
    for (const name of Object.keys(value).sort()) flatten(value[name], key ? key + '.' + name : name, out);
  } else out[key] = value;
  return out;
}

/** Compare two checked-in snapshots or two specifications, field by field. */
export function diffSpecs(before, after) {
  const left = own(before, 'format') ? before : specSnapshot(before);
  const right = own(after, 'format') ? after : specSnapshot(after);
  if (left.id !== right.id) fail('Cannot compare different application IDs');
  const a = flatten(left), b = flatten(right), keys = [...new Set([...Object.keys(a), ...Object.keys(b)])].sort();
  return keys.flatMap(path => {
    if (!own(a, path)) return [{ type: 'added', path, after: b[path] }];
    if (!own(b, path)) return [{ type: 'removed', path, before: a[path] }];
    if (a[path] !== b[path]) return [{
      type: 'changed', path,
      before: path.endsWith('.logic') ? '旧ロジック' : a[path],
      after: path.endsWith('.logic') ? '新ロジック' : b[path],
    }];
    return [];
  });
}
