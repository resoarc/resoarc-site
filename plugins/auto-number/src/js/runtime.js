/*
 * ResoArc Auto Number v1.0.0 / MIT License.
 * Only same-origin kintone REST GET/PUT. No external service.
 * Kintone's record ID is unique per app, allowing concurrent inserts.
 */
(function (pluginId) {
  'use strict';
  const config = kintone.plugin.app.getConfig(pluginId);
  const core = typeof ResoArcAutoNumber !== 'undefined' ? ResoArcAutoNumber : null;
  const opts = core && core.validConfig(config);
  if (!opts) return;
  const mobile = !!(kintone.mobile && /mobile\./.test((typeof location !== 'undefined' && location.pathname) || '')) ;
  // Register both desktop and mobile handlers: Kintone only fires the matching event.
  const showTypes = ['app.record.create.show', 'mobile.app.record.create.show',
    'app.record.edit.show', 'mobile.app.record.edit.show'];
  kintone.events.on(showTypes, function (event) {
    const field = event.record && event.record[opts.field];
    if (field) {
      field.disabled = true;
      if (event.type.includes('.create.')) field.value = '';
    }
    return event;
  });
  const submitTypes = ['app.record.create.submit', 'mobile.app.record.create.submit'];
  kintone.events.on(submitTypes, function (event) {
    if (event.record && event.record[opts.field]) event.record[opts.field].value = '';
    return event;
  });
  function endpoint() { return kintone.api.url('/k/v1/record.json', true); }
  async function assignIfBlank(appId, recordId) {
    const app = Number(appId);
    const id = String(recordId || '');
    if (!Number.isSafeInteger(app) || app <= 0 || !/^[1-9][0-9]*$/.test(id)) throw new Error('レコードIDを取得できません。');
    const existing = await kintone.api(endpoint(), 'GET', {app, id});
    if (!existing || !existing.record || !existing.record[opts.field]) throw new Error('採番フィールドが存在しません。');
    const current = existing.record[opts.field].value;
    // Never overwrite a previously assigned value or manually imported number.
    if (current !== '' && current !== null && typeof current !== 'undefined') return { number: current, updated: false };
    const number = core.makeNumber(id, opts);
    const fields = {};
    fields[opts.field] = {value: number};
    await kintone.api(endpoint(), 'PUT', {app, id, record:fields, revision:existing.record.$revision.value});
    return {number, updated:true};
  }
  kintone.events.on(['app.record.create.submit.success','mobile.app.record.create.submit.success'], async function(event) {
    try {
      await assignIfBlank(event.appId, event.recordId);
    } catch (err) {
      const message = 'レコードは保存されましたが、自動採番できませんでした。レコード詳細画面から「採番を再試行」を実行してください。\n' +
        (err && err.message ? err.message : '権限または通信状態をご確認ください。');
      console.error('[ResoArc Auto Number]', err);
      window.alert(message);
    }
    return event;
  });
  function header(mobileEvent) {
    return mobileEvent ? (kintone.mobile && kintone.mobile.app.getHeaderSpaceElement
      ? kintone.mobile.app.getHeaderSpaceElement() : null)
      : (kintone.app && kintone.app.record.getHeaderMenuSpaceElement
      ? kintone.app.record.getHeaderMenuSpaceElement() : null);
  }
  kintone.events.on(['app.record.detail.show','mobile.app.record.detail.show'], function(event) {
    if (!event.record || !event.record[opts.field]) return event;
    const container = header(event.type.startsWith('mobile.'));
    if (!container) return event;
    const old = container.querySelector('[data-resoarc-auto-number]');
    if (old) old.remove();
    const val = event.record[opts.field].value;
    if (val !== '' && val !== null && typeof val !== 'undefined') return event;
    const banner = document.createElement('div');
    banner.className = 'ra-number-notice';
    banner.setAttribute('data-resoarc-auto-number', '');
    banner.setAttribute('role','status');
    const label = document.createElement('span');
    label.textContent = '採番欄が空欄です。保存後の採番が完了していない可能性があります。';
    const retry = document.createElement('button');
    retry.type = 'button';
    retry.className = 'ra-number-retry';
    retry.textContent = '採番を再試行';
    retry.addEventListener('click', async function() {
      retry.disabled = true;
      label.textContent = '採番を実行しています…';
      try {
        const result = await assignIfBlank(event.appId, event.recordId || (event.record.$id && event.record.$id.value));
        label.textContent = '採番：' + result.number;
        retry.remove();
        // kintone detail event snapshot is not refreshed automatically.
        window.location.reload();
      } catch (err) {
        label.textContent = '採番できませんでした。フィールド編集権限と通信環境を確認してください。';
        retry.disabled = false;
        console.error('[ResoArc Auto Number]', err);
      }
    });
    banner.append(label, retry);
    container.appendChild(banner);
    return event;
  });
  // Unit-test hook, not a public kintone API.
  if (typeof window !== 'undefined' && window.__RESOARC_TEST__) {
    window.__RESOARC_TEST__.assignIfBlank = assignIfBlank;
  }
})(kintone.$PLUGIN_ID);