#!/usr/bin/env python3
"""
Validate that every Pull Request carries an explicit decision trace artifact.

Phase 2 goal: "No decision without trace" (Explainability v1).

This check is intentionally mechanical (not "AI"):
  - For PRs, require that the PR adds/modifies at least one of:
      * decision_trace.md
      * decision_trace.json

The file can live anywhere in the repository.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import List, Tuple


REQUIRED_BASENAMES = ("decision_trace.md", "decision_trace.json")


def run(cmd: List[str]) -> Tuple[int, str]:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return p.returncode, p.stdout.strip()


def load_event() -> dict:
    event_path = os.environ.get("GITHUB_EVENT_PATH", "")
    if not event_path or not os.path.exists(event_path):
        return {}
    with open(event_path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    if event_name != "pull_request":
        print(f"[OK] validate_pr_decision_trace: not a pull_request event ({event_name}).")
        return 0

    event = load_event()
    pr = (event.get("pull_request") or {})
    base_sha = (pr.get("base") or {}).get("sha")
    head_sha = (pr.get("head") or {}).get("sha")

    if not base_sha or not head_sha:
        print("[FAIL] Could not read base/head SHA from GitHub event payload.")
        print(f"Event keys present: {list(event.keys())}")
        return 1

    # Determine changed files for this PR (merge-base diff).
    rc, out = run(["git", "diff", "--name-only", f"{base_sha}...{head_sha}"])
    if rc != 0
        # Fallback: GitHub erlaubt nicht immer das Fetchen beliebiger SHAs.
        pr_number = pr.get("number")
        base_ref = (pr.get("base") or {}).get("ref")

        if pr_number and base_ref:
            print("[WARN] git diff by SHA failed; falling back to PR refs fetch.")
            rc2, out2 = run([
                "git", "fetch", "--no-tags", "--prune", "origin",
                f"+refs/heads/{base_ref}:refs/remotes/origin/{base_ref}",
                f"+refs/pull/{pr_number}/head:refs/remotes/pull/{pr_number}/head",
            ])
            if rc2 == 0:
                base_refspec = f"refs/remotes/origin/{base_ref}"
                head_refspec = f"refs/remotes/pull/{pr_number}/head"
                rc, out = run(["git", "diff", "--name-only", f"{base_refspec}...{head_refspec}"])

        if rc != 0:
            print("[FAIL] git diff failed. Output:")
            print(out)
            return 1

    changed = [line.strip() for line in out.splitlines() if line.strip()]
    hits = [p for p in changed if os.path.basename(p) in REQUIRED_BASENAMES]

    if hits:
        print("[OK] Decision trace artifact present in PR diff:")
        for h in hits:
            print(f" - {h}")
        return 0

    print("[FAIL] Missing mandatory decision trace artifact for this Pull Request.")
    print("Add or modify at least one of the following in this PR:")
    for b in REQUIRED_BASENAMES:
        print(f" - {b}")
    print("\nTip (minimal): add a file named 'decision_trace.md' with:")
    print(" - Decision / Intent")
    print(" - Authority")
    print(" - Scope (files/modules touched)")
    print(" - Expected outcome")
    return 1


if __name__ == "__main__":
    sys.exit(main())
