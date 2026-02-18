#!/usr/bin/env python3
"""
validate_pr_decision_trace.py

<<<<<<< Jingle1999-patch-877947
PR policy:
- Every PR must include a decision trace artifact.
- Accepted:
  - decision_trace.md
  - decision_trace.json
  - any file matching **/*.decision_trace.md
  - any file matching **/*.decision_trace.json
"""

import os
import subprocess
import sys
from pathlib import Path
=======
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
>>>>>>> main

ALLOWED_DECISION_TRACE_PATTERNS = [
    "decision_trace.md",
    "decision_trace.json",
    "decision_traces/**.decision_trace.md",
    "decision_traces/**.decision_trace.json",
]

<<<<<<< Jingle1999-patch-877947
ACCEPTED_EXACT = {"decision_trace.md", "decision_trace.json"}
ACCEPTED_SUFFIXES = (".decision_trace.md", ".decision_trace.json")
=======
>>>>>>> main

def run(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()

<<<<<<< Jingle1999-patch-877947
def sh(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()
=======
>>>>>>> main

def get_merge_base() -> str:
    # Works for GitHub Actions checkout of PR head (full history enabled by workflow)
    # merge-base between PR HEAD and origin/main
    return run(["git", "merge-base", "origin/main", "HEAD"])

<<<<<<< Jingle1999-patch-877947
def list_changed_files() -> list[str]:
    # In PR workflows, HEAD is the PR tip. We compare to merge-base with origin/main if available.
    # Fallback to comparing against origin/main directly.
    base_ref = os.environ.get("GITHUB_BASE_REF", "main")
=======

def get_changed_files(merge_base: str) -> list[str]:
    out = run(["git", "diff", "--name-only", f"{merge_base}..HEAD"])
    if not out:
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def matches_any(path: str, patterns: list[str]) -> bool:
    return any(fnmatch(path, pat) for pat in patterns)
>>>>>>> main

    # Ensure refs exist (Actions checkout usually fetches enough, but be defensive)
    try:
        sh(["git", "fetch", "--no-tags", "--prune", "--depth=50", "origin", base_ref])
    except Exception:
        pass

<<<<<<< Jingle1999-patch-877947
    try:
        merge_base = sh(["git", "merge-base", "HEAD", f"origin/{base_ref}"])
        diff_range = f"{merge_base}..HEAD"
    except Exception:
        diff_range = f"origin/{base_ref}..HEAD"

    out = sh(["git", "diff", "--name-only", diff_range])
    files = [f for f in out.splitlines() if f.strip()]
    return files


def has_decision_trace(files: list[str]) -> bool:
    for f in files:
        name = Path(f).name
        if name in ACCEPTED_EXACT:
            return True
        if f.endswith(ACCEPTED_SUFFIXES):
            return True
    return False


def main() -> int:
    files = list_changed_files()

    if not has_decision_trace(files):
        print("[FAIL] Missing mandatory decision trace artifact for this Pull Request.")
        print("Add or modify at least one of the following in this PR:")
        print("  - decision_trace.md")
        print("  - decision_trace.json")
        print("  - **/*.decision_trace.md")
        print("  - **/*.decision_trace.json")
        print("\nTip (minimal): add a file named 'decision_trace.md' at repo root with:")
        print("  - Decision / Intent")
        print("  - Authority")
        print("  - Scope (files/modules touched)")
        print("  - Expected outcome")
        return 1

    print("[PASS] Decision trace artifact present in PR.")
=======
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
>>>>>>> main
    return 0


if __name__ == "__main__":
    sys.exit(main())
