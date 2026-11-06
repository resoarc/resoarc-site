#!/usr/bin/env python3
"""Metadata-only SARIF accounting. Never print finding messages or code snippets."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

SCHEMA = "resoarc.codeql-sarif-summary.v1"
LANGUAGES = frozenset(("go", "python", "javascript-typescript", "actions"))
IDENTIFIER = re.compile(r"^[A-Za-z0-9._/-]{1,160}$")
LIMIT = 64 * 1024 * 1024
EXAMPLES = 80

def clean_path(value):
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        return "<redacted>"
    if value.startswith("/") or ".." in value.split("/") or "\\" in value:
        return "<redacted>"
    return value

def clean_id(value):
    return value if isinstance(value, str) and IDENTIFIER.fullmatch(value) else "<redacted>"

def extract(document):
    if not isinstance(document, dict) or document.get("version") != "2.1.0":
        raise ValueError("invalid SARIF version")
    runs = document.get("runs")
    if not isinstance(runs, list) or not runs:
        raise ValueError("no SARIF runs")
    rule_counts = Counter()
    level_counts = Counter()
    examples = []
    for run in runs:
        if not isinstance(run, dict) or not isinstance(run.get("results", []), list):
            raise ValueError("invalid SARIF results")
        for result in run.get("results", []):
            if not isinstance(result, dict):
                raise ValueError("invalid result")
            rule = clean_id(result.get("ruleId"))
            level = result.get("level", "warning")
            if level not in ("error", "warning", "note", "none"):
                level = "unknown"
            rule_counts[rule] += 1
            level_counts[level] += 1
            if len(examples) == EXAMPLES:
                continue
            locations = result.get("locations", [])
            first = locations[0] if isinstance(locations, list) and locations and isinstance(locations[0], dict) else {}
            location = first.get("physicalLocation", {})
            if not isinstance(location, dict): location = {}
            artifact = location.get("artifactLocation", {})
            if not isinstance(artifact, dict): artifact = {}
            region = location.get("region", {})
            if not isinstance(region, dict): region = {}
            lineno = region.get("startLine")
            if not isinstance(lineno, int) or not 1 <= lineno <= 10000000:
                lineno = None
            examples.append({"rule_id": rule, "level": level, "file": clean_path(artifact.get("uri")), "line": lineno})
    return rule_counts, level_counts, examples

def summarize(directory, language, output):
    if language not in LANGUAGES:
        raise ValueError("unsupported language")
    files = sorted(Path(directory).rglob("*.sarif"))
    if not files or len(files) > 16:
        raise ValueError("missing/excessive SARIF")
    rules, levels, examples = Counter(), Counter(), []
    for file in files:
        if not file.is_file() or file.stat().st_size > LIMIT:
            raise ValueError("invalid SARIF file")
        r, l, items = extract(json.loads(file.read_text(encoding="utf8")))
        rules.update(r)
        levels.update(l)
        examples.extend(items[:max(0, EXAMPLES-len(examples))])
    report = {
        "schema": SCHEMA, "language": language,
        "sarif_results_not_unique_alerts": sum(rules.values()),
        "sarif_file_count": len(files),
        "level_counts": dict(sorted(levels.items())),
        "rule_counts": dict(sorted(rules.items())),
        "examples_max_80": examples,
        "contains_raw_source_or_messages": False,
        "human_reviewed": False, "formal_release": "HOLD"
    }
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=True)+"\n",encoding="utf8")
    print("CODEQL_REAL_FINDINGS " + json.dumps({"schema":SCHEMA,"language":language,"results":sum(rules.values()),
                      "rules":len(rules),"level_counts":dict(levels),"formal_release":"HOLD"},sort_keys=True))
    return report

def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--sarif-dir", required=True)
    p.add_argument("--language", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args(argv)
    try:
        summarize(a.sarif_dir, a.language, a.output)
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        print(json.dumps({"schema":SCHEMA,"result":"FAIL_CLOSED","formal_release":"HOLD"}))
        return 2
    return 0

if __name__ == "__main__":
    sys.exit(main())
