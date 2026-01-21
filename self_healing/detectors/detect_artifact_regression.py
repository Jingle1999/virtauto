from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, List


MANIFEST_PATH = Path("self_healing/templates/artifact_manifest.json")


def load_manifest() -> List[str]:
    if MANIFEST_PATH.exists():
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        items = data.get("mandatory_artifacts", [])
        return [str(x) for x in items]
    # Fallback (hard-coded)
    return [
        "ops/reports/decision_trace.jsonl",
        "ops/decisions/gate_result.json",
        "ops/reports/system_status.json",
        "ops/reports/latest.json",
    ]


def detect() -> Dict[str, Any]:
    required = load_manifest()
    missing = [p for p in required if not Path(p).is_file()]

    regression = len(missing) > 0
    return {
        "regression": regression,
        "type": "MISSING_ARTIFACT" if regression else "NONE",
        "missing": missing,
        "severity": "blocking" if regression else "none",
    }


if __name__ == "__main__":
    print(json.dumps(detect(), indent=2, sort_keys=True))
