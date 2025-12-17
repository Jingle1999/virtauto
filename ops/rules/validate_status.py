import json
from jsonschema import validate

schema = json.load(open("ops/rules/agent_status.schema.json"))
status = json.load(open("ops/reports/system_status.json"))

for agent, data in status.get("agents", {}).items():
    validate(instance=data, schema=schema)
