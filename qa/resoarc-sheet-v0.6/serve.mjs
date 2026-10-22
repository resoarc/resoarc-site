import {createServer} from 'node:http';
import {createReadStream,statSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {dirname,resolve,extname,sep} from 'node:path';
const here=dirname(fileURLToPath(import.meta.url));
const root=resolve(here,'dist');
const port=Number(process.env.RESOARC_SHEET_PORT)||5174;
const mime={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.svg':'image/svg+xml','.json':'application/json','.png':'image/png','.ico':'image/x-icon','.woff2':'font/woff2'};
const server=createServer((req,res)=>{
 if(req.method!=='GET'&&req.method!=='HEAD'){res.writeHead(405);res.end();return;}
 let url;
 try{url=new URL(req.url,'http://127.0.0.1:'+port);}catch{res.writeHead(400);res.end();return;}
 let pathname;
 try{pathname=decodeURIComponent(url.pathname);}catch{res.writeHead(400);res.end();return;}
 const target=resolve(root,'.'+(pathname.endsWith('/')?pathname+'index.html':pathname));
 if(!target.startsWith(root+sep)){res.writeHead(403);res.end();return;}
 try{
  const info=statSync(target);if(!info.isFile())throw Error('Not a file');
  res.writeHead(200,{
   'Content-Type':mime[extname(target).toLowerCase()]||'application/octet-stream',
   'Content-Length':info.size,
   'X-Content-Type-Options':'nosniff',
   'Referrer-Policy':'no-referrer',
   'Cross-Origin-Resource-Policy':'same-origin',
   'Cache-Control':'no-store'
  });
  if(req.method==='HEAD')res.end();else createReadStream(target).pipe(res);
 }catch{res.writeHead(404);res.end('Not found');}
});
server.on('error',err=>{console.error('ResoArc Sheetの起動に失敗:',err.message);process.exitCode=1;});
server.listen(port,'127.0.0.1',()=>{
 console.log('ResoArc Sheet QA ローカルモード');
 console.log('http://127.0.0.1:'+port+'/');
 console.log('終了するには Ctrl+C を押してください。');
});
