#!/usr/bin/env python3
"""
Autonomy Score Reproducibility Check (Phase 10 prep)

Derives the expected autonomy_score deterministically from ops/autonomy.json
and verifies ops/reports/system_status.json matches.

No external deps. Intended as a required CI check.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Tuple


AUTONOMY_MAP = {
    # canonical levels
    "DISABLED": 0.0,
    "MANUAL": 0.0,
    "SUPERVISED": 0.5,
    "AUTONOMOUS": 0.8,
    # tolerances / aliases
    "MIXED": 0.5,
    "UNKNOWN": 0.0,
}


def die(msg: str) -> None:
    print(f"AUTONOMY SCORE CHECK FAILED: {msg}")
    sys.exit(1)


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        die(f"{path.as_posix()} not found")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        die(f"Invalid JSON in {path.as_posix()}: {e}")
    return {}  # unreachable


def normalize_level(v: Any) -> Tuple[float, str]:
    """
    Accepts:
      - float/int in [0..1]
      - string level like 'SUPERVISED'
    Returns: (value_0_1, mode_string_upper)
    """
    if isinstance(v, (int, float)):
        val = float(v)
        if val < 0.0:
            val = 0.0
        if val > 1.0:
            val = 1.0
        # derive a stable label (best-effort)
        if val >= 0.75:
            return val, "AUTONOMOUS"
        if val >= 0.25:
            return val, "SUPERVISED"
        return val, "MANUAL"

    if isinstance(v, str):
        key = v.strip().upper()
        if key in AUTONOMY_MAP:
            val = AUTONOMY_MAP[key]
            # keep original canonical label if known
            canon = key if key in ("DISABLED", "MANUAL", "SUPERVISED", "AUTONOMOUS") else "SUPERVISED"
            if key in ("DISABLED", "MANUAL"):
                canon = "MANUAL"
            if key == "AUTONOMOUS":
                canon = "AUTONOMOUS"
            if key == "SUPERVISED":
                canon = "SUPERVISED"
            return val, canon
        # unknown string -> fail hard (keeps governance strict)
        die(f'Unknown system_autonomy_level "{v}" (expected one of {sorted(AUTONOMY_MAP.keys())} or numeric 0..1)')

    die(f"system_autonomy_level has unsupported type: {type(v).__name__}")
    return 0.0, "MANUAL"  # unreachable


def approx_equal(a: Any, b: Any, tol: float = 1e-6) -> bool:
    try:
        return abs(float(a) - float(b)) <= tol
    except Exception:
        return False


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]

    autonomy_path = repo_root / "ops/autonomy.json"
    ssot_path = repo_root / "ops/reports/system_status.json"

    autonomy = load_json(autonomy_path)
    ssot = load_json(ssot_path)

    raw = autonomy.get("system_autonomy_level", None)
    if raw is None:
        die("ops/autonomy.json missing key: system_autonomy_level")

    value, mode = normalize_level(raw)
    percent = round(value * 100.0, 1)

    ss = ssot.get("autonomy_score", {})
    if not isinstance(ss, dict):
        die("system_status.json autonomy_score must be an object")

    got_value = ss.get("value", None)
    got_percent = ss.get("percent", None)
    got_mode = ss.get("mode", None)

    if got_value is None or got_percent is None or got_mode is None:
        die("system_status.json autonomy_score must include: value, percent, mode")

    if not approx_equal(got_value, value, tol=1e-6):
        die(f"autonomy_score.value mismatch: expected {value} but got {got_value}")

    if not approx_equal(got_percent, percent, tol=1e-6):
        die(f"autonomy_score.percent mismatch: expected {percent} but got {got_percent}")

    if str(got_mode).strip().upper() != mode:
        die(f'autonomy_score.mode mismatch: expected "{mode}" but got "{got_mode}"')

    print(f"AUTONOMY SCORE CHECK OK: value={value} percent={percent} mode={mode}")
    sys.exit(0)


if __name__ == "__main__":
    main()