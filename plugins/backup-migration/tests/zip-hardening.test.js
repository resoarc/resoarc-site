import test from 'node:test';
import assert from 'node:assert/strict';
import {Zip,ZipPassThrough,strToU8,zipSync} from 'fflate';
import {inspectArchive,MAX_ZIP_ENTRIES} from '../src/core.js';

// The streaming ZIP writer permits duplicate entry names; a normal JS object
// passed to zipSync cannot represent this malicious archive.
async function duplicateEntryZip(){
  return new Promise((resolve,reject)=>{
    const chunks=[];
    const writer=new Zip((error,data,final)=>{
      if(error){reject(error);return;}
      chunks.push(data);
      if(final)resolve(Buffer.concat(chunks.map(chunk=>Buffer.from(chunk))));
    });
    for(const text of ['first','second']){
      const entry=new ZipPassThrough('manifest.json');
      writer.add(entry);
      entry.push(strToU8(text),true);
    }
    writer.end();
  });
}

test('untrusted ZIP with duplicated entry path is rejected before processing data',async()=>{
  const zip=await duplicateEntryZip();
  await assert.rejects(()=>inspectArchive(zip),/重複しています/);
});

test('ZIP with more file headers than the caller limit is rejected',async()=>{
  const zip=zipSync({
    'manifest.json':strToU8('{}'),
    'schema/fields.json':strToU8('{}')
  });
  await assert.rejects(()=>inspectArchive(zip,{maxEntries:1}),/ファイル数が上限/);
});

test('ZIP file entry cap cannot be silently disabled or increased',async()=>{
  const zip=zipSync({'manifest.json':strToU8('x')});
  for(const maxEntries of [0,-1,NaN,1.5,MAX_ZIP_ENTRIES+1])
    await assert.rejects(()=>inspectArchive(zip,{maxEntries}),/ファイル数上限が不正/);
});
