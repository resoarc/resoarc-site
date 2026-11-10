#!/usr/bin/env node
// SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
// SPDX-License-Identifier: MIT
// qAIUIck Spec CLI: deterministic specification snapshots and human-readable diffs.
import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { specSnapshot, diffSpecs, impactReport } from '../site/assets/qaiuick/spec.js';

function usage() {
  console.error('Usage: node tools/qaiuick_spec.mjs snapshot app.js output.json');
  console.error('       node tools/qaiuick_spec.mjs diff old.json new.json');
  process.exitCode = 2;
}

async function main() {
  const [command, first, second] = process.argv.slice(2);
  if (!command || !first || !second) return usage();
  if (command === 'snapshot') {
    if (!first.endsWith('.js') || !second.endsWith('.json')) return usage();
    const app = await import(pathToFileURL(resolve(first)).href);
    if (!app.spec) throw new Error('Application must export const spec');
    const normalized = specSnapshot(app.spec);
    await writeFile(resolve(second), JSON.stringify(normalized, null, 2) + '\n', 'utf8');
    console.log('SPEC_SNAPSHOT_OK', normalized.id, 'v' + normalized.version);
  } else if (command === 'diff') {
    const before = JSON.parse(await readFile(resolve(first), 'utf8'));
    const after = JSON.parse(await readFile(resolve(second), 'utf8'));
    const changes = diffSpecs(before, after);
    if (!changes.length) console.log('SPEC_UNCHANGED', after.id);
    for (const change of changes) {
      console.log([
        change.type === 'added' ? '+' : change.type === 'removed' ? '-' : '~',
        change.path,
        change.before === undefined ? '' : JSON.stringify(change.before),
        '=>',
        change.after === undefined ? '' : JSON.stringify(change.after),
      ].join(' '));
    }
    if (changes.length) {
      console.log('SPEC_CHANGED_FIELDS', changes.length);
      const report = impactReport(before, after);
      console.log('SPEC_IMPACT_AREAS', report.impacts.length);
      for (const impact of report.impacts)
        console.log('IMPACT', impact.area, '|', impact.test, '|', impact.risk);
      if (report.needsDataReview) console.log('DATA_REVIEW_REQUIRED');
    }
  } else usage();
}
main().catch(error => { console.error('SPEC_ERROR', error.message); process.exitCode = 1; });
