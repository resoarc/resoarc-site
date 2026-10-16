#!/usr/bin/env node
// Fail-closed cross-check for the per-product QA evidence in the ResoArc portfolio.
// Default: node scripts/kintone-evidence.mjs
// For isolated tests: node scripts/kintone-evidence.mjs --root <fixture-root>
import { readFileSync } from 'node:fs';
import { resolve, dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
const args = process.argv.slice(2);
if (args.length !== 0 && !(args.length === 2 && args[0] === '--root' && args[1])) {
  throw new Error('usage: kintone-evidence.mjs [--root fixture-dir]');
}
const root = args.length ? resolve(args[1]) : resolve(dirname(fileURLToPath(import.meta.url)), '..');
const path = name => join(root, 'docs/kintone-progress', name);
const tracker = JSON.parse(readFileSync(path('tracker.json'), 'utf8'));
const unit = JSON.parse(readFileSync(path('evidence/unit-tests-20261017.json'), 'utf8'));
const manifest = JSON.parse(readFileSync(path('evidence/manifest-preflight-20261017.json'), 'utf8'));
function fail(message) { throw new Error('Evidence mismatch: ' + message); }
const packages = tracker.items.filter(x => x.group === 'package');
const mini = tracker.items.filter(x => x.group === 'mini');
if (packages.length !== 11 || mini.length !== 18) fail('expected 11 packages and 18 mini features');
if (unit.schema_version !== 1 || manifest.schema_version !== 1) fail('unknown evidence schema');
if (unit.entries.length !== 11 || manifest.entries.length !== 9) fail('unexpected source evidence count');
const bySlug = entries => {
  const map = new Map(entries.map(x => [x.slug, x]));
  if (map.size !== entries.length) fail('duplicate evidence slugs');
  return map;
};
const units = bySlug(unit.entries), manifests = bySlug(manifest.entries);
let passed = 0, observedManifest = 0;
for (const item of packages) {
  const test = units.get(item.slug);
  if (!test || item.gates.unit !== 'passed') fail(item.slug + ': required unit result missing');
  if (test.tests !== test.passed || test.failed !== 0 || test.exit_code !== 0 ||
      test.passed !== item.unit_tests?.pass || item.unit_tests?.fail !== 0) {
    fail(item.slug + ': unit count or exit code differs from tracker');
  }
  if (item.unit_tests.evidence !== 'docs/kintone-progress/evidence/unit-tests-20261017.json') {
    fail(item.slug + ': incorrect evidence pointer');
  }
  passed += test.passed;
  const staticCheck = manifests.get(item.slug);
  if (staticCheck) {
    if (item.gates.manifest !== 'passed' || staticCheck.passed !== true ||
        (staticCheck.issues || []).length !== 0 ||
        item.manifest_evidence !== 'docs/kintone-progress/evidence/manifest-preflight-20261017.json') {
      fail(item.slug + ': manifest evidence differs from tracker');
    }
    observedManifest++;
  } else if (item.gates.manifest === 'passed') {
    fail(item.slug + ': manifest pass has no evidence');
  }
}
for (const item of mini) {
  if (item.gates.unit === 'passed' && !units.has(item.slug)) fail(item.slug + ': mini test pass is unverified');
  if (item.gates.manifest === 'passed' && !manifests.has(item.slug)) fail(item.slug + ': mini manifest pass is unverified');
}
if (passed !== 187 || unit.passed !== passed || unit.failed !== 0 || unit.total !== passed) {
  fail('aggregate unit test counts differ');
}
if (observedManifest !== 9 || manifest.passed !== 9 || manifest.failed !== 0 || manifest.total !== 9) {
  fail('aggregate static preflight counts differ');
}
console.log('Evidence cross-check passed: 11 packages, ' + passed +
    ' unit tests, 9 manifest checks; mini 18 feature gates remain unverified');
