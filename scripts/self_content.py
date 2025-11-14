#!/usr/bin/env python3
"""
Self Content Agent

Scans the ./content directory for markdown files and produces a simple
JSON report with basic quality signals. The goal is:
- give the CI workflow a stable script that always succeeds
- create a machine-readable report that later agents (or humans) can use
  to propose better content.

Typical usage from GitHub Actions:
    python scripts/self_content.py --root . --out ops/reports/content.json
"""

import argparse
import json
import os
import sys
from datetime import datetime

# Optional telemetry integration (fails gracefully if module not present)
try:
    from tools.ops.telemetry import emit as telemetry_emit  # type: ignore
except Exception:  # pragma: no cover
    def telemetry_emit(event: dict) -> None:
        # No-op fallback
        return


def find_markdown_files(root: str) -> list[tuple[str, str]]:
    """
    Find all markdown files under <root>/content and return a list of
    (relative_path, absolute_path).
    """
    content_root = os.path.join(root, "content")
    files: list[tuple[str, str]] = []

    if not os.path.isdir(content_root):
        return files

    for base, _dirs, filenames in os.walk(content_root):
        for name in filenames:
            if not name.lower().endswith((".md", ".markdown")):
                continue
            abs_path = os.path.join(base, name)
            rel_path = os.path.relpath(abs_path, root)
            files.append((rel_path, abs_path))

    return sorted(files)


def analyse_markdown(text: str) -> dict:
    """
    Very simple heuristic content checks.

    This is intentionally lightweight – it just gives the Self-Content
    Agent something to reason about and keeps CI stable.
    """
    lines = text.splitlines()
    word_count = len(text.split())
    has_h1 = any(l.strip().startswith("# ") for l in lines[:10])
    has_todo = any("TODO" in l or "todo" in l for l in lines)
    very_short = word_count < 50
    very_long = word_count > 2500

    issues: list[str] = []
    if not has_h1:
        issues.append("missing_h1_title")
    if has_todo:
        issues.append("contains_todo_markers")
    if very_short:
        issues.append("very_short_content")
    if very_long:
        issues.append("very_long_content")

    return {
        "word_count": word_count,
        "has_h1": has_h1,
        "has_todo": has_todo,
        "very_short": very_short,
        "very_long": very_long,
        "issues": issues,
    }


def scan_content(root: str) -> dict:
    """
    Scan all markdown files and return a report structure.
    """
    files = find_markdown_files(root)
    results: list[dict] = []
    total_issues = 0

    for rel_path, abs_path in files:
        try:
            with open(abs_path, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception as exc:  # pragma: no cover
            results.append(
                {
                    "path": rel_path,
                    "error": f"failed_to_read: {exc!r}",
                    "analysis": None,
                }
            )
            total_issues += 1
            continue

        analysis = analyse_markdown(text)
        total_issues += len(analysis["issues"])

        results.append(
            {
                "path": rel_path,
                "analysis": analysis,
            }
        )

    report = {
        "agent": "self_content",
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "root": root,
        "file_count": len(files),
        "total_issues": total_issues,
        "files": results,
    }

    return report


def write_report(report: dict, out_path: str) -> None:
    """
    Write JSON report to the given path, creating directories as needed.
    """
    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Self Content Agent")
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root (default: current directory)",
    )
    parser.add_argument(
        "--out",
        default="ops/reports/content.json",
        help="Output JSON report path (default: ops/reports/content.json)",
    )
    args = parser.parse_args(argv)

    root = os.path.abspath(args.root)
    report = scan_content(root)
    write_report(report, args.out)

    # optional telemetry event
    telemetry_emit(
        {
            "agent": "self_content",
            "event": "content_scan_completed",
            "file_count": report["file_count"],
            "total_issues": report["total_issues"],
            "out": args.out,
        }
    )

    print(f"[self_content] report saved to {args.out}")
    print(
        f"[self_content] scanned {report['file_count']} files, "
        f"found {report['total_issues']} issues"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

