import { chromium } from 'playwright-core';
import ExcelJS from 'exceljs';
import assert from 'node:assert/strict';
import {mkdir,readFile} from 'node:fs/promises';
import {resolve,join} from 'node:path';

const dir=resolve(process.cwd(),'tests','qa-artifacts');
await mkdir(dir,{recursive:true});
const fixture=join(dir,'input-two-sheets.xlsx');
const w=new ExcelJS.Workbook();
w.creator='ResoArc QA';
const s=w.addWorksheet('売上');
s.getCell('A1').value='品名';s.getCell('B1').value='数量';s.getCell('C1').value='単価';s.getCell('D1').value='金額';
s.getCell('A2').value='鉛筆';s.getCell('B2').value=3;s.getCell('C2').value=120;s.getCell('D2').value={formula:'B2*C2',result:360};
s.getCell('A3').value='ノート';s.getCell('B3').value=5;s.getCell('C3').value=200;s.getCell('D3').value={formula:'B3*C3',result:1000};
s.getCell('D4').value={formula:'SUM(D2:D3)',result:1360};
s.getCell('B5').value=0;s.getCell('B6').value=-4.25;s.getCell('B7').value='0007';
s.getRow(1).font={bold:true,color:{argb:'FFFFFFFF'}};
s.getRow(1).fill={type:'pattern',pattern:'solid',fgColor:{argb:'FF174EA6'}};
s.getColumn('A').width=22;
const t=w.addWorksheet('備考');t.getCell('A1').value='別シートも保存';t.getCell('B2').value=42;
await w.xlsx.writeFile(fixture);

const executablePath='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const browser=await chromium.launch({headless:true,executablePath,args:['--no-first-run','--disable-extensions']});
const logs=[];
const externalRequests=[];
const ret={};
try {
 const page=await browser.newPage({viewport:{width:1380,height:900},acceptDownloads:true});
 page.on('dialog',d=>d.accept());
 page.on('pageerror',e=>logs.push('pageerror: '+e.message));
 page.on('request',request=>{const url=request.url();if(/^https?:/.test(url)&&!url.startsWith(process.env.RESOARC_BASE_URL||'http://127.0.0.1:5173/'))externalRequests.push(url);});
 page.on('console',m=>{if(m.type()==='error') logs.push('console: '+m.text());});
 await page.goto(process.env.RESOARC_BASE_URL || 'http://127.0.0.1:5173/',{waitUntil:'networkidle',timeout:20000});
 const fileInput=page.locator('input[accept=".xlsx,.csv"]');
 await fileInput.setInputFiles(fixture);
 await page.waitForTimeout(4500);
 if(process.argv.includes('--edit')) {
  await page.getByRole('textbox',{name:'名前ボックス'}).fill('B2');
  await page.getByRole('textbox',{name:'名前ボックス'}).press('Enter');
  ret.editorBefore=await page.getByRole('textbox',{name:'数式バー'}).inputValue();
  await page.getByRole('textbox',{name:'数式バー'}).fill('7');
  await page.getByRole('textbox',{name:'数式バー'}).press('Enter');
  ret.editorAfter=await page.getByRole('textbox',{name:'数式バー'}).inputValue();
  await page.waitForTimeout(1200);
  ret.editedStatus=await page.locator('.saved-indicator').innerText();
 }
 ret.afterImport=(await page.locator('.statusbar').innerText()).slice(0,450);
 await page.getByRole('tab',{name:'ファイル'}).click();
 const backupPromise=page.waitForEvent('download',{timeout:25000});
 await page.getByRole('button',{name:'バックアップ',exact:true}).click();
 const backup=await backupPromise;
 const bFile=join(dir,'backup.json'); await backup.saveAs(bFile);
 const bObj=JSON.parse(await readFile(bFile,'utf8'));
 ret.sheetData=bObj.sheets.map(s=>({name:s.name,B2:s.data?.[1]?.[1],D2:s.data?.[1]?.[3]}));
 const downloadPromise=page.waitForEvent('download',{timeout:25000});
 await page.getByRole('button',{name:'保存',exact:true}).click();
 const download=await downloadPromise;
 const output=join(dir,'output-roundtrip.xlsx');
 await download.saveAs(output);
 ret.download={filename:download.suggestedFilename(),failure:await download.failure()};
 await page.waitForTimeout(1000);
 ret.afterExport=(await page.locator('.statusbar').innerText()).slice(0,450);
 const outW=new ExcelJS.Workbook();
 await outW.xlsx.readFile(output);
 ret.sheets=outW.worksheets.map(sh=>sh.name);
 for(const cell of ['A1','A2','B2','C2','D2','D4']){
  ret[cell]={raw:outW.worksheets[0].getCell(cell).value,type:outW.worksheets[0].getCell(cell).type};
 }
 ret.remarks=outW.getWorksheet('備考')?.getCell('A1').value;
 ret.headerBold=outW.worksheets[0].getCell('A1').font?.bold;
 ret.extra={B5:outW.worksheets[0].getCell('B5').value,B6:outW.worksheets[0].getCell('B6').value,B7:outW.worksheets[0].getCell('B7').value};
 ret.errors=logs;
 ret.externalRequests=externalRequests;
 await page.screenshot({path:join(dir,'screen-after-save.png'),fullPage:true});
 assert.deepEqual(ret.sheets,['売上','備考']);
 assert.equal(ret.remarks,'別シートも保存');
 assert.equal(ret.A1.raw,'品名');
 assert.equal(ret.B2.raw,process.argv.includes('--edit')?7:3);
 assert.equal(ret.C2.raw,120);
 assert.equal(ret.D2.raw.formula,'B2*C2');
 assert.equal(ret.D2.raw.result,process.argv.includes('--edit')?840:360);
 assert.equal(ret.D4.raw.result,process.argv.includes('--edit')?1840:1360);
 assert.equal(ret.headerBold,true);
 assert.deepEqual(ret.extra,{B5:0,B6:-4.25,B7:'0007'});
 assert.equal(ret.download.failure,null);
 assert.equal(ret.download.filename,'input-two-sheets.xlsx');
 assert.deepEqual(ret.errors,[]);
 assert.deepEqual(ret.externalRequests,[]);
 console.log('PASS: XLSX round-trip and typed numeric cells');
 console.log(JSON.stringify(ret,null,2));
} catch(e){console.log('FAILED',e.stack);console.log('LOGS',JSON.stringify(logs));process.exitCode=1;}
finally{await browser.close();}
