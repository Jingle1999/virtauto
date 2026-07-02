import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def stable_hash(data):
    payload = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


class SnapshotBuilder:
    def build(self, *, runtime_state, contract_traces, final_decision):
        snapshot = {
            "snapshot_id": "SNAP-" + stable_hash(
                {
                    "runtime_state": runtime_state,
                    "contract_traces": contract_traces,
                    "final_decision": final_decision,
                }
            ),
            "created_at": utc_now(),
            "snapshot_type": "decision_environment",
            "runtime_state": runtime_state,
            "contract_traces": contract_traces,
            "final_decision": final_decision,
            "reproducibility": {
                "principle": "Same decision only if the decision environment is the same",
                "environment_hash": stable_hash(
                    {
                        "runtime_state": runtime_state,
                        "contract_traces": contract_traces,
                        "final_decision": final_decision,
                    }
                ),
            },
        }

        return snapshot

    def write(self, snapshot, path="ops/decisions/snapshots/latest_snapshot.json"):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2, ensure_ascii=False)

        return str(path)
