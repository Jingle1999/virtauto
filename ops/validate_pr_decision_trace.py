#!/usr/bin/env python3
"""
validate_pr_decision_trace.py

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


ACCEPTED_EXACT = {"decision_trace.md", "decision_trace.json"}
ACCEPTED_SUFFIXES = (".decision_trace.md", ".decision_trace.json")


def sh(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()


def list_changed_files() -> list[str]:
    # In PR workflows, HEAD is the PR tip. We compare to merge-base with origin/main if available.
    # Fallback to comparing against origin/main directly.
    base_ref = os.environ.get("GITHUB_BASE_REF", "main")

    # Ensure refs exist (Actions checkout usually fetches enough, but be defensive)
    try:
        sh(["git", "fetch", "--no-tags", "--prune", "--depth=50", "origin", base_ref])
    except Exception:
        pass

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
    return 0


if __name__ == "__main__":
    sys.exit(main())
