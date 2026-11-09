#!/usr/bin/env python3
"""Conservative GitHub Actions trust-boundary audit (stdlib only).

This is a repository policy check, not proof that the GitHub runner cannot be
compromised. All protected-branch PRs run the same checker before merging.
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
UNTRUSTED = ("github.event.pull_request.", "github.event.issue.", "github.event.comment.",
             "github.event.head_commit.", "github.event.commits.", "github.event.inputs.",
             "github.event.workflow_run.", "github.head_ref", "inputs.")
EXPR_OPEN = "$" + "{{"


def audit() -> list[str]:
    problems: list[str] = []
    files = sorted(WORKFLOWS.glob("*.yml")) + sorted(WORKFLOWS.glob("*.yaml"))
    if len(files) < 10:
        problems.append("Expected the ten original workflows; audit the current inventory")
    for path in files:
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        if re.search(r"(?m)^\s*(?:pull_request_target|workflow_run)\s*:", text):
            problems.append(f"{path.name}: elevated/untrusted workflow trigger requires separate review")
        if re.search(r"(?m)^\s*permissions\s*:\s*write-all", text):
            problems.append(f"{path.name}: write-all token permission prohibited")
        # Never pass event-controlled strings into inline bash/PowerShell via
        # expression substitution. Pass through env and validate first.
        in_run = False
        run_indent = 0
        for lineno, line in enumerate(lines, 1):
            indent = len(line) - len(line.lstrip())
            if in_run and line.strip() and indent <= run_indent:
                in_run = False
            if re.match(r"\s*run:\s*[|>]\s*$", line):
                in_run, run_indent = True, indent
            inline = line.strip().startswith("run: ") or in_run
            if inline and EXPR_OPEN in line and any(x in line for x in UNTRUSTED):
                problems.append(f"{path.name}:{lineno}: untrusted expression directly interpolated in run")
            action = re.search(r"(?<![A-Za-z])uses:\s*([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)?)@([^\s#]+)", line)
            if action and not re.fullmatch(r"[0-9a-f]{40}", action.group(2)):
                problems.append(f"{path.name}:{lineno}: action is not pinned to a full commit SHA")
        if re.search(r"(?m)^\s+pull_request\s*:", text) and EXPR_OPEN + " secrets." in text:
            problems.append(f"{path.name}: PR workflow references a privileged secret")
        if EXPR_OPEN + " secrets." in text:
            if "workflow_dispatch:" not in text and "schedule:" not in text:
                problems.append(f"{path.name}: secret-consuming workflow lacks trusted trigger")
        if "contents: write" in text and "pull_request:" in text:
            problems.append(f"{path.name}: write-capable workflow also handles pull_request")
        if "contents: write" in text and "github.repository ==" not in text:
            problems.append(f"{path.name}: release writer lacks explicit repository identity guard")
        # Read-only checkout is expected throughout; no lingering checkout token.
        if "actions/checkout@" in text and "persist-credentials: false" not in text:
            problems.append(f"{path.name}: checkout credentials not explicitly discarded")
    return problems


if __name__ == "__main__":
    problems = audit()
    for item in problems:
        print("FAIL:", item, file=sys.stderr)
    print(f"Audited GitHub Actions: {len(list(WORKFLOWS.glob('*.yml'))) + len(list(WORKFLOWS.glob('*.yaml')))}")
    print("Policy: no pull_request_target, untrusted run interpolations, unpinned actions, or writable PR tokens")
    raise SystemExit(1 if problems else 0)
