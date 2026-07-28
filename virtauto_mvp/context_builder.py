from __future__ import annotations

import csv
import hashlib
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import DataQuality, IndustrialContext, PeakEvent

REQUIRED_COLUMNS = {
    "timestamp",
    "production_state",
    "power_kw",
    "takt_target_s",
    "takt_actual_s",
    "parts_produced_min",
}


def _as_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_bool(value: str | None) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


class ContextBuilder:
    version = "0.1.0"

    def build(self, csv_path: str | Path, config: dict[str, Any]) -> IndustrialContext:
        path = Path(csv_path)
        rows = self._load_rows(path)
        quality = self._validate(rows)
        timestamps = [datetime.fromisoformat(r["timestamp"]) for r in rows]
        powers = [_as_float(r.get("power_kw")) for r in rows]
        valid_powers = [v for v in powers if v is not None]
        threshold = float(config["analysis"]["peak_threshold_kw"])
        peaks = self._detect_peaks(rows, threshold)
        run_rows = [r for r in rows if r.get("production_state") == "RUN"]
        run_powers = [_as_float(r.get("power_kw")) for r in run_rows]
        run_powers = [v for v in run_powers if v is not None]
        takt_deviation = self._takt_deviation(run_rows)
        production_state_counts: dict[str, int] = {}
        for row in rows:
            state = row.get("production_state", "UNKNOWN")
            production_state_counts[state] = production_state_counts.get(state, 0) + 1

        anomaly_counts: dict[str, int] = {}
        for row in rows:
            if _as_bool(row.get("anomaly_active")):
                anomaly = row.get("anomaly_type", "unknown")
                anomaly_counts[anomaly] = anomaly_counts.get(anomaly, 0) + 1

        dataset_id = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
        now = datetime.now(timezone.utc).isoformat()
        strongest_peak = max(peaks, key=lambda p: p.maximum_power_kw, default=None)
        trigger_type = "PEAK_ACTIVE" if peaks else "NO_TRIGGER"
        readiness = quality.decision_readiness
        confidence = "HIGH" if readiness == "READY" else "MEDIUM" if readiness == "LIMITED" else "INSUFFICIENT"
        uncertainties = [
            "Energy price is supplied by configuration, not by the CSV.",
            "Quality, buffer and order state are supplied by demo configuration.",
            "Expected load reductions are engineering assumptions for the demo.",
        ]
        summary = (
            f"{len(rows):,} one-minute records were analysed. "
            f"{len(peaks)} peak event(s) above {threshold:.1f} kW were detected."
        )
        if strongest_peak:
            summary += f" The maximum measured power was {strongest_peak.maximum_power_kw:.1f} kW."

        return IndustrialContext(
            context_id=f"CTX-{dataset_id}",
            dataset_id=dataset_id,
            site_id=config["site_id"],
            area_id=config["area_id"],
            line_id=config["line_id"],
            generated_at=now,
            analysis_window={"start": timestamps[0].isoformat(), "end": timestamps[-1].isoformat()},
            data_quality=quality,
            trigger={
                "type": trigger_type,
                "active": bool(peaks),
                "severity": "HIGH" if strongest_peak and strongest_peak.excess_kw >= 25 else "MEDIUM" if peaks else "NONE",
                "peak_events": [p.model_dump() for p in peaks],
            },
            energy={
                "average_power_kw": round(statistics.fmean(valid_powers), 2),
                "maximum_power_kw": round(max(valid_powers), 2),
                "median_run_power_kw": round(statistics.median(run_powers), 2) if run_powers else None,
                "peak_threshold_kw": threshold,
                "peak_event_count": len(peaks),
                "assumed_price_eur_per_kwh": config["analysis"].get("assumed_price_eur_per_kwh"),
            },
            production={
                "state_counts": production_state_counts,
                "parts_produced": int(sum(int(r.get("parts_produced_min") or 0) for r in rows)),
                "takt_deviation_pct": takt_deviation,
                "status": "DEGRADED" if takt_deviation and takt_deviation > 5 else "STABLE",
                "anomaly_counts": anomaly_counts,
            },
            quality=config["quality"],
            material_flow=config["material_flow"],
            order=config["order"],
            governance=config["governance"],
            uncertainties=uncertainties,
            context_confidence=confidence,
            context_summary=summary,
        )

    def _load_rows(self, path: Path) -> list[dict[str, str]]:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        if not rows:
            raise ValueError("CSV contains no data rows.")
        return rows

    def _validate(self, rows: list[dict[str, str]]) -> DataQuality:
        columns = set(rows[0].keys())
        missing_columns = sorted(REQUIRED_COLUMNS - columns)
        issues: list[str] = []
        if missing_columns:
            issues.append("Missing required columns: " + ", ".join(missing_columns))
        missing_values = sum(1 for row in rows for col in REQUIRED_COLUMNS if col not in row or row[col] in (None, ""))
        timestamps = [row.get("timestamp") for row in rows]
        duplicates = len(timestamps) - len(set(timestamps))
        interval = None
        try:
            parsed = [datetime.fromisoformat(t) for t in timestamps if t]
            deltas = [(b - a).total_seconds() / 60 for a, b in zip(parsed, parsed[1:])]
            interval = statistics.median(deltas) if deltas else None
            if deltas and any(abs(d - interval) > 0.001 for d in deltas):
                issues.append("Timestamp intervals are not fully regular.")
        except ValueError:
            issues.append("One or more timestamps are invalid.")
        if duplicates:
            issues.append(f"Duplicate timestamps: {duplicates}")
        readiness = "INSUFFICIENT" if missing_columns else "LIMITED" if issues else "READY"
        return DataQuality(
            rows=len(rows),
            columns=len(columns),
            missing_required_values=missing_values,
            duplicate_timestamps=duplicates,
            interval_minutes=interval,
            decision_readiness=readiness,
            issues=issues,
        )

    def _detect_peaks(self, rows: list[dict[str, str]], threshold: float) -> list[PeakEvent]:
        events: list[PeakEvent] = []
        current: list[dict[str, str]] = []
        for row in rows:
            power = _as_float(row.get("power_kw"))
            if power is not None and power > threshold:
                current.append(row)
            elif current:
                events.append(self._to_peak(current, threshold))
                current = []
        if current:
            events.append(self._to_peak(current, threshold))
        return events

    def _to_peak(self, rows: list[dict[str, str]], threshold: float) -> PeakEvent:
        powers = [float(r["power_kw"]) for r in rows]
        maximum = max(powers)
        return PeakEvent(
            start=rows[0]["timestamp"],
            end=rows[-1]["timestamp"],
            duration_minutes=len(rows),
            maximum_power_kw=round(maximum, 2),
            threshold_kw=threshold,
            excess_kw=round(maximum - threshold, 2),
        )

    def _takt_deviation(self, rows: list[dict[str, str]]) -> float | None:
        deviations = []
        for row in rows:
            target = _as_float(row.get("takt_target_s"))
            actual = _as_float(row.get("takt_actual_s"))
            if target and actual:
                deviations.append((actual - target) / target * 100)
        return round(statistics.fmean(deviations), 2) if deviations else None
