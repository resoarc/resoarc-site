import {chromium} from 'playwright-core';
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',args:['--no-first-run','--disable-extensions']});
try{
 const page=await browser.newPage({viewport:{width:1366,height:820}});page.on('pageerror',e=>console.log('ERROR',e.message));page.on('console',m=>{if(m.type()==='error')console.log('CONSOLE',m.text())});
 await page.goto('http://127.0.0.1:5180/',{waitUntil:'networkidle'});
 await page.mouse.click(220,355);await page.waitForTimeout(180);await page.mouse.click(220,355,{button:'right'});
 await page.waitForTimeout(400);
 const out=await page.evaluate(()=>{
  const hits=[...document.querySelectorAll('[class*=context],[class*=Context],[role=menu]')].filter(el=>getComputedStyle(el).display!=='none').slice(0,20);
  return hits.map(el=>({tag:el.tagName,cls:el.className,html:el.outerHTML.slice(0,1500),text:el.innerText?.slice(0,400)}));
 });
 console.log('BODY',(await page.locator('body').innerText()).slice(-700));console.log('COUNTS',{context:await page.locator('.fortune-context-menu').count(),items:await page.locator('[data-resoarc-label]').count(),body:await page.locator('body').count()});console.log(JSON.stringify(out,null,2).slice(0,8000));
}finally{await browser.close();}
