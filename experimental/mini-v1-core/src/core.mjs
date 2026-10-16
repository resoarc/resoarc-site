/* ResoArc Mini v1 candidate pure operations. MIT. NO kintone/global side effects. */
export function fieldCode(v) {
  if (typeof v !== 'string' || !v || v.length > 128 || /[\x00-\x1f]/.test(v) ||
      ['__proto__','prototype','constructor'].includes(v)) throw Error('Invalid field code');
  return v;
}
export function applyPreset(record, mapping, overwrite = false) {
  if (!record || typeof record !== 'object' || !mapping || typeof mapping !== 'object' ||
      Array.isArray(mapping)) throw Error('Invalid preset');
  for (const [key,value] of Object.entries(mapping)) {
    fieldCode(key);
    if (!Object.prototype.hasOwnProperty.call(record,key) || !('value' in record[key])) continue;
    if (!overwrite && record[key].value !== '' && record[key].value != null) continue;
    if (typeof value !== 'string' && typeof value !== 'number' && typeof value !== 'boolean') continue;
    if (['SINGLE_LINE_TEXT','MULTI_LINE_TEXT','NUMBER','DROP_DOWN','RADIO_BUTTON','CHECK_BOX'].includes(record[key].type))
      record[key].value = record[key].type === 'CHECK_BOX' ? [String(value)] : String(value);
  }
  return record;
}
export function resetOnReuse(record, names, isReuse) {
  if (isReuse !== true) return record;
  if (!Array.isArray(names)) throw Error('Expected fields');
  for(const n of names) {
    fieldCode(n);
    if (!Object.prototype.hasOwnProperty.call(record,n)) continue;
    const f=record[n];
    if (!f || !('value' in f)) continue;
    if (['FILE','CHECK_BOX','MULTI_SELECT','USER_SELECT','ORGANIZATION_SELECT','GROUP_SELECT'].includes(f.type)) f.value=[];
    else if(f.type==='SUBTABLE') f.value=[];
    else if (f.type !== 'RECORD_NUMBER' && f.type !== 'CREATOR' && f.type !== 'CREATED_TIME' && f.type !== 'MODIFIER' && f.type !== 'UPDATED_TIME') f.value='';
  }
  return record;
}
export function normalizeText(raw, mode='nfkc-trim') {
  if (raw == null) return '';
  let s=String(raw);
  if (mode==='phone') return s.normalize('NFKC').replace(/[^\d+]/g,'').replace(/(?!^)\+/g,'');
  if (mode==='trim') return s.trim();
  if (mode==='spaces') return s.replace(/[\u3000\t]+/g,' ').replace(/ +/g,' ').trim();
  if (mode==='nfkc-trim') return s.normalize('NFKC').trim();
  throw Error('Unknown normalize mode');
}
export function normalizeFields(record,config) {
  if(!Array.isArray(config)) throw Error('Rules array required');
  for(const rule of config){
    const k=fieldCode(rule.field);
    if(record?.[k] && ['SINGLE_LINE_TEXT','MULTI_LINE_TEXT'].includes(record[k].type)){
      record[k].value=normalizeText(record[k].value,rule.mode);
    }
  }
  return record;
}
export function helpContent(text) {
  return String(text == null ? '' : text).slice(0,2000);
}
export function postSaveDestination(mode,origin,appId){
  if(!['stay','index','create'].includes(mode)) throw Error('Unknown redirect');
  if(mode==='stay') return null;
  if(!/^[1-9]\d{0,8}$/.test(String(appId))) throw Error('Bad app ID');
  const u=new URL(origin);
  if(u.protocol!=='https:' || u.username || u.password) throw Error('HTTPS required');
  return u.origin+'/k/'+appId+'/'+(mode==='create'?'edit':'');
}
export function mailtoTemplate(recipient,subject,body){
  if(typeof recipient!=='string'||recipient.length>254||/[\r\n?&]/.test(recipient)||!/^([a-z\d._%+-]+@[a-z\d.-]+\.[a-z]{2,})?$/i.test(recipient))throw Error('Bad email');
  const clean=v=>String(v ?? '').replace(/[\r\n]+/g,' ').slice(0,4000);
  return 'mailto:'+recipient+'?subject='+encodeURIComponent(clean(subject))+'&body='+encodeURIComponent(clean(body));
}
export function aggregatePage(records,key){
  if(!Array.isArray(records))throw Error('Records required');
  fieldCode(key);
  let sum=0,count=0;
  for(const r of records){
    const value=r?.[key]?.value;
    if(value===null||value===''||value===undefined)continue;
    const n=Number(value);
    if(!Number.isFinite(n)||Math.abs(n)>Number.MAX_SAFE_INTEGER)continue;
    sum+=n;count++;
    if(!Number.isFinite(sum)||Math.abs(sum)>Number.MAX_SAFE_INTEGER)throw Error('Numeric precision limit');
  }
  return {pageRecordCount:records.length,numericCount:count,sum,average:count ? sum/count : null,scope:'current_page'};
}
export function csvCell(value){
  let s=Array.isArray(value)?value.join(';'):String(value??'');
  // Mitigate spreadsheet formula injection, including whitespace-prefixed formulas.
  if(/^[\s\uFEFF]*[=+\-@]/.test(s))s="'"+s;
  return '"'+s.replace(/"/g,'""')+'"';
}
export function exportCurrentPage(records,fields,withBom=true){
  if(!Array.isArray(records)||!Array.isArray(fields)||fields.length===0||fields.length>100) throw Error('Bad CSV shape');
  for(const k of fields)fieldCode(k);
  const lines=[fields.map(csvCell).join(',')];
  for(const r of records){
    lines.push(fields.map(k=>csvCell(r?.[k]?.value)).join(','));
  }
  return (withBom?'\uFEFF':'')+lines.join('\r\n')+'\r\n';
}
export function attachmentCount(record,key){
  fieldCode(key); const field=record?.[key]; return field?.type==='FILE'&&Array.isArray(field.value)?field.value.length:0;
}
export function copySubtableRow(row){
  if(!row||typeof row!=='object'||!row.value||typeof row.value!=='object')throw Error('Invalid subtable row');
  const value=Object.create(null);
  for(const [k,v] of Object.entries(row.value)){
    fieldCode(k);
    if(!v || typeof v!=='object' || !('value' in v))continue;
    value[k]={type:v.type,value:JSON.parse(JSON.stringify(v.value))};
  }
  return {value};
}
export function qrPayload(raw){
  const s=String(raw??'');
  if(!s||s.length>2048||/[\x00-\x08\x0e-\x1f]/.test(s))throw Error('Invalid QR payload');
  return s;
}
export function tocEntries(fields,record) {
  if(!Array.isArray(fields))throw Error('Fields array required');
  return fields.filter(f=>f&&typeof f.code==='string'&&record&&
    Object.prototype.hasOwnProperty.call(record,f.code)).map(f=>({code:fieldCode(f.code),label:helpContent(f.label||f.code).slice(0,100)}));
}
export function safeRelatedLink(origin,path,value){
  const u=new URL(origin);if(u.protocol!=='https:'||u.username||u.password)throw Error('HTTPS required');
  if(!/^\/k\/[1-9]\d{0,8}\/?$/.test(path))throw Error('Only same-origin app links allowed');
  return u.origin+path+(path.includes('?')?'&':'?')+'q='+encodeURIComponent(String(value??'').slice(0,200));
}
export function stickyStyle(firstColumn=true) {
  return '.recordlist-gaia thead th{position:sticky;top:0;z-index:4;}'+
    (firstColumn?'.recordlist-gaia tbody td:first-child,.recordlist-gaia thead th:first-child{position:sticky;left:0;z-index:5;background:var(--kintone-base-bg,#fff);}':'');
}
export function previewFileMeta(file){
  if(!file||typeof file.fileKey!=='string'||!/^[A-Za-z0-9_-]{1,150}$/.test(file.fileKey))throw Error('Bad file key');
  const size=Number(file.size);
  if(!Number.isSafeInteger(size)||size<0||size>20*1024*1024)throw Error('File size limit');
  const type=String(file.contentType??'');
  if(type!=='application/pdf'&&!/^image\/(png|jpeg|gif|webp)$/.test(type))throw Error('Unsupported preview type');
  return {fileKey:file.fileKey,size,contentType:type,name:helpContent(file.name).slice(0,160)};
}
export function lookupQuery(code,term,limit=20){
  fieldCode(code);
  if(!Number.isInteger(limit)||limit<1||limit>100)throw Error('Bad query limit');
  const value=String(term??'').slice(0,80).replace(/\\/g,'\\\\').replace(/"/g,'\\"').replace(/[\r\n]/g,' ');
  return code+' like "'+value+'" limit '+limit;
}
export function normalizePostal(raw){
  const value=String(raw??'').normalize('NFKC').replace(/[ -]/g,'');
  if(!/^\d{7}$/.test(value))throw Error('Expected seven-digit postal code');
  return value;
}
export function postalLookupAllowed(postal,consent){
  if(consent!==true)throw Error('Explicit postal lookup consent required');
  return normalizePostal(postal);
}
export function barcodeValue(raw){
  const x=String(raw??'').trim();
  if(!x||x.length>128||/[\x00-\x1f]/.test(x))throw Error('Invalid barcode');
  return x;
}
