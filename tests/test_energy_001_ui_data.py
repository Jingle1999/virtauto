import json
from pathlib import Path
import pytest
from virtauto_mvp.energy_001 import evaluate_energy_001
ROOT=Path(__file__).resolve().parents[1]
@pytest.mark.parametrize('scenario',['s01','s02','s03'])
def test_published_scenario_matches_evaluator(scenario):
    fixture=json.loads((ROOT/f'tests/fixtures/energy_001/{scenario}.json').read_text())
    expected=evaluate_energy_001(fixture).to_dict()
    for folder in ['docs/energy_001/outputs','demo/decision-center/data/standby']:
        assert json.loads((ROOT/folder/f'{scenario}_result.json').read_text())==expected
