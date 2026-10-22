import {chromium} from 'playwright-core';
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
try{const page=await browser.newPage({viewport:{width:1280,height:780}});
 await page.goto('http://127.0.0.1:5173/',{waitUntil:'networkidle'});
 await page.waitForTimeout(1300);
 const details=await page.evaluate(()=>{
 const main=document.querySelector('.fortune-container');
 return {html:main?.outerHTML.slice(0,9500),rects:Array.from(document.querySelectorAll('[class*="cell"],[class*="grid"]')).slice(0,28).map(el=>({tag:el.tagName,cls:el.className,id:el.id,rect:{x:el.getBoundingClientRect().x,y:el.getBoundingClientRect().y}}))};});
 console.log(JSON.stringify(details,null,2).slice(0,13000));
}finally{await browser.close();}
