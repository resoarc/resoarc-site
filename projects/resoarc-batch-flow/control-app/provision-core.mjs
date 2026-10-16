/* ResoArc Clock: session-authenticated, new-app-only provisioning.
 * No existing apps are modified. Keep this module usable from Node tests and browser installer. */
export function buildClockLayout(properties) {
  if (!properties || typeof properties !== 'object' || !properties.Steps) throw Error('Clock schema is missing Steps');
  const name = code => {
    const config = properties[code];
    if(!config || config.type === 'SUBTABLE') throw Error('Invalid layout field '+code);
    return {type:config.type,code};
  };
  const rows=[
    ['BatchName','BatchEnabled','RunState'],
    ['ScheduleType','DailyTime','OneTimeAt','IntervalMinutes'],
    ['NextRunAt','LastStartedAt','LastFinishedAt'],
    ['LastResult'],
    ['RunHistory'],
    ['RunToken']
  ].map(fields=>({type:'ROW',fields:fields.map(name)}));
  const table=properties.Steps;
  rows.push({type:'SUBTABLE',code:'Steps',fields:Object.keys(table.fields).map(code=>({
    type:table.fields[code].type,code
  }))});
  return rows;
}
export async function provisionClockApp(request,properties,appName='ResoArc Clock 検証用') {
  if(typeof request!=='function') throw Error('kintone API adapter required');
  if(typeof appName!=='string'||appName.length>64||!appName.trim())throw Error('Invalid app name');
  if(!properties||Object.keys(properties).length<10)throw Error('Clock fields are missing');
  // Plan before any network write, so local definition errors cannot leave an empty app.
  const layout=buildClockLayout(properties);
  let app;
  try {
    const result=await request('/k/v1/preview/app.json','POST',{name:appName});
    app=Number(result?.app);
    if(!Number.isSafeInteger(app)||app<1)throw Error('kintone did not return a valid new app ID');
    const fields=await request('/k/v1/preview/app/form/fields.json','POST',{app,properties});
    if(!fields?.revision)throw Error('Field addition returned no revision');
    const structure=await request('/k/v1/preview/app/form/layout.json','PUT',{app,revision:fields.revision,layout});
    if(!structure?.revision)throw Error('Layout update returned no revision');
    await request('/k/v1/preview/app/deploy.json','POST',{apps:[{app,revision:structure.revision}]});
    return {app,status:'deploy_requested',name:appName};
  } catch (error) {
    // The new app might remain in preview and need manual inspection.
    error.clockAppId=app||null;
    throw error;
  }
}
