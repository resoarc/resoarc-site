"""Interactive-free Windows acceptance of all three engines and CLI outputs.
Synthetic fixtures only. Never scans the actual user profile or downloads.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import app
import common


def main():
    passed = []
    with tempfile.TemporaryDirectory(prefix='ResoArc_Windows_QA_') as folder:
        root = Path(folder) / '日本語 テスト files'
        root.mkdir()
        for mode in ('secret', 'log', 'file'):
            paths = [Path(s) for s in app.build_samples(mode, root)]
            original_hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
            result = app.TOOLS[mode][3]([str(p) for p in paths])
            assert result.scanned > 0, mode
            assert result.findings, mode
            report = root / f'report-{mode}.json'
            common.export_json(report, result)
            document = json.loads(report.read_text(encoding='utf-8'))
            assert document['tool'] == result.app
            assert document['version'].startswith('0.3.0-'), document['version']
            assert document['findings'], mode
            assert all(hashlib.sha256(p.read_bytes()).hexdigest() == original_hashes[str(p)] for p in paths), mode
            # CLI uses real process invocation rather than an in-process mock.
            cli_report = root / f'cli-{mode}.csv'
            invocation = [sys.executable, str(Path(__file__).resolve().parent.parent / 'app.py'),
                          '--mode', mode, '--output', str(cli_report), '--format', 'csv', *map(str, paths)]
            proc = subprocess.run(invocation, capture_output=True, text=True, timeout=60)
            assert proc.returncode in (1, 2), (mode, proc.stdout, proc.stderr)
            assert cli_report.exists() and cli_report.stat().st_size > 0
            passed.append({'mode': mode, 'engine_scanned': result.scanned,
                           'findings': len(result.findings), 'cli_code': proc.returncode})
    print(json.dumps({'windows_acceptance': 'PASS', 'checks': passed}, ensure_ascii=False))


if __name__ == '__main__':
    main()
