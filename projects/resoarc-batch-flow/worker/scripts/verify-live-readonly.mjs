/* Cloudflare live read-only Clock check. Never print provider log text or secrets.
   Caller should pre-verify RA_ALLOW_WRITES=false and RA_CONTROL_APP_ID=50. */
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {resolve,dirname} from 'node:path';
const worker=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const child=spawn('cmd.exe',['/d','/s','/c','npx.cmd wrangler tail resoarc-clock-self-hosted --format json'],{
  cwd:worker,windowsHide:true,stdio:['ignore','pipe','pipe']
});
let stdout='',stderr='';
child.stdout.on('data',x=>{stdout+=x.toString();if(stdout.length>180000)stdout=stdout.slice(-180000)});
child.stderr.on('data',x=>{stderr+=x.toString();if(stderr.length>5000)stderr=stderr.slice(-5000)});
const stop=setTimeout(()=>{
  if(child.pid)spawn('taskkill',['/PID',String(child.pid),'/T','/F'],{windowsHide:true,stdio:'ignore'});
},82_000);
await new Promise(done=>child.once('close',done));
clearTimeout(stop);
const polled=(stdout.match(/ResoArc Clock: polled/g)||[]).length;
const cached=(stdout.match(/ResoArc Clock: cache hit/g)||[]).length;
const disabled=(stdout.match(/ResoArc Clock is disabled/g)||[]).length;
const dryRun=(stdout.match(/ResoArc Clock DRY RUN:/g)||[]).length;
const failed=/\"outcome\":\"exception\"|\"exceptions\":\[\{|kintone API (?:40[01349]|50\d)/i.test(stdout);
const report={check:'adaptive-remote-readonly',polledTicks:polled,cachedTicks:cached,dryRunTasks:dryRun,
  disabledTicks:disabled,unexpectedApiErrors:failed,
  result:polled+cached>0&&!failed?'PASS':'NOT_CONFIRMED'};
console.log(JSON.stringify(report,null,2));
if(report.result!=='PASS')process.exitCode=2;
