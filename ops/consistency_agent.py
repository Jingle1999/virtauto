# ops/consistency_agent.py
import json
import sys
from pathlib import Path

REGISTRY = Path("agents/registry.yaml")
DECISION_TRACE = Path("ops/reports/decision_trace.jsonl")
SYSTEM_STATUS = Path("ops/reports/system_status.json")

REQUIRED_REGISTRY_FIELDS = {"agent_id", "name", "autonomy_mode", "state"}
REQUIRED_TRACE_KEYS = {"trace_id", "schema_version", "generated_at", "inputs", "outputs", "because"}

def fail(msg: str):
    print(f"[FAIL] {msg}")
    sys.exit(2)

def warn(msg: str):
    print(f"[WARN] {msg}")

def ok(msg: str):
    print(f"[OK] {msg}")

def load_yaml_minimal(path: Path) -> dict:
    # ultra-minimal YAML loader to avoid dependencies:
    # expects simple YAML structures used in registry.yaml
    # If your repo already uses PyYAML elsewhere, feel free to replace with yaml.safe_load.
    try:
        import yaml  # type: ignore
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as e:
        fail(f"Cannot read YAML {path}: {e}")

def validate_registry():
    if not REGISTRY.exists():
        fail(f"Missing {REGISTRY}")

    data = load_yaml_minimal(REGISTRY)
    agents = data.get("agents", [])
    if not isinstance(agents, list) or not agents:
        fail(f"{REGISTRY} has no agents list")

    missing = []
    for a in agents:
        if not isinstance(a, dict):
            missing.append(("<?>", "not-a-dict"))
            continue
        aid = a.get("agent_id", "<?>")
        for k in REQUIRED_REGISTRY_FIELDS:
            if k not in a:
                missing.append((aid, k))

    if missing:
        for aid, k in missing:
            print(f"[FAIL] CNS-REG-007: Agent missing field: {k} ({REGISTRY}) agent_id={aid}")
        sys.exit(2)

    ok("agents/registry.yaml has required fields for all agents")

def tail_jsonl(path: Path, max_lines: int = 200) -> list[dict]:
    if not path.exists():
        warn(f"Missing {path} (no decision trace available yet)")
        return []

    lines = path.read_text(encoding="utf-8").splitlines()[-max_lines:]
    entries = []
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        try:
            entries.append(json.loads(ln))
        except Exception:
            warn(f"Invalid JSONL line in {path}: {ln[:80]}...")
    return entries

def validate_decision_trace():
    entries = tail_jsonl(DECISION_TRACE, 200)
    if not entries:
        warn("No decision trace entries found (yet).")
        return

    # validate last entry only (deterministic, low noise)
    last = entries[-1]
    missing = [k for k in REQUIRED_TRACE_KEYS if k not in last]
    if missing:
        for k in missing:
            print(f"[FAIL] CNS-TRACE-010: decision_trace entry missing key: {k} ({DECISION_TRACE})")
        sys.exit(2)

    outputs = last.get("outputs", [])
    if isinstance(outputs, list):
        # Require system_status.json output, but do NOT require gate_result.json anymore.
        if "ops/reports/system_status.json" not in outputs and str(SYSTEM_STATUS) not in outputs:
            warn("Latest decision_trace.outputs does not reference ops/reports/system_status.json (recommended).")
    else:
        warn("decision_trace.outputs is not a list (recommended list of produced artifacts).")

    ok("ops/reports/decision_trace.jsonl last entry has required keys")

def validate_system_status():
    if not SYSTEM_STATUS.exists():
        warn(f"Missing {SYSTEM_STATUS} (Status Agent may not have produced it yet)")
        return
    try:
        json.loads(SYSTEM_STATUS.read_text(encoding="utf-8"))
        ok("ops/reports/system_status.json is valid JSON")
    except Exception as e:
        fail(f"Invalid JSON in {SYSTEM_STATUS}: {e}")

def main():
    validate_registry()
    validate_decision_trace()
    validate_system_status()
    ok("Consistency Agent v1 finished.")
    sys.exit(0)

if __name__ == "__main__":
    main()
