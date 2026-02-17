#!/usr/bin/env python3
"""
validate_pr_decision_trace.py

Goal:
- Enforce that every PR contains (adds or modifies) a decision trace artifact.
- Accept either:
  - decision_trace.md (repo root)
  - decision_trace.json (repo root)
  - any file matching:
      decision_traces/**/*.decision_trace.md
      decision_traces/**/*.decision_trace.json

Why:
- Avoid merge conflicts on a single root decision_trace.md across many parallel PRs.
- Still keep strict governance: every PR must justify intent/scope/authority/outcome.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from fnmatch import fnmatch

ALLOWED_ROOT_FILES = {"decision_trace.md", "decision_trace.json"}
ALLOWED_GLOB_PATTERNS = [
    "decision_traces/**/*.decision_trace.md",
    "decision_traces/**/*.decision_trace.json",
]


def run(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()


def get_merge_base() -> str:
    # Works on GH Actions checkout of PR head (full history enabled in workflow)
    return run(["git", "merge-base", "origin/main", "HEAD"])


def get_changed_files(merge_base: str) -> list[str]:
    out = run(["git", "diff", "--name-only", f"{merge_base}..HEAD"])
    if not out:
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def matches_glob(path: str, pattern: str) -> bool:
    # fnmatch doesn't understand ** reliably across platforms unless we normalize.
    # We'll do a simple approach: try direct fnmatch and also with Path-style.
    path_norm = path.replace("\\", "/")
    pat_norm = pattern.replace("\\", "/")
    return fnmatch(path_norm, pat_norm)


def main() -> int:
    try:
        merge_base = get_merge_base()
    except Exception as e:
        print(f"[FAIL] Could not determine merge-base: {e}")
        return 2

    changed = get_changed_files(merge_base)

    # Fast path: allow root decision_trace.* if it is changed in this PR
    for f in changed:
        if f in ALLOWED_ROOT_FILES:
            print("[PASS] PR contains modified decision trace artifact:", f)
            return 0

    # Allow PR-specific decision traces under decision_traces/**
    for f in changed:
        for pat in ALLOWED_GLOB_PATTERNS:
            if matches_glob(f, pat):
                print("[PASS] PR contains modified decision trace artifact:", f)
                return 0

    print("[FAIL] Missing mandatory decision trace artifact for this Pull Request.")
    print("Add OR modify at least one of the following in this PR:")
    for f in sorted(ALLOWED_ROOT_FILES):
        print(f" - {f}")
    for pat in ALLOWED_GLOB_PATTERNS:
        print(f" - {pat}")
    print("")
    print("Tip: preferred is a PR-specific file to avoid conflicts, e.g.:")
    print("  decision_traces/pr-<id>.decision_trace.md")
    return 1


if __name__ == "__main__":
    sys.exit(main())
