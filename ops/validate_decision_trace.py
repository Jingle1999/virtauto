#!/usr/bin/env python3
"""
Decision Trace Validator (Explainability v1)

Ziel:
- PR darf nicht ohne Decision Trace "durchrutschen"
- Aber: Legacy/Bundle-Formate sollen NICHT alles blockieren

Akzeptierte Formate (jsonl):
A) Record-Format (events/records)
   Required (after normalization): ts, trace_version, decision_id, actor, phase, result

B) Bundle-Format (generated trace bundle)
   Required: schema_version OR trace_version, trace_id, (generated_at OR ts), inputs, outputs
   Optional but recommended: because, evidence

Exit Codes:
- 0 = OK
- 1 = FAIL (bindender Blocker)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# Prefer canonical location under ops/reports (matches your repo screenshots)
CANDIDATE_PATHS = [
    Path("ops/reports/decision_trace.jsonl"),
    Path("ops/decision_trace.jsonl"),
    Path("ops/reports/decision_trace.json"),
    Path("ops/decision_trace.json"),
]

# Allowed phases for record-format (keep minimal + tolerant)
ALLOWED_PHASES = {
    "route",
    "guardian_precheck",
    "authority_enforcement",
    "execute",
    "guardian_postcheck",
    "finalize",
    "blocked",
    # tolerate some legacy/common synonyms
    "guardrail",
    "precheck",
    "postcheck",
}

def fail(msg: str, code: int = 1) -> None:
    print(f"VALIDATION FAILED: {msg}")
    sys.exit(code)

def warn(msg: str) -> None:
    print(f"VALIDATION WARN: {msg}")

def load_json_lines(path: Path) -> List[Dict[str, Any]]:
    txt = path.read_text(encoding="utf-8").strip()
    if not txt:
        return []
    # jsonl
    if path.suffix == ".jsonl":
        out: List[Dict[str, Any]] = []
        for i, line in enumerate(txt.splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception as e:
                fail(f"{path}: invalid JSON on line {i}: {e}")
            if not isinstance(obj, dict):
                fail(f"{path}: line {i} must be a JSON object")
            out.append(obj)
        return out

    # single json
    try:
        obj = json.loads(txt)
    except Exception as e:
        fail(f"{path}: invalid JSON: {e}")

    if isinstance(obj, dict):
        return [obj]
    if isinstance(obj, list):
        out = []
        for i, it in enumerate(obj):
            if not isinstance(it, dict):
                fail(f"{path}: list item {i} must be an object")
            out.append(it)
        return out
    fail(f"{path}: JSON must be an object or list of objects")
    return []


def normalize_record(rec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize various legacy keys into canonical record keys:
    - ts: allow ts/timestamp/generated_at/time
    - decision_id: allow decision_id/id/trace_id (fallback)
    - actor: allow actor/agent
    - phase: allow phase/stage/step
    - result: allow result/status/outcome
    - trace_version: allow trace_version/schema_version/version
    """
    r = dict(rec)

    # timestamp
    if "ts" not in r:
        for k in ("timestamp", "time", "generated_at"):
            if k in r:
                r["ts"] = r[k]
                break

    # decision_id
    if "decision_id" not in r:
        for k in ("decisionId", "id"):
            if k in r:
                r["decision_id"] = r[k]
                break
    if "decision_id" not in r and "trace_id" in r:
        # fallback: some traces only have trace_id
        r["decision_id"] = r["trace_id"]

    # actor
    if "actor" not in r:
        for k in ("agent", "who"):
            if k in r:
                r["actor"] = r[k]
                break

    # phase
    if "phase" not in r:
        for k in ("stage", "step"):
            if k in r:
                r["phase"] = r[k]
                break

    # result
    if "result" not in r:
        for k in ("status", "outcome"):
            if k in r:
                r["result"] = r[k]
                break

    # trace_version
    if "trace_version" not in r:
        for k in ("schema_version", "version"):
            if k in r:
                # keep as string
                r["trace_version"] = str(r[k])
                break

    return r


def is_bundle_format(obj: Dict[str, Any]) -> bool:
    # Heuristic: bundle has inputs/outputs arrays + trace_id, and often "because"/"evidence"
    if "trace_id" in obj and "inputs" in obj and "outputs" in obj:
        return True
    # Another heuristic: schema_version + generated_at + because (as list)
    if "schema_version" in obj and "generated_at" in obj and "because" in obj:
        return True
    return False


def validate_bundle(obj: Dict[str, Any], idx: int) -> None:
    missing = []
    if "trace_id" not in obj:
        missing.append("trace_id")
    if "inputs" not in obj:
        missing.append("inputs")
    if "outputs" not in obj:
        missing.append("outputs")

    # timestamp field can be generated_at or ts
    if "generated_at" not in obj and "ts" not in obj:
        missing.append("generated_at|ts")

    if missing:
        fail(f"Invalid decision trace bundle (idx={idx}): missing required keys {missing}")

    if not isinstance(obj["inputs"], list) or not obj["inputs"]:
        fail(f"Invalid decision trace bundle (idx={idx}): inputs must be a non-empty list")
    if not isinstance(obj["outputs"], list) or not obj["outputs"]:
        fail(f"Invalid decision trace bundle (idx={idx}): outputs must be a non-empty list")

    # recommended sections
    if "because" not in obj:
        warn(f"Bundle trace (idx={idx}) has no 'because' field (recommended)")
    if "evidence" not in obj:
        warn(f"Bundle trace (idx={idx}) has no 'evidence' field (recommended)")


def validate_record(obj: Dict[str, Any], idx: int) -> None:
    r = normalize_record(obj)

    required = ["ts", "trace_version", "decision_id", "actor", "phase", "result"]
    missing = [k for k in required if k not in r or r[k] in (None, "", [])]
    if missing:
        fail(f"Invalid decision trace record (idx={idx}): missing required keys {missing}")

    # basic type checks (tolerant, but safe)
    if not isinstance(r["ts"], str):
        fail(f"Invalid decision trace record (idx={idx}): ts must be string")
    if not isinstance(r["decision_id"], str):
        fail(f"Invalid decision trace record (idx={idx}): decision_id must be string")
    if not isinstance(r["actor"], str):
        fail(f"Invalid decision trace record (idx={idx}): actor must be string")
    if not isinstance(r["phase"], str):
        fail(f"Invalid decision trace record (idx={idx}): phase must be string")
    if not isinstance(r["result"], (str, bool, int, float, dict, list)):
        fail(f"Invalid decision trace record (idx={idx}): result has unsupported type")

    if r["phase"] not in ALLOWED_PHASES:
        warn(f"Record trace (idx={idx}) has non-standard phase='{r['phase']}' (allowed but review recommended)")


def main() -> None:
    path = next((p for p in CANDIDATE_PATHS if p.exists()), None)
    if not path:
        fail(
            "No decision trace file found. Expected one of: "
            + ", ".join(str(p) for p in CANDIDATE_PATHS)
        )

    items = load_json_lines(path)
    if not items:
        fail(f"{path} is empty (must contain at least one trace record/bundle)")

    # Validate last N entries to keep it fast but meaningful
    N = 50
    tail = items[-N:] if len(items) > N else items

    for i, obj in enumerate(tail, start=max(0, len(items) - len(tail))):
        if is_bundle_format(obj):
            validate_bundle(obj, i)
        else:
            validate_record(obj, i)

    print(f"VALIDATION OK: decision trace present and valid ({path}, checked {len(tail)} entries).")
    sys.exit(0)


if __name__ == "__main__":
    main()
