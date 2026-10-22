import { chromium } from 'playwright-core';
const executablePath='C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const browser=await chromium.launch({headless:true,executablePath,args:['--no-first-run','--disable-extensions']});
try {
 const page=await browser.newPage({viewport:{width:1360,height:900},acceptDownloads:true});
 const errors=[];
 page.on('pageerror',e=>errors.push(String(e)));
 page.on('console',m=>{if(m.type()==='error')errors.push('console '+m.text());});
 await page.goto('http://127.0.0.1:5173/',{waitUntil:'networkidle',timeout:20000});
 await page.waitForTimeout(1800);
 console.log('TITLE',await page.title());
 console.log('BODY_SNIPPET',(await page.locator('body').innerText()).slice(0,600));
 console.log('FROZEN?',await page.locator('.fortune-container').count());
 console.log('BUTTONS',await page.locator('button').allTextContents());
 console.log('ERRORS',JSON.stringify(errors));
 await page.screenshot({path:'qa-start-screen.png',fullPage:true});
}finally{await browser.close();}