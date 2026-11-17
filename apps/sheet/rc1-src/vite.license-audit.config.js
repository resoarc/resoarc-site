import { defineConfig } from 'vite';
import original from './vite.config.js';
import { writeFileSync, mkdirSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
const auditDir = resolve(process.env.RESOARC_SHEET_AUDIT_DIR || './qa/bundle-audit');
const report = resolve(auditDir,'bundled-modules.json');
const outDir = resolve(auditDir,'dist');
export default defineConfig({
  ...original,
  build: {
    ...original.build,
    outDir, emptyOutDir: true,
    rollupOptions: {
      ...(original.build?.rollupOptions || {}),
      plugins: [{
        name: 'resoarc-bundle-licenses-readonly-audit',
        generateBundle(options, bundle) {
          const items=[];
          for(const [file, artifact] of Object.entries(bundle)) {
            if(artifact.type !== 'chunk') continue;
            for(const [source, metadata] of Object.entries(artifact.modules || {})) {
              items.push({chunk:file, source, renderedLength:metadata.renderedLength});
            }
          }
          mkdirSync(dirname(report),{recursive:true});
          writeFileSync(report, JSON.stringify(items,null,2));
        }
      }]
    }
  }
});
