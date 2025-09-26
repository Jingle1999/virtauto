#!/usr/bin/env python3
"""
UX Unify Agent
- Scans all *.html files
- Injects assets/styles_unify.css if missing
- Normalizes <img> tags and wraps them in <figure class="media"> with optional <figcaption>
- Writes a log to logs/ux-unify-YYYYMMDD-HHMMSS.log
"""
import re
import os
import sys
import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = REPO_ROOT / "logs"
TOOLS = REPO_ROOT / "tools" / "site_unifier.py"

def run_tool(apply: bool) -> int:
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    LOG_DIR.mkdir(exist_ok=True, parents=True)
    log_file = LOG_DIR / f"ux-unify-{ts}.log"
    cmd = f'"{sys.executable}" "{TOOLS}" --root "{REPO_ROOT}" {"--apply" if apply else "--dry-run"} > "{log_file}" 2>&1'
    print(f"[UX-AGENT] running: {cmd}")
    rc = os.system(cmd)
    if rc == 0:
        print(f"[UX-AGENT] done. See log: {log_file}")
    else:
        print(f"[UX-AGENT] finished with rc={rc}. Check log: {log_file}")
    return rc

def main():
    apply = "--apply" in sys.argv
    if "--dry-run" in sys.argv and apply:
        print("Choose either --dry-run or --apply, not both.", file=sys.stderr)
        sys.exit(2)
    if "--dry-run" not in sys.argv and not apply:
        # default to dry-run for safety
        print("[UX-AGENT] No flag supplied → defaulting to --dry-run")
        return run_tool(False)
    return run_tool(apply)

if __name__ == "__main__":
    sys.exit(main())
