# virtauto Local Decision Intelligence MVP

## Start als CLI

```bash
python -m virtauto_mvp.cli \
  --csv local_mvp/input/biw_door_line_anomalies_30d.csv \
  --config local_mvp/demo_config.yaml \
  --output local_mvp/output
```

## Start als lokale Webanwendung

```bash
uvicorn virtauto_mvp.api:app --reload
```

Danach `http://127.0.0.1:8000` öffnen und eine CSV hochladen.

## Aktueller Umfang

- CSV-Validierung
- Context Builder
- Peak-Erkennung
- Baseline und flexible Lastoption
- deterministisches Scoring
- Governance Gate im Modus `PROPOSE_ONLY`
- HTML- und JSON-Decision-Report

Die statischen Produktions-, Qualitäts-, Puffer-, Auftrags- und Governance-Informationen liegen in `demo_config.yaml`.
