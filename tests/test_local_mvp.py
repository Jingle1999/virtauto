from pathlib import Path
from virtauto_mvp.pipeline import run_pipeline


def test_local_mvp_pipeline(tmp_path: Path):
    result = run_pipeline(
        "local_mvp/input/biw_door_line_anomalies_30d.csv",
        "local_mvp/demo_config.yaml",
        tmp_path,
    )
    assert result["context"].data_quality.decision_readiness == "READY"
    assert result["context"].trigger["active"] is True
    assert result["decision"].options
    assert result["governance"].execution_mode == "PROPOSE_ONLY"
    assert Path(result["paths"]["json"]).exists()
    assert Path(result["paths"]["html"]).exists()
