#!/usr/bin/env python3
"""
Validate that every Pull Request carries an explicit decision trace artifact.

Phase 2 goal: "No decision without trace" (Explainability v1).

Hard rule:
- For Pull Requests, the PR MUST add or modify exactly one of:
    * decision_trace.md
    * decision_trace.json
- The file MUST live at repository root.

This check is intentionally mechanical (not "AI").
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import List, Tuple


REQUIRED_ROOT_FILES = ("decision_trace.md", "decision_trace.json")


def run(cmd: List[str]) -> Tuple[int, str]:
    p = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
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
        # Enforce decision traces ONLY on PR events
        print(f"[OK] validate_pr_decision_trace: not a pull_request event ({event_name}).")
        return 0

    event = load_event()
    pr = event.get("pull_request") or {}

    base_sha = (pr.get("base") or {}).get("sha")
    head_sha = (pr.get("head") or {}).get("sha")

    if not base_sha or not head_sha:
        print("[FAIL] Could not read base/head SHA from GitHub event payload.")
        return 1

    # Use merge-base diff to correctly capture PR changes
    rc, out = run(["git", "diff", "--name-only", f"{base_sha}...{head_sha}"])
    if rc != 0:
        print("[FAIL] git diff failed:")
        print(out)
        return 1

    changed = [line.strip() for line in out.splitlines() if line.strip()]

    hits = [p for p in changed if p in REQUIRED_ROOT_FILES]

    if hits:
        print("[OK] Root-level decision trace present in PR diff:")
        for h in hits:
            print(f" - {h}")
        return 0

    print("[FAIL] Missing mandatory decision trace artifact for this Pull Request.")
    print("You must add or modify exactly one of the following at repository root:")
    for f in REQUIRED_ROOT_FILES:
        print(f" - {f}")

    print("\nMinimal required content:")
    print(" - Decision / Intent")
    print(" - Authority")
    print(" - Scope")
    print(" - Expected outcome")

    return 1


if __name__ == "__main__":
    sys.exit(main())
