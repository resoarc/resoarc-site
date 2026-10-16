/* ResoArc read-only kintone session check. Run in DevTools on an authorized kintone page. */
(async () => {
  const report = {timestamp: new Date().toISOString(), origin: location.origin, loggedIn: false, appRead: false, fieldsRead: false, warnings: []};
  if (!location.hostname.endsWith('.cybozu.com')) throw Error('kintoneドメインで実行してください');
  if (!window.kintone?.api) throw Error('kintone API が使えるページを開いてください');
  const call = (path, params) => kintone.api(kintone.api.url(path, true), 'GET', params);
  try {
    const user = kintone.getLoginUser?.();
    report.loggedIn = Boolean(user?.code);
  } catch (error) { report.warnings.push('ログイン情報を確認できません'); }
  const app = new URLSearchParams(location.search).get('app') || location.pathname.match(/^\/k\/(\d+)/)?.[1];
  if (app) {
    report.appId = Number(app);
    try {
      const info = await call('/k/v1/app.json', {id: report.appId});
      report.appRead = Boolean(info?.appId);
      report.appName = info?.name;
      const fields = await call('/k/v1/app/form/fields.json', {app: report.appId});
      report.fieldsRead = Boolean(fields?.properties);
      report.fieldCount = Object.keys(fields?.properties || {}).length;
    } catch (error) {
      report.warnings.push('アプリ参照に失敗: ' + (error?.code || 'HTTP/permission error'));
    }
  } else report.warnings.push('アプリ画面で実行すると読み取り権限も確認できます');
  console.info('ResoArc read-only API diagnostics:', report);
  return report;
})();
