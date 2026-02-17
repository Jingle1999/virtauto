#!/usr/bin/env python3
"""
validate_pr_decision_trace.py

Goal:
- Enforce that every PR contains (adds or modifies) a PR-scoped decision trace artifact.

Accepted artifacts (at least one must be changed in the PR):
- decision_trace.md (repo root)
- decision_trace.json (repo root)
- decision_traces/**/.decision_trace.md
- decision_traces/**/.decision_trace.json

Why:
- Avoid merge conflicts / deadlocks caused by a single shared root decision_trace across parallel PRs.
- Keep governance: every PR must justify intent/scope/authority/outcome with a trace artifact.
"""

from __future__ import annotations

import subprocess
import sys
from fnmatch import fnmatch

ALLOWED_DECISION_TRACE_PATTERNS = [
    "decision_trace.md",
    "decision_trace.json",
    "decision_traces/**.decision_trace.md",
    "decision_traces/**.decision_trace.json",
]


def run(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()


def get_merge_base() -> str:
    # Works for GitHub Actions checkout of PR head (full history enabled by workflow)
    # merge-base between PR HEAD and origin/main
    return run(["git", "merge-base", "origin/main", "HEAD"])


def get_changed_files(merge_base: str) -> list[str]:
    out = run(["git", "diff", "--name-only", f"{merge_base}..HEAD"])
    if not out:
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def matches_any(path: str, patterns: list[str]) -> bool:
    return any(fnmatch(path, pat) for pat in patterns)


def main() -> int:
    merge_base = get_merge_base()
    changed_files = get_changed_files(merge_base)

    if not changed_files:
        print("[FAIL] No files changed in PR (unexpected).")
        return 1

    if not any(matches_any(f, ALLOWED_DECISION_TRACE_PATTERNS) for f in changed_files):
        print("[FAIL] Missing mandatory decision trace artifact for this Pull Request.")
        print("Add/modify at least one of the following in this PR:")
        for p in ALLOWED_DECISION_TRACE_PATTERNS:
            print(f" - {p}")
        print("\nTip: preferred is a PR-specific file to avoid conflicts, e.g.:")
        print(" decision_traces/pr-<id>.decision_trace.md")
        return 1

    print("[PASS] PR contains a decision trace artifact change.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
