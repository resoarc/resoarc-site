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
const win=read('docs/kintone-progress/evidence/mini-v012-windows-e2e-mock-20261017.json');
if(!qa.windows_transfer || qa.windows_transfer.original_source_in_windows_development_folder!==true ||
   qa.windows_transfer.file_count!==152 ||
   qa.windows_transfer.tree_sha256!=='64c1954c736a8e72ed33e3da6afbb94255714847601e83a70ae30f18e2f0ea3a')
   throw Error('Canonical Windows source import evidence missing');
if(win.source_import?.source_tree_sha256!==qa.windows_transfer.tree_sha256 ||
   win.hardening_windows_qa?.content_tree_sha256!=='7e4039c144f84d4143e49fffe409c791f7bb67f6017622d9e636c7bbc00a4db4' ||
   win.hardening_windows_qa?.manifest_with_mobile_section!==0 ||
   win.hardening_windows_qa?.tenant_installed!==false ||
   win.hardening_windows_qa?.signed_package_created!==false)
   throw Error('Windows proof or release holds are inconsistent');
if(mini.some(x=>x.release_decision==='approved'||x.gates.tenant==='passed'))
   throw Error('No isolated tenant product acceptance evidence exists');
const mobile=read('docs/kintone-progress/evidence/mini-v1-text-mobile-20261017.json');
const bundle=mobile.source_only_bundle;
if(mobile.product!=='text-normalizer'||mobile.unit_tests?.passed!==12||
   mobile.unit_tests?.failed!==0||mobile.manifest_checks?.with_mobile_entrypoint!==1||
   mobile.manifest_checks?.other_products_without_mobile!==17||
   bundle?.sha256!=='8d153f2dfda3969d53bcb4a5e069d72ef5fa0a94a30e8f784a16408ec626dff3' ||
   bundle?.file_count!==157||bundle?.javaScript_files!==38||
   bundle?.digitally_signed!==false||bundle?.publicly_released!==false||
   bundle?.kintone_installable!==false||
   mini.find(x=>x.slug==='text-normalizer')?.gates?.mobile!=='unverified')
   throw Error('Experimental source-only mobile proof or release hold differs from evidence');
const mobile16=read('docs/kintone-progress/evidence/mini-v1-mobile16-windows-20261017.json');
const mobileSet=new Set(mobile16.design?.supported_mobile_candidate_slugs||[]);
const excluded=new Set(mobile16.design?.not_supported_slugs||[]);
if(mobileSet.size!==16||excluded.size!==2||
   [...mobileSet].some(slug=>!seen.has(slug)||excluded.has(slug))||
   [...excluded].some(slug=>!seen.has(slug))||
   mobileSet.size+excluded.size!==mini.length)throw Error('Mobile 16/2 coverage mismatch');
if(mobile16.tests?.mobile_event_mock_cases!==20||
   mobile16.tests?.security_hardening_tests!==8||
   mobile16.tests?.combined_pass!==28||mobile16.tests?.combined_fail!==0||
   mobile16.tests?.desktop_event_registration_handlers!==31||
   mobile16.tests?.edge_mock_browser_cases!==17||
   mobile16.tests?.javaScript_syntax_files!==53||
   mobile16.tests?.javaScript_syntax_pass!==53||
   mobile16.tests?.mobile_manifests!==16||
   mobile16.tests?.manifests!==18||
   mobile16.tests?.missing_manifest_assets!==0||
   mobile16.tests?.signer_fail_closed_without_original_keys!==true||
   mobile16.tests?.signing_keys_generated!==false||
   mobile16.tests?.release_zip_generated!==false)throw Error('Mobile QA evidence mismatch');
if(mobile16.source_bundle?.sha256!=='0e4fd2354f9054a9b409be168b81bb9f0425021fc0de69c2f4934c66c8476467'||
   mobile16.source_bundle?.file_count!==174||
   mobile16.source_bundle?.is_signed!==false||
   mobile16.source_bundle?.is_kintone_installable!==false||
   mobile16.release_decision!=='hold')throw Error('Mobile source-only bundle mislabelled');
for(const product of mini){
  if(product.gates.mobile!=='unverified'||product.release_decision!=='hold')throw Error('Mobile gate approved without tenant proof: '+product.slug);
  if(mobileSet.has(product.slug)){
    if(product.mobile_source_evidence!=='docs/kintone-progress/evidence/mini-v1-mobile16-windows-20261017.json'||
       product.v1_preparation?.mobile_manifest!=='generated_source_only_v1_candidate')
      throw Error('Mobile source item missing evidence: '+product.slug);
  }else if(product.v1_preparation?.mobile_manifest!=='not_implemented_due_to_mobile_api_behavior')
    throw Error('Unsupported mobile feature must not claim runtime: '+product.slug);
}
console.log('Mini source provenance and 16 mobile candidates verified; all 29 releases remain HOLD.');
