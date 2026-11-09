/** qAIUIck Core v0.2: tiny, safe, zero-dependency, no-build UI bindings. */
const SEGMENT = /^[A-Za-z_$][A-Za-z0-9_$]*$/;
const BLOCKED = new Set(['__proto__', 'prototype', 'constructor']);

export function pathSegments(path) {
  if (typeof path !== 'string' || !path || path.length > 200) throw new Error('Invalid qAIUIck path');
  const segments = path.split('.');
  if (segments.length > 12 || segments.some((s) => !SEGMENT.test(s) || BLOCKED.has(s))) {
    throw new Error(`Unsafe or unsupported binding path: ${path}`);
  }
  return segments;
}

export function getPath(object, path) {
  return pathSegments(path).reduce((value, key) => {
    if (value == null || !Object.prototype.hasOwnProperty.call(Object(value), key)) return undefined;
    return value[key];
  }, object);
}

export function setPath(object, path, value) {
  const segments = pathSegments(path);
  let cursor = object;
  for (const segment of segments.slice(0, -1)) {
    if (!Object.prototype.hasOwnProperty.call(cursor, segment) ||
        cursor[segment] === null || typeof cursor[segment] !== 'object') {
      throw new Error(`Missing state object at ${segment}`);
    }
    cursor = cursor[segment];
  }
  cursor[segments.at(-1)] = value;
  return value;
}

export function createApp({ root, state = {}, computed = {}, actions = {}, onError = console.error } = {}) {
  if (typeof document === 'undefined') throw new Error('createApp requires a browser DOM');
  const host = typeof root === 'string' ? document.querySelector(root) : root;
  if (!host || !(host instanceof Element)) throw new Error('qAIUIck root not found');
  if (!state || typeof state !== 'object' || Array.isArray(state)) throw new Error('state must be an object');
  if (!computed || typeof computed !== 'object' || Array.isArray(computed)) throw new Error('computed must be an object');
  for (const [key, derive] of Object.entries(computed)) {
    if (pathSegments(key).length !== 1 || Object.prototype.hasOwnProperty.call(state, key)) {
      throw new Error(`Computed name must be a unique single identifier: ${key}`);
    }
    if (typeof derive !== 'function') throw new Error(`Computed value must be a function: ${key}`);
  }

  const rowContexts = new WeakMap();
  const templates = [...host.querySelectorAll('template[q-each]')].map((element) => ({
    element, path: element.getAttribute('q-each'), as: element.getAttribute('q-as') || 'item', nodes: [],
  }));
  for (const template of templates) {
    pathSegments(template.path);
    pathSegments(template.as);
    if (template.as.includes('.')) throw new Error('q-as must be a single identifier');
  }
  let disposed = false;
  let derived = Object.create(null);

  function contextFor(element) {
    for (let current = element; current && current !== host.parentNode; current = current.parentNode) {
      if (rowContexts.has(current)) return rowContexts.get(current);
    }
    return null;
  }
  function valueOf(element, path) {
    const context = contextFor(element);
    const prefix = pathSegments(path)[0];
    return context && Object.prototype.hasOwnProperty.call(context, prefix)
      ? getPath(context, path)
      : (Object.prototype.hasOwnProperty.call(derived, prefix) ? getPath(derived, path) : getPath(state, path));
  }

  function render({ preserveFocusedInput = false } = {}) {
    if (disposed) return;
    derived = Object.create(null);
    for (const [name, derive] of Object.entries(computed)) derived[name] = derive(state);
    for (const template of templates) {
      for (const node of template.nodes) node.remove();
      template.nodes = [];
      const items = Object.prototype.hasOwnProperty.call(derived, template.path.split('.')[0])
        ? getPath(derived, template.path) : getPath(state, template.path);
      if (items == null) continue;
      if (!Array.isArray(items)) throw new Error(`q-each expects an array: ${template.path}`);
      const fragment = document.createDocumentFragment();
      for (const [index, item] of items.entries()) {
        const copy = template.element.content.cloneNode(true);
        const roots = [...copy.childNodes];
        const context = Object.assign(Object.create(null), { [template.as]: item, index });
        for (const node of roots) if (node.nodeType === 1) rowContexts.set(node, context);
        template.nodes.push(...roots);
        fragment.append(copy);
      }
      template.element.parentNode.insertBefore(fragment, template.element.nextSibling);
    }
    const elements = [host, ...host.querySelectorAll('[q-text],[q-show],[q-model]')];
    for (const el of elements) {
      if (el.hasAttribute('q-text')) {
        const value = valueOf(el, el.getAttribute('q-text'));
        el.textContent = value == null ? '' : String(value); // Never interpret user text as HTML.
      }
      if (el.hasAttribute('q-show')) {
        el.hidden = !Boolean(valueOf(el, el.getAttribute('q-show')));
      }
      if (el.hasAttribute('q-model')) {
        const value = getPath(state, el.getAttribute('q-model'));
        if (el.type === 'checkbox') el.checked = Boolean(value);
        else if ((!preserveFocusedInput || document.activeElement !== el) && el.value !== String(value ?? '')) el.value = String(value ?? '');
      }
    }
  }

  function report(error) { try { onError(error); } catch (_) { /* keep DOM listener safe */ } }
  async function invoke(el, directive, event) {
    if (!el || !host.contains(el)) return;
    const actionName = el.getAttribute(directive);
    const handler = Object.prototype.hasOwnProperty.call(actions, actionName) ? actions[actionName] : undefined;
    if (typeof handler !== 'function' || BLOCKED.has(actionName)) {
      report(new Error(`Unknown action: ${actionName}`)); return;
    }
    const argPath = el.getAttribute('q-arg');
    try {
      if (el.disabled) return;
      const arg = argPath ? valueOf(el, argPath) : undefined;
      await handler(state, { arg, event, app });
      render();
    } catch (error) { report(error); }
  }
  function click(event) {
    const el = event.target instanceof Element ? event.target.closest('[q-action]') : null;
    if (el) void invoke(el, 'q-action', event);
  }
  function submit(event) {
    const form = event.target;
    if (!(form instanceof Element) || !host.contains(form) || !form.hasAttribute('q-submit')) return;
    event.preventDefault(); // Enter works in forms; no page reload.
    void invoke(form, 'q-submit', event);
  }
  function input(event) {
    const el = event.target;
    if (!(el instanceof Element) || !host.contains(el) || !el.hasAttribute('q-model')) return;
    try {
      const path = el.getAttribute('q-model');
      setPath(state, path, el.type === 'checkbox' ? el.checked : el.value);
      render({ preserveFocusedInput: true });
    } catch (error) { report(error); }
  }

  const app = {
    state,
    render,
    set(path, value) { setPath(state, path, value); render(); },
    destroy() { disposed = true; host.removeEventListener('click', click); host.removeEventListener('submit', submit); host.removeEventListener('input', input); },
  };
  host.addEventListener('submit', submit);
  host.addEventListener('click', click);
  host.addEventListener('input', input);
  render();
  return app;
}
