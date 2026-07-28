import csv
from pathlib import Path

import pytest

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


def test_missing_required_value_marks_data_quality_limited(tmp_path: Path):
    source_csv = Path("local_mvp/input/biw_door_line_anomalies_30d.csv")
    broken_csv = tmp_path / "broken_input.csv"

    with source_csv.open("r", encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
        fieldnames = list(rows[0].keys())

    rows[0]["power_kw"] = ""

    with broken_csv.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    result = run_pipeline(
        broken_csv,
        "local_mvp/demo_config.yaml",
        tmp_path / "output",
    )

    quality = result["context"].data_quality

    assert quality.missing_required_values == 1
    assert quality.decision_readiness == "LIMITED"
    assert any(
        "Missing required values" in issue
        for issue in quality.issues
    )
def test_invalid_timestamp_is_rejected_with_clear_error(tmp_path: Path):
    source_csv = Path("local_mvp/input/biw_door_line_anomalies_30d.csv")
    broken_csv = tmp_path / "invalid_timestamp.csv"

    with source_csv.open("r", encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
        fieldnames = list(rows[0].keys())

    rows[0]["timestamp"] = "not-a-timestamp"

    with broken_csv.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    with pytest.raises(
        ValueError,
        match="CSV contains one or more invalid timestamps",
    ):
        run_pipeline(
            broken_csv,
            "local_mvp/demo_config.yaml",
            tmp_path / "output",
        )