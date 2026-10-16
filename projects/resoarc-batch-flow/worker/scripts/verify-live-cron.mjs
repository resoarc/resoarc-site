/* ResoArc Clock live observability smoke test.
 * Collects only stdout from an authenticated Wrangler tail session, never secrets.
 * Cannot trigger a Clock or write to kintone. */
import {spawn} from 'node:child_process';
const durationMs=83_000;
const child=spawn('cmd.exe',['/d','/s','/c','npx.cmd wrangler tail resoarc-clock-self-hosted --format json'],{
  cwd:new URL('../',import.meta.url).pathname.replace(/^\/([A-Za-z]:)/,'$1'),
  windowsHide:true, stdio:['ignore','pipe','pipe']
});
let stdout='',stderr='';
child.stdout.on('data',x=>{stdout+=x.toString();if(stdout.length>100_000)stdout=stdout.slice(-100_000);});
child.stderr.on('data',x=>{stderr+=x.toString();if(stderr.length>10_000)stderr=stderr.slice(-10_000);});
const cutoff=setTimeout(()=>{
  if(child.pid)spawn('taskkill',['/PID',String(child.pid),'/T','/F'],{windowsHide:true,stdio:'ignore'});
},durationMs);
await new Promise(resolve=>child.once('close',resolve));
clearTimeout(cutoff);
const ticks=(stdout.match(/ResoArc Clock is disabled/g)||[]).length;
console.log(JSON.stringify({
  check:'remote-cloudflare-cron',
  observedDisabledCronTicks:ticks,
  connectedToTail:/Successfully created tail|Connected to|Created tail|Listening for logs|Tail created/i.test(stdout+stderr),
  stdoutBytes:stdout.length,stderrBytes:stderr.length,
  diagnostic:stderr.replace(/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+/g,'[redacted-email]')
    .replace(/[a-f0-9]{24,}/gi,'[redacted-id]').slice(0,420),
  result:ticks>0?'PASS_DISABLED_TICK_OBSERVED':'NO_TICK_OBSERVED',
  // Do not print raw Cloudflare output because it can contain personal account IDs.
},null,2));
if(!ticks)process.exitCode=2;
