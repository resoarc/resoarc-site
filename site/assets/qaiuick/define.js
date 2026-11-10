/** SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
 *  SPDX-License-Identifier: MIT
 *  qAIUIck Spec-first UI generator. Safe DOM composition, no innerHTML/eval.
 *  HTML, form validation, table, search, actions, persistence and spec inspector
 *  are framework responsibilities. The author writes just one app specification.
 */
import { quickApp } from './quick.js';
import { sqliteStore } from './remote.js';
import { normalizeSpec, specSnapshot, diffSpecs, impactReport, validateRecord } from './spec.js';

const own = (value, name) => Object.prototype.hasOwnProperty.call(value, name);
const copy = value => JSON.parse(JSON.stringify(value));

function node(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === true) el.setAttribute(key, '');
    else if (value !== false && value != null) el.setAttribute(key, String(value));
  }
  for (const child of children.flat()) {
    if (child == null) continue;
    el.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return el;
}

function fieldControl(field) {
  const id = 'qf-' + field.name;
  let input;
  if (field.type === 'select') {
    input = node('select', { id, 'q-model': 'draft.' + field.name },
      field.options.map(x => node('option', { value: x }, x)));
  } else if (field.type === 'textarea') {
    input = node('textarea', { id, 'q-model': 'draft.' + field.name, rows: 2 });
  } else {
    input = node('input', {
      id, type: field.type, 'q-model': 'draft.' + field.name,
      ...(field.type === 'number' ? { step: field.step ?? 'any' } : {}),
    });
  }
  if (field.required) input.required = true;
  if (field.placeholder) input.setAttribute('placeholder', field.placeholder);
  if (field.min != null) input.setAttribute('min', field.min);
  if (field.max != null) input.setAttribute('max', field.max);
  if (field.maxLength != null) input.setAttribute('maxlength', field.maxLength);
  if (field.minLength != null) input.setAttribute('minlength', field.minLength);
  if (field.integer) input.setAttribute('step', '1');
  return node('label', { class: 'qs-field' },
    node('span', {}, field.label, field.required ? ' *' : ''), input,
    field.hint ? node('small', { class: 'qs-hint' }, field.hint) : null);
}


function formatChanges(changes) {
  if (!changes.length) return '基準仕様からの変更はありません。';
  return changes.map(change => {
    const prefix = change.type === 'added' ? '＋' : change.type === 'removed' ? '－' : '変更';
    const after = change.after === undefined ? '' : ' → ' + String(change.after);
    const before = change.before === undefined ? '' : '：' + String(change.before);
    return prefix + ' ' + change.path + before + after;
  }).join('\n');
}

function createUI(spec, config) {
  const target = config.root ?? '#app';
  const host = typeof target === 'string' ? document.querySelector(target) : target;
  if (!(host instanceof Element)) throw new Error('qAIUIck Spec root not found');
  if (host.children.length) throw new Error('Spec root must be empty (put custom content in slots)');
  host.classList.add('q-app', 'qs-app');
  host.dataset.qTheme = spec.theme ?? 'teal';
  const form = node('form', { 'q-submit': 'save', class: 'qs-form' },
    node('div', { class: 'qs-form-sections' }, spec.sections.map(section =>
      node('fieldset', { class: 'qs-form-section' },
        node('legend', {}, section.title),
        node('div', { class: 'qs-form-grid' },
          section.fields.map(name => fieldControl(spec.fields.find(f => f.name === name))))))),
    node('div', { class: 'qs-actions' },
      node('button', { type: 'submit', 'q-text': 'saveLabel' }, '追加する'),
      node('button', { type: 'button', 'q-action': 'cancel',
        class: 'q-button--quiet', 'q-show': 'editingId' }, '編集をやめる')));
  const header = node('header', { class: 'qs-header' },
    node('span', { class: 'q-eyebrow' }, 'qAIUIck SPEC • v' + spec.version),
    node('h2', {}, spec.title),
    node('p', { class: 'q-muted' }, spec.description ?? ''));
  const metrics = node('div', { class: 'qs-metrics' },
    node('div', { class: 'qs-metric' },
      node('strong', { 'q-text': 'count' }),
      node('small', {}, '登録件数')),
    Object.entries(spec.metrics).map(([name, metric]) =>
      node('div', { class: 'qs-metric' },
        node('strong', { 'q-text': name }),
        node('small', {}, metric.label))));
  const search = spec.search.length
    ? node('label', { class: 'qs-search' }, '一覧を検索',
      node('input', { type: 'search', 'q-model': 'query', placeholder: spec.search.map(name => spec.fields.find(f => f.name === name).label).join('・') }))
    : null;
  const head = node('tr', {}, ...spec.columns.map(name => node('th', { scope: 'col' }, spec.fields.find(f => f.name === name).label)), node('th', { scope: 'col' }, '操作'));
  const row = node('tr', {},
    spec.columns.map(name => node('td', { 'q-text': 'item.' + name })),
    node('td', { class: 'qs-row-actions' },
      ...(spec.detail.length ? [node('button', {
        type: 'button', class: 'q-button--small q-button--quiet',
        'q-action': 'view', 'q-arg': 'item.id',
      }, '詳細')] : []),
      node('button', { type: 'button', class: 'q-button--small q-button--quiet', 'q-action': 'edit', 'q-arg': 'item.id' }, '編集'),
      ...Object.entries(spec.actions).map(([name, action]) =>
        node('button', {
          type: 'button', class: 'q-button--small q-button--quiet',
          'q-action': name, 'q-arg': 'item.id', title: action.description ?? action.label,
        }, action.label)),
      node('button', { type: 'button', class: 'q-button--small q-button--quiet',
        'q-action': 'remove', 'q-arg': 'item.id' }, '削除')));
  const template = node('template', { 'q-each': 'filtered', 'q-as': 'item' });
  template.content.append(row);
  const table = node('div', { class: 'qs-tablewrap' },
    node('table', { class: 'q-table qs-table' },
      node('thead', {}, head),
      node('tbody', {}, template)));
  const list = node('section', { class: 'q-panel qs-panel' },
    node('div', { class: 'q-panel-heading' },
      node('h2', {}, '一覧'),
      node('span', { class: 'q-pill' },
        spec.storage === 'sqlite' ? 'このPCのSQLiteに保存' : 'データはこの端末内だけ')),
    search,
    table,
    node('p', { class: 'q-empty', 'q-show': 'filteredEmpty' }, '該当するデータがありません。'),
    node('div', { class: 'qs-bottom' },
      node('button', { type: 'button', class: 'q-button--quiet q-button--small', 'q-action': 'reset' }, '初期サンプルに戻す')));
  const formPanel = node('section', { class: 'q-panel qs-panel' },
    node('h2', {}, 'データを登録・編集'),
    form,
    node('p', { class: 'q-error', role: 'alert', 'q-text': 'error' }));
  const detailPanel = spec.detail.length
    ? node('section', { class: 'q-panel qs-panel qs-detail', 'q-show': 'showDetails' },
      node('div', { class: 'q-panel-heading' },
        node('h2', {}, 'レコード詳細'),
        node('button', { type: 'button', class: 'q-button--quiet q-button--small',
          'q-action': 'closeDetail' }, '閉じる')),
      node('dl', { class: 'qs-details-grid' },
        spec.detail.map(name => node('div', {},
          node('dt', {}, spec.fields.find(f => f.name === name).label),
          node('dd', { 'q-text': 'selectedRecord.' + name })))))
    : null;
  const schema = specSnapshot(config);
  const json = JSON.stringify(schema, null, 2);
  const specText = node('pre', { class: 'qs-code', tabindex: '0' }, json);
  const changes = node('pre', { class: 'qs-code qs-diff', tabindex: '0' }, '基準仕様を確認中…');
  const impacts = node('div', { class: 'qs-impact' }, '影響範囲を確認中…');
  const copyButton = node('button', { type: 'button', class: 'q-button--quiet q-button--small' }, '仕様JSONをコピー');
  copyButton.addEventListener('click', async () => {
    try { await navigator.clipboard.writeText(json); copyButton.textContent = 'コピーしました'; }
    catch (_) { copyButton.textContent = 'コピー不可：下のJSONを選択してください'; }
  });
  const inspector = node('details', { class: 'q-panel qs-inspector' },
    node('summary', {}, '実装仕様とAIの変更差分を確認'),
    node('p', { class: 'q-muted' }, '画面・項目・操作・実装ロジックをJSONで説明できます。保存済みの基準仕様との差分も表示します。'),
    copyButton,
    node('h3', {}, '実装仕様'), specText,
    node('h3', {}, '基準仕様からの変更'), changes,
    node('h3', {}, '変更の影響と推奨試験'), impacts);
  // Position hooks are actual insertion points, not an append-only footer.
  const slot = (position, where) => {
    const hook = config.slots?.[position];
    if (!hook) return;
    if (typeof hook !== 'function') throw new Error('Slot must be a function');
    const result = hook({ node, spec: schema });
    if (result instanceof Node) where.push(result);
    else if (result != null) where.push(node('p', {}, String(result)));
  };
  const beforeForm = [], afterList = [];
  slot('beforeForm', beforeForm);
  slot('afterList', afterList);
  host.append(header, metrics, ...beforeForm, formPanel, list, detailPanel, ...afterList, inspector);
  if (config.baseline) {
    const url = new URL(config.baseline, document.baseURI);
    if (url.origin !== location.origin) throw new Error('Baseline must be same-origin');
    void fetch(url, { credentials: 'omit' }).then(async response => {
      if (!response.ok) throw new Error('HTTP ' + response.status);
      const before = await response.json();
      const report = impactReport(before, schema);
      changes.textContent = formatChanges(report.changes);
      impacts.replaceChildren(...(
        report.impacts.length ? report.impacts.map(item =>
          node('p', {},
            node('strong', {}, item.area + '：'),
            item.test, item.risk === '要確認' ? '（要確認）' : ''))
          : [node('p', {}, '基準仕様からの変更はありません。')]
      ));
    }).catch(error => {
      changes.textContent = '基準仕様を取得できません: ' + error.message;
      impacts.textContent = '比較不能のため、影響範囲を確定できません。';
    });
  } else {
    changes.textContent = '比較対象がありません。CLIで保存した基準仕様を指定できます。';
    impacts.textContent = '基準仕様が指定されていないため、影響分析は未実施です。';
  }
  return { host, schema };
}

/** Build a complete, accessible CRUD app from one readable specification. */
export function defineApp(config) {
  const spec = normalizeSpec(config);
  const { host, schema } = createUI(spec, config);
  const draft = Object.fromEntries(spec.fields.map(field => [field.name, field.default]));
  const custom = Object.fromEntries(Object.entries(spec.actions).map(([name, action]) => [
    name,
    async function(id) {
      const row = this.items.find(item => String(item.id) === String(id));
      if (!row) return this.$error('対象レコードが見つかりません');
      const api = {
        record: copy(row), records: copy(this.items),
        update: (key, changes) => this.$update(key, changes),
        add: value => this.$add(value),
        remove: key => this.$remove(key),
      };
      await action.run(api);
      this.error = '';
    },
  ]));
  const app = quickApp({
    root: host,
    key: spec.id,
    persist: spec.storage === 'sqlite' ? 'remote' : (spec.storage ?? spec.persist ?? 'local'),
    ...(spec.storage === 'sqlite' ? { storage: sqliteStore(), schema } : {}),
    sample: spec.sample,
    data: { draft, query: '', editingId: '', selectedId: '' },
    computed: {
      ...Object.fromEntries(Object.entries(spec.metrics).map(([name, metric]) =>
        [name, state => metric.calc(state.items)])),
      filtered: state => {
        const query = state.query.trim().toLocaleLowerCase('ja-JP');
        return !query ? state.items : state.items.filter(row =>
          spec.search.some(name => String(row[name] ?? '').toLocaleLowerCase('ja-JP').includes(query)));
      },
      filteredEmpty: state => {
        const query = state.query.trim().toLocaleLowerCase('ja-JP');
        return !state.items.some(row => !query ||
          spec.search.some(name => String(row[name] ?? '').toLocaleLowerCase('ja-JP').includes(query)));
      },
      saveLabel: state => state.editingId ? '更新する' : '追加する',
      selectedRecord: state => state.items.find(item => String(item.id) === String(state.selectedId)) ?? {},
      showDetails: state => Boolean(state.selectedId) &&
        state.items.some(item => String(item.id) === String(state.selectedId)),
    },
    actions: {
      save() {
        let record;
        try { record = validateRecord(spec, this.draft, this.items, this.editingId); }
        catch (error) { return this.$error(error.message); }
        if (this.editingId) {
          this.$update(this.editingId, record);
        } else this.$add(record);
        this.editingId = '';
        this.$clear('draft');
        this.error = '';
      },
      edit(id) {
        const row = this.items.find(item => String(item.id) === String(id));
        if (!row) return this.$error('対象レコードが見つかりません');
        this.editingId = String(row.id);
        this.draft = Object.fromEntries(spec.fields.map(field =>
          [field.name, row[field.name] ?? field.default]));
        this.error = '';
      },
      cancel() { this.editingId = ''; this.$clear('draft'); this.error = ''; },
      view(id) { this.selectedId = String(id); },
      closeDetail() { this.selectedId = ''; },
      ...custom,
    },
  });
  return { ...app, schema, spec, inspect: () => specSnapshot(config) };
}
