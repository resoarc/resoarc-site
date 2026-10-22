import {join} from 'node:path';
import { chromium } from 'playwright-core';
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',args:['--no-first-run','--disable-extensions']});
try{
 const page=await browser.newPage({viewport:{width:1366,height:768},acceptDownloads:true});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:5173/',{waitUntil:'networkidle',timeout:20000});
 await page.waitForTimeout(950);
 await page.screenshot({path:join(process.cwd(),'tests','ui-audit-desktop.png'),fullPage:true});
 const desktop=await page.evaluate(()=>({
  title:document.title,lang:document.documentElement.lang,
  viewport:{w:innerWidth,h:innerHeight,scrollW:document.documentElement.scrollWidth,scrollH:document.documentElement.scrollHeight},
  headers:[...document.querySelectorAll('header,nav,.toolbar,.fortune-toolbar,.luckysheet-toolbar')].map(x=>({tag:x.tagName,cls:String(x.className),text:x.innerText?.slice(0,300),rect:{x:x.getBoundingClientRect().x,y:x.getBoundingClientRect().y,h:x.getBoundingClientRect().height}})).slice(0,14),
  buttons:[...document.querySelectorAll('button')].slice(0,80).map(x=>({text:x.innerText.slice(0,34),title:x.getAttribute('title'),aria:x.getAttribute('aria-label')})),
  inputs:[...document.querySelectorAll('input:not([hidden])')].slice(0,25).map(x=>({placeholder:x.placeholder,aria:x.getAttribute('aria-label'),value:x.value,type:x.type})),
  body:document.body.innerText.slice(0,1200),
 }));
 await page.mouse.click(120,300);
 const rightClickBefore=(await page.locator('body').innerText()).slice(-800);
 await page.mouse.click(120,300,{button:'right'});await page.waitForTimeout(300);
 const rightClickAfter=(await page.locator('body').innerText()).slice(-1200);
 await page.screenshot({path:join(process.cwd(),'tests','ui-audit-context.png')});
 await page.setViewportSize({width:390,height:844}); await page.waitForTimeout(250);
 const mobile=await page.evaluate(()=>({viewport:innerWidth,scrollWidth:document.documentElement.scrollWidth,gridWidth:document.querySelector('.fortune-container')?.getBoundingClientRect().width,navScrollWidth:document.querySelector('.toolbar')?.scrollWidth,navClientWidth:document.querySelector('.toolbar')?.clientWidth,screenText:document.body.innerText.slice(0,480)}));
 await page.screenshot({path:join(process.cwd(),'tests','ui-audit-mobile.png'),fullPage:true});
 console.log(JSON.stringify({desktop,rightClickMenuAppeared:rightClickAfter!==rightClickBefore,rightClickText:rightClickAfter,mobile,errors},null,2).slice(0,15500));
}finally{await browser.close();}