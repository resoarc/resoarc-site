import {build} from 'esbuild';
import {mkdir, readFile, writeFile} from 'node:fs/promises';

const result=await build({
  entryPoints:['src/browser.js'],
  outfile:'dist/resoarc-backup.js',
  bundle:true,
  format:'iife',
  target:'es2020',
  write:false,
  legalComments:'none',
});
const license=await readFile('node_modules/fflate/LICENSE','utf8');
const header='/*\nResoArc Backup & Migration 0.1 alpha (MIT)\n' +
  'Includes fflate 0.8.2, licensed under the MIT License:\n\n' + license + '\n*/\n';
await mkdir('dist',{recursive:true});
await writeFile('dist/resoarc-backup.js',header + new TextDecoder().decode(result.outputFiles[0].contents));
console.log('Generated dist/resoarc-backup.js (with third-party license notice)');
