/** SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
 *  SPDX-License-Identifier: MIT
 *  Read the REAL same-origin HTML / CSS / JS files; never execute fetched code.
 */
const view = document.querySelector('[data-q-source]');
if (view) {
  const files = {
    html: view.dataset.sourceHtml,
    css: view.dataset.sourceCss,
    js: view.dataset.sourceJs,
  };
  const code = view.querySelector('[data-q-source-code]');
  const file = view.querySelector('[data-q-source-file]');
  const buttons = [...view.querySelectorAll('[data-q-source-tab]')];
  const copy = view.querySelector('[data-q-source-copy]');
  const cache = new Map();
  let active = 'js';
  let shown = '';
  const decode = (value) => value.split(',').map(x => x.trim()).filter(Boolean);

  async function load(kind) {
    const paths = decode(files[kind] || '');
    if (!paths.length || paths.length > 4) throw new Error('未設定のソース種別です');
    if (!cache.has(kind)) {
      const result = await Promise.all(paths.map(async (path) => {
        // Only explicitly configured same-origin assets can be fetched.
        if (!path.startsWith('/') || path.includes('..') || path.includes('\\') ||
            /[?#]/.test(path) || /\/\//.test(path)) {
          throw new Error('許可されないソースパス');
        }
        const response = await fetch(path, { credentials: 'omit', cache: 'no-store' });
        if (!response.ok) throw new Error(`取得失敗: HTTP ${response.status}`);
        const content = await response.text();
        if (content.length > 130000) throw new Error('ソースが大きすぎます');
        return paths.length > 1 ? `/* ===== ${path} ===== */\n${content}` : content;
      }));
      cache.set(kind, result.join('\n\n'));
    }
    return { text: cache.get(kind), path: paths.join('   +   ') };
  }
  async function select(kind) {
    if (!Object.prototype.hasOwnProperty.call(files, kind)) return;
    active = kind;
    buttons.forEach((button) => {
      const selected = button.dataset.qSourceTab === kind;
      button.setAttribute('aria-selected', String(selected));
      button.tabIndex = selected ? 0 : -1;
    });
    code.textContent = '読み込み中…';
    file.textContent = '配信中のソースファイルを取得しています';
    try {
      const result = await load(kind);
      if (active !== kind) return;
      code.textContent = result.text;
      file.textContent = result.path;
      shown = result.text;
    } catch (error) {
      if (active !== kind) return;
      shown = '';
      code.textContent = `ソースを取得できません: ${error.message}`;
      file.textContent = 'オフライン時はソース表示を利用できません';
    }
  }
  buttons.forEach((button, index) => {
    button.addEventListener('click', () => void select(button.dataset.qSourceTab));
    button.addEventListener('keydown', (event) => {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault();
      const next = event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1 :
        (index + (event.key === 'ArrowRight' ? 1 : -1) + buttons.length) % buttons.length;
      buttons[next].focus();
      void select(buttons[next].dataset.qSourceTab);
    });
  });
  copy?.addEventListener('click', async () => {
    if (!shown) return;
    try {
      await navigator.clipboard.writeText(shown);
      copy.textContent = 'コピーしました';
    } catch (_) {
      copy.textContent = 'コピー不可（選択してコピーしてください）';
    }
    setTimeout(() => { copy.textContent = 'コードをコピー'; }, 2600);
  });
  void select('js');
}
