// ResoArc v1 safety evidence check. No keys or ZIP binaries handled.
import { readFileSync } from 'node:fs';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
const root=resolve(dirname(fileURLToPath(import.meta.url)), '..');
const read=path=>JSON.parse(readFileSync(join(root,path),'utf8'));
const tracker=read('docs/kintone-progress/tracker.json');
const qa=read('docs/kintone-progress/evidence/mini-beta-v012-recovered-20261017.json');
const pins=read('docs/kintone-progress/evidence/mini-v012-public-key-pins.json');
if(tracker.items.length!==29)throw Error('Expected 29 releases');
const mini=tracker.items.filter(x=>x.group==='mini');
if(mini.length!==18||qa.slugs.length!==18||new Set(qa.slugs).size!==18)throw Error('Expected 18 distinct mini plugins');
const seen=new Set(mini.map(x=>x.slug));
if(qa.slugs.some(s=>!seen.has(s))||qa.slugs.length!==seen.size)throw Error('Mini QA slug mismatch');
const identity=pins.plugin_pubkey_sha256;
if(pins.schema_version!==1||pins.source_release!=='v0.1.2-beta'||
    Object.keys(identity||{}).length!==18||Object.keys(identity).some(k=>!seen.has(k)))
    throw Error('Public key pin set is incomplete or inconsistent');
const digests=Object.values(identity);
if(digests.some(x=>typeof x!=='string'||!/^[a-f0-9]{64}$/.test(x))||
   new Set(digests).size!==18)throw Error('Bad or repeated public-key hash');
if(qa.source.sha256!=='22f22159407063a90fc354cf0ee1af1283f402f25fe554d5f7c49026a4da0edb')
   throw Error('Canonical beta source digest mismatch');
if(qa.v1_qa_source_candidate?.signed!==false)throw Error('Unsigned v1 review source is wrongly labelled');
if(!qa.windows_transfer||qa.windows_transfer.original_source_in_windows_development_folder!==false)
   throw Error('Cannot claim completed Windows copy without an evidence update');
if(mini.some(x=>x.release_decision==='approved'||x.gates.tenant==='passed'))
   throw Error('No isolated tenant product acceptance evidence exists');
console.log('Mini v0.1.2 provenance verified: 18 unique key pins; 29-product release holds intact.');
