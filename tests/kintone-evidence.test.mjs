import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const repo = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const evidencePath = 'docs/kintone-progress/evidence/';
const baseline = {
  tracker: JSON.parse(readFileSync(join(repo, 'docs/kintone-progress/tracker.json'), 'utf8')),
  unit: JSON.parse(readFileSync(join(repo, evidencePath, 'unit-rebuild-20261017.json'), 'utf8')),
  manifest: JSON.parse(readFileSync(join(repo, evidencePath, 'manifest-preflight-20261017.json'), 'utf8')),
  miniQa: JSON.parse(readFileSync(join(repo, evidencePath, 'mini-v1-local-qa-20261017.json'), 'utf8')),
  signatures: JSON.parse(readFileSync(join(repo, evidencePath, 'signed-zip-audit-20261017.json'), 'utf8')),
  smoke: JSON.parse(readFileSync(join(repo, evidencePath, 'auto-number-tenant-smoke-20261017.json'), 'utf8'))
};

function run(modify = () => {}) {
  const tmp = mkdtempSync(join(tmpdir(), 'resoarc-evidence-'));
  try {
    const d = structuredClone(baseline);
    modify(d);
    mkdirSync(join(tmp, evidencePath), { recursive: true });
    writeFileSync(join(tmp, 'docs/kintone-progress/tracker.json'), JSON.stringify(d.tracker));
    writeFileSync(join(tmp, evidencePath, 'unit-rebuild-20261017.json'), JSON.stringify(d.unit));
    writeFileSync(join(tmp, evidencePath, 'manifest-preflight-20261017.json'), JSON.stringify(d.manifest));
    writeFileSync(join(tmp, evidencePath, 'mini-v1-local-qa-20261017.json'), JSON.stringify(d.miniQa));
    writeFileSync(join(tmp, evidencePath, 'signed-zip-audit-20261017.json'), JSON.stringify(d.signatures));
    writeFileSync(join(tmp, evidencePath, 'auto-number-tenant-smoke-20261017.json'), JSON.stringify(d.smoke));
    return spawnSync(process.execPath, [join(repo, 'scripts/kintone-evidence.mjs'), '--root', tmp], {
      encoding: 'utf8', timeout: 10000
    });
  } finally {
    rmSync(tmp, { recursive: true, force: true });
  }
}

test('all 203 unit tests and 9 preflights are traceable', () => {
  const result = run();
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /Evidence cross-check passed/);
});
test('missing a product evidence entry is rejected', () => {
  const result = run(d => { d.unit.entries.pop(); });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /unexpected source evidence count/);
});
test('inflated test result is rejected', () => {
  const result = run(d => { d.unit.entries[0].passed += 1; });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /unit count or exit code differs/);
});
test('manifest pass cannot be asserted without evidence', () => {
  const result = run(d => { d.manifest.entries[0].passed = false; });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /manifest evidence differs/);
});
test('duplicate evidence slug is rejected', () => {
  const result = run(d => { d.unit.entries[0].slug = d.unit.entries[1].slug; });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /duplicate evidence slugs/);
});
test('mini product may not claim unsubstantiated unit pass', () => {
  const result = run(d => { d.tracker.items.find(x => x.group === 'mini').gates.unit = 'passed'; });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /mini test pass is unverified/);
});

test('signed package gate must match audit evidence', () => {
  const result = run(d => { d.tracker.items.find(x => x.slug === 'kanban').gates.signature = 'unverified'; });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /verified signature missing from tracker/);
});
test('unattributed E2E must not approve a specific build', () => {
  const result = run(d => { d.tracker.items.find(x => x.slug === 'auto-number-stable').gates.tenant = 'passed'; });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /unattributed E2E must not approve/);
});
test('missing signature evidence is rejected', () => {
  const result = run(d => { d.signatures.artifacts.pop(); });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /signed ZIP evidence count/);
});

test('missing mini manifest QA evidence blocks all mini claims', () => {
  const result = run(d => { d.miniQa.products.pop(); });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /Mini source QA evidence is incomplete/);
});
test('mini manifest gate requires explicit validated evidence', () => {
  const result = run(d => { d.tracker.items.find(x => x.slug === 'postal-address').manifest_evidence = 'unknown'; });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /mini manifest evidence differs from tracker/);
});
test('missing signing keys must never be reported as successful signing', () => {
  const result = run(d => { d.miniQa.signing.private_keys_generated = true; });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /Mini source QA evidence is incomplete/);
});
