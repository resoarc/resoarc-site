/* Input normalizer kintone bridge. MIT. Fail closed. */
export function validateRules(config) {
  let settings;
  try { settings=typeof config?.settings === 'string' ? JSON.parse(config.settings) : config?.settings; }
  catch { return null; }
  if (!settings || !Array.isArray(settings.rules) || settings.rules.length < 1 || settings.rules.length > 20) return null;
  const allowed=new Set(['nfkc-trim','trim','spaces','phone']), fields=new Set();
  for (const x of settings.rules){
    if(!x || typeof x.field!=='string' || !x.field || x.field.length>128 ||
       /[\x00-\x1f]/.test(x.field) || ['__proto__','prototype','constructor'].includes(x.field) ||
       !allowed.has(x.mode) || fields.has(x.field)) return null;
    fields.add(x.field);
  }
  return settings.rules.map(x=>({field:x.field,mode:x.mode}));
}
export function registerTextNormalizer(k,pluginConfig,operations){
  const rules=validateRules(pluginConfig);
  if(!rules || !k?.events?.on || typeof operations?.normalizeFields!=='function')return false;
  const events=['app.record.create.submit','app.record.edit.submit',
    'mobile.app.record.create.submit','mobile.app.record.edit.submit'];
  k.events.on(events,function(event){
    if(!event || !event.record)return event;
    return Object.assign(event,{record:operations.normalizeFields(event.record,rules)});
  });
  return true;
}
