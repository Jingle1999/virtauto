
"""
Bridge: bindet den lokalen consistency_agent_mvp als Pre-/Post-Gate ein.
Bitte den Pfad unten (MVP_DIR) anpassen auf deinen lokalen Ordner.
"""

import json, subprocess, tempfile, pathlib, sys

# >>>>>>>> HIER DEIN LOKALER PFAD ZUM MVP-ORDNER <<<<<<<<
MVP_DIR = pathlib.Path(
    r"C:\Users\BraunA\Desktop\Privat\virtauto_repo\2_Development\Consistency_Agent\consistency_agent_mvp"
)

def _run_python(entry: str, payload: dict) -> dict:
    tmp_in  = pathlib.Path(tempfile.gettempdir()) / "va_consistency_in.json"
    tmp_out = pathlib.Path(tempfile.gettempdir()) / "va_consistency_out.json"
    tmp_in.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # ruft consistency_agent.py im MVP-Ordner auf
    subprocess.check_call([sys.executable, entry, str(tmp_in), str(tmp_out)], cwd=MVP_DIR)
    return json.loads(tmp_out.read_text(encoding="utf-8"))

def precheck(task: dict) -> dict:
    """Preflight für Tasks"""
    return _run_python("consistency_agent.py", {"stage": "pre", "task": task})

def postcheck(result: dict) -> dict:
    """Postflight für Results"""
    return _run_python("consistency_agent.py", {"stage": "post", "result": result})
