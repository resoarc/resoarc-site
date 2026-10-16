import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {dirname,resolve} from 'node:path';
import {buildClockLayout,provisionClockApp} from './provision-core.mjs';
const dir=dirname(fileURLToPath(import.meta.url));
const props=JSON.parse(readFileSync(resolve(dir,'fields.json'),'utf8')).properties;
buildClockLayout(props);
const script=`/* ResoArc Clock v0.3.1 one-time install script
 * Run ONLY on your own logged-in kintone test tenant in the browser console.
 * Creates a NEW app. No API tokens or passwords are used or requested.
 * No writes occur until you confirm the prompt.
 * Upload the signed ResoArc Batch Center plugin separately after deploy.
 */
(async () => {
  'use strict';
  const properties=${JSON.stringify(props)};
  const buildClockLayout=${buildClockLayout.toString()};
  const provisionClockApp=${provisionClockApp.toString()};
  if(!/^([a-zA-Z0-9-]+\\.)+(cybozu\\.com|kintone\\.com)$/.test(location.hostname))
    throw Error('Open your own kintone test tenant');
  if(typeof kintone==='undefined'||typeof kintone.api!=='function')
    throw Error('Open a signed-in kintone app page');
  if(!confirm('ResoArc Clock専用の新しい検証用アプリを1つ作成します。既存アプリは変更しません。よろしいですか？'))
    return {cancelled:true};
  let createdAppId=null;
  try{
    const response=await provisionClockApp((path,method,params)=>
      kintone.api(kintone.api.url(path,true),method,params),properties);
    createdAppId=response.app;
    console.info('ResoArc Clock app created; deployment requested. ID:',createdAppId);
    console.info('Next: install signed Batch Center plugin and create read-only API token');
    return response;
  }catch(error){
    console.error('ResoArc Clock setup stopped:',error.message);
    if(error.clockAppId)console.info('New app remains for review. App ID:',error.clockAppId);
    throw error;
  }
})()
`;
const output=resolve(dir,'../release/resoarc-clock-bootstrap-v0.3.1.js');
mkdirSync(dirname(output),{recursive:true});
writeFileSync(output,script,'utf8');
console.log(output);
