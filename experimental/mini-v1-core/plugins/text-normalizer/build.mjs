import {readFileSync,writeFileSync,mkdirSync,copyFileSync} from 'node:fs';
import {resolve,dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
const dir=dirname(fileURLToPath(import.meta.url));
const root=resolve(dir,'../../../..');
const out=resolve(dir,'out/src');
const core=readFileSync(join(root,'src/core.mjs'),'utf8').replaceAll('export function ','function ');
const bridge=readFileSync(join(dir,'runtime.mjs'),'utf8').replaceAll('export function ','function ');
const js='(function(pluginId){\n\'use strict\';\n'+core+'\n'+bridge+
  '\nregisterTextNormalizer(kintone,kintone.plugin.app.getConfig(pluginId),{normalizeFields});\n})(kintone.$PLUGIN_ID);\n';
for(const n of ['js','html','image'])mkdirSync(join(out,n),{recursive:true});
for(const platform of ['desktop','mobile'])writeFileSync(join(out,'js',platform+'.js'),js);
const configJs=readFileSync(join(dir,'config.js'),'utf8');
writeFileSync(join(out,'js/config.js'),configJs);
copyFileSync(join(dir,'config.html'),join(out,'html/config.html'));
copyFileSync(join(root,'../../plugins/auto-number/src/image/icon.png'),join(out,'image/icon.png'));
const manifest={manifest_version:1,version:'0.2.0',type:'APP',
name:{ja:'ResoArc 入力文字自動整形 (開発版)',en:'ResoArc Text Normalizer dev'},
description:{ja:'文字整形。開発評価用。v1未承認',en:'Text normalization experimental; no v1 approval.'},
icon:'image/icon.png',
desktop:{js:['js/desktop.js']},mobile:{js:['js/mobile.js']},
config:{html:'html/config.html',js:['js/config.js'],required_params:['settings']}};
writeFileSync(join(out,'manifest.json'),JSON.stringify(manifest,null,2)+'\n');
console.log('Built experimental text normalizer assets in '+out);
