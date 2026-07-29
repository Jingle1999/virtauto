import csv
from pathlib import Path

import pytest
import yaml

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

def test_unsorted_rows_are_processed_chronologically(tmp_path: Path):
    source_csv = Path("local_mvp/input/biw_door_line_anomalies_30d.csv")
    unsorted_csv = tmp_path / "unsorted_input.csv"

    with source_csv.open("r", encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
        fieldnames = list(rows[0].keys())

    expected_start = rows[0]["timestamp"]
    expected_end = rows[-1]["timestamp"]

    # Zwei weit auseinanderliegende Datensätze vertauschen.
    rows[0], rows[-1] = rows[-1], rows[0]

    with unsorted_csv.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    result = run_pipeline(
        unsorted_csv,
        "local_mvp/demo_config.yaml",
        tmp_path / "output",
    )

    context = result["context"]

    assert context.analysis_window["start"] == expected_start
    assert context.analysis_window["end"] == expected_end

def test_peak_shorter_than_minimum_duration_is_ignored(tmp_path: Path):
    source_csv = Path("local_mvp/input/biw_door_line_anomalies_30d.csv")
    short_peak_csv = tmp_path / "short_peak.csv"
    config_path = tmp_path / "config.yaml"

    with source_csv.open("r", encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
        fieldnames = list(rows[0].keys())

    # Alle Werte zunächst sicher unter die Peak-Grenze setzen.
    for row in rows:
        row["power_kw"] = "100"

    # Genau eine Minute oberhalb der Schwelle.
    rows[100]["power_kw"] = "220"

    with short_peak_csv.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    with Path("local_mvp/demo_config.yaml").open(
        "r",
        encoding="utf-8",
    ) as source:
        config = yaml.safe_load(source)

    config["analysis"]["minimum_peak_duration_minutes"] = 3

    with config_path.open("w", encoding="utf-8") as target:
        yaml.safe_dump(
            config,
            target,
            sort_keys=False,
            allow_unicode=True,
        )

    result = run_pipeline(
        short_peak_csv,
        config_path,
        tmp_path / "output",
    )

    assert result["context"].trigger["active"] is False
    assert result["context"].energy["peak_event_count"] == 0