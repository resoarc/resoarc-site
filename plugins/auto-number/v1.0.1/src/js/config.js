/*
 * ResoArc Auto Number: plugin settings / MIT
 */
(function (pluginId) {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const form = $('ra-config-form');
  const old = kintone.plugin.app.getConfig(pluginId) || {};
  const error = (message) => { $('ra-error').textContent = message || ''; };
  const api = (path, method, params) => kintone.api(kintone.api.url(path, true), method, params);
  const app = kintone.app.getId();
  function preview() {
    const prefix = $('ra-prefix').value;
    const width = Number($('ra-width').value);
    const offset = $('ra-start').value.trim();
    let value = '';
    try {
      if (!/^[1-9][0-9]{0,8}$/.test(offset)) throw Error();
      value = prefix + BigInt(offset).toString().padStart(width, '0');
    } catch (_) { value = '設定値を確認してください'; }
    $('ra-preview-number').textContent = value;
  }
  $('ra-prefix').value = old.prefix || '';
  $('ra-width').value = old.width || '6';
  $('ra-start').value = old.start || '1';
  [$('ra-prefix'), $('ra-width'), $('ra-start')].forEach((el) => el.addEventListener('input', preview));
  preview();
  async function init() {
    try {
      if (!app) throw new Error('アプリIDを取得できません。設定画面をアプリから開いてください。');
      const response = await api('/k/v1/app/form/fields.json', 'GET', {app});
      const select = $('ra-field');
      select.replaceChildren();
      const first = document.createElement('option');
      first.value = ''; first.textContent = 'フィールドを選択してください';
      select.appendChild(first);
      for (const value of Object.values(response.properties || {})) {
        if (value.type !== 'SINGLE_LINE_TEXT' || value.required || value.lookup || value.expression) continue;
        const option = document.createElement('option');
        option.value = value.code;
        option.textContent = value.label + ' (' + value.code + ')';
        select.appendChild(option);
      }
      if (old.field) select.value = old.field;
      if (!select.value) error('採番先にできる文字列（1行）フィールドが見つからない場合は、フォームへ追加してください。');
    } catch (e) {
      const select = $('ra-field');
      select.replaceChildren();
      const opt = document.createElement('option'); opt.value=''; opt.textContent='フィールドを取得できません'; select.appendChild(opt);
      error('フィールド一覧を取得できません。アプリ設定を確認してください。' + (e.message || ''));
    }
  }
  form.addEventListener('submit', function (event) {
    event.preventDefault();
    error('');
    const field = $('ra-field').value;
    const prefix = $('ra-prefix').value;
    const width = $('ra-width').value;
    const start = $('ra-start').value.trim();
    if (!field) {error('採番先フィールドを選択してください。');return;}
    if (!/^[A-Za-z0-9_-]{0,20}$/.test(prefix)) {error('接頭辞は半角英数字・ハイフン・アンダースコアの20文字以内です。');return;}
    if (!/^(?:[3-9]|1[0-2])$/.test(width)) {error('桁数は3～12を指定してください。');return;}
    if (!/^[1-9][0-9]{0,8}$/.test(start)) {error('先頭番号は1～999999999の整数です。');return;}
    $('ra-save').disabled = true;
    kintone.plugin.app.setConfig({field,prefix,width,start});
  });
  $('ra-cancel').addEventListener('click', () => {window.history.back();});
  init();
})(kintone.$PLUGIN_ID);