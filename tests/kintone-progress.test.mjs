import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync, cpSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const repo = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const sourceData = JSON.parse(readFileSync(join(repo, 'docs/kintone-progress/tracker.json'), 'utf8'));
const sourceMarkdown = readFileSync(join(repo, 'docs/kintone-progress/README.md'), 'utf8');
const sourceScript = readFileSync(join(repo, 'scripts/kintone-progress.mjs'), 'utf8');

function run(mutator = () => {}, md = sourceMarkdown) {
  const dir = mkdtempSync(join(tmpdir(), 'resoarc-kintone-progress-'));
  try {
    mkdirSync(join(dir, 'docs/kintone-progress'), { recursive: true });
    mkdirSync(join(dir, 'scripts'), { recursive: true });
    const data = structuredClone(sourceData);
    mutator(data);
    writeFileSync(join(dir, 'docs/kintone-progress/tracker.json'), JSON.stringify(data) + '\n');
    writeFileSync(join(dir, 'docs/kintone-progress/README.md'), md);
    writeFileSync(join(dir, 'scripts/kintone-progress.mjs'), sourceScript);
    return spawnSync(process.execPath, [join(dir, 'scripts/kintone-progress.mjs'), '--check'], { encoding: 'utf8', timeout: 10000 });
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

test('canonical 18+11 inventory and Markdown are valid', () => {
  const result = run();
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /29 tracked items/);
});

test('duplicate product IDs fail before release', () => {
  const result = run(d => { d.items[0].id = d.items[1].id; });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /duplicate ids/);
});

test('unverified feature cannot be marked approved', () => {
  const result = run(d => { d.items[11].release_decision = 'approved'; });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /unverified gates/);
});

test('a missing unit evidence record cannot pass', () => {
  const result = run(d => { d.items[0].unit_tests = null; });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /unit pass without evidence/);
});

test('unknown gate status is rejected', () => {
  const result = run(d => { d.items[0].gates.signature = 'likely-good'; });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /unknown gate status/);
});

test('dashboard generated before data change is rejected as stale', () => {
  const result = run(d => { d.items[11].name = 'changed name without regenerating dashboard'; });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /stale/);
});

test('missing item and unrecognized schema fail validation', () => {
  const missing = run(d => { d.items.pop(); });
  assert.notEqual(missing.status, 0);
  assert.match(missing.stderr, /expected exactly/);
  const invalid = run(d => { d.schema_version = 500; });
  assert.notEqual(invalid.status, 0);
  assert.match(invalid.stderr, /unknown inventory/);
});
