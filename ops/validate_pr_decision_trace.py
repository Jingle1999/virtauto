# ops/validate_pr_decision_trace.py
import os
import subprocess
import sys
from pathlib import Path

MANDATORY_ANY_OF = [
    "decision_trace.md",
    "decision_trace.json",
]

# Optional accepted alt patterns (keeps governance strict, but unblocks common naming)
ALT_SUFFIXES = [
    ".decision_trace.md",
    ".decision-trace.md",
]

def git_changed_files() -> list[str]:
    # In PR validation we typically have merge-base available; if not, we fail safe.
    try:
        base = subprocess.check_output(["git", "merge-base", "HEAD", "origin/main"], text=True).strip()
    except Exception:
        # fallback: try main (in case origin/main not present)
        try:
            base = subprocess.check_output(["git", "merge-base", "HEAD", "main"], text=True).strip()
        except Exception:
            print("[FATAL] No merge-base found. Cannot reliably validate PR decision trace.")
            sys.exit(2)

    out = subprocess.check_output(["git", "diff", "--name-only", f"{base}...HEAD"], text=True)
    return [l.strip() for l in out.splitlines() if l.strip()]

def matches_alt(name: str) -> bool:
    return any(name.endswith(sfx) for sfx in ALT_SUFFIXES)

def main():
    changed = set(git_changed_files())

    ok = any(x in changed for x in MANDATORY_ANY_OF) or any(matches_alt(x) for x in changed)

    if not ok:
        print("[FATAL] Missing mandatory decision trace artifact for this Pull Request.")
        print("Add or modify at least one of the following in this PR:")
        for x in MANDATORY_ANY_OF:
            print(f" - {x}")
        print("\nAccepted alternatives:")
        for sfx in ALT_SUFFIXES:
            print(f" - *{sfx}")
        print("\nTip (minimal): add a file named 'decision_trace.md' with:")
        print(" - Decision / Intent")
        print(" - Authority")
        print(" - Scope (files/modules touched)")
        print(" - Expected outcome")
        sys.exit(1)

    print("[OK] PR decision trace present.")
    sys.exit(0)

if __name__ == "__main__":
    main()
