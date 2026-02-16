#!/usr/bin/env python3
"""
Require a decision trace artifact for every PR that changes code/config.

PASS if the PR modifies at least one of:
- decision_trace.md
- decision_trace.json
- any file ending with .decision_trace.md (any path)
"""

from __future__ import annotations

import fnmatch
import os
import subprocess
import sys
from typing import List


ALLOWED = [
    "decision_trace.md",
    "decision_trace.json",
]
ALLOWED_GLOB = [
    "**/*.decision_trace.md",
]


def _run(cmd: List[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()


def _changed_files(base: str, head: str) -> List[str]:
    out = _run(["git", "diff", "--name-only", f"{base}...{head}"])
    files = [line.strip() for line in out.splitlines() if line.strip()]
    return files


def _matches_allowed(path: str) -> bool:
    if path in ALLOWED:
        return True
    # glob match for .decision_trace.md anywhere
    for pat in ALLOWED_GLOB:
        if fnmatch.fnmatch(path, pat) or fnmatch.fnmatch(path, pat.replace("**/", "")):
            return True
    return False


def main() -> int:
    base = os.environ.get("GITHUB_BASE_SHA", "").strip()
    head = os.environ.get("GITHUB_SHA", "").strip()

    # Fallbacks that work in PR context where merge-base is available
    if not base:
        # Try merge-base of HEAD and origin/main
        try:
            base = _run(["git", "merge-base", "HEAD", "origin/main"])
        except Exception:
            base = ""
    if not head:
        head = "HEAD"

    if not base:
        print("[WARN] No merge-base found; skipping PR decision trace validation.")
        return 0

    changed = _changed_files(base, head)

    if any(_matches_allowed(p) for p in changed):
        print("[OK] PR contains a decision trace artifact change.")
        return 0

    print("[FAIL] Missing mandatory decision trace artifact for this Pull Request.")
    print("Add or modify at least one of the following in this PR:")
    for a in ALLOWED:
        print(f"  - {a}")
    print("  - any file ending with .decision_trace.md (any folder)")
    print("")
    print("Tip (minimal): add docs/decision_traces/<topic>.decision_trace.md")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
