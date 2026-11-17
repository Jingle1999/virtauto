import json
from pathlib import Path
import copy
import pytest
from virtauto_mvp.energy_001 import evaluate_energy_001

FIXTURES = Path(__file__).parent / "fixtures" / "energy_001"
def fixture(name): return json.loads((FIXTURES / (name.lower()+".json")).read_text())

def test_s01_conditional_winner_not_realtime_authorization():
    d=evaluate_energy_001(fixture("S01")).to_dict()
    assert [x["energy_kwh"] for x in d["alternatives"]] == [18.0,9.15,3.8]
    assert d["governance"]["conditional_preferred_state"] == "DEEP_ECO"
    assert d["selected_action"] == "HOLD"
    assert d["expected_outcome"]["conditional_energy_saving_kwh"] == 14.2
    assert d["expected_outcome"]["conditional_avoided_energy_cost_eur"] == 2.84
    assert not d["governance"]["execution_permitted"]

def test_s02_restart_blocks_changes():
    d=evaluate_energy_001(fixture("S02")).to_dict()
    assert [x["scenario_feasibility"] for x in d["alternatives"]] == ["ALLOW","BLOCK","BLOCK"]
    assert [round(x["energy_kwh"],4) for x in d["alternatives"]] == [1,0.65,0.9667]
    assert d["governance"]["conditional_preferred_state"] == "READY"
    assert d["selected_action"] == "BLOCK"

def test_s03_unknown_holds_changes():
    d=evaluate_energy_001(fixture("S03")).to_dict()
    assert [x["scenario_feasibility"] for x in d["alternatives"]] == ["ALLOW","HOLD","HOLD"]
    assert d["selected_action"] == "HOLD"
    assert d["governance"]["realtime_recommended_state"] == "READY"

def test_trigger_blocks():
    x=fixture("S01");x["trigger"]["stop_confirmed"]["value"]=False
    d=evaluate_energy_001(x)
    assert all(a["scenario_feasibility"]=="BLOCK" for a in d.alternatives[1:])

def test_known_prohibition_overrides_unknown():
    x=fixture("S03");x["decision_context"]["state_approval"]["ECO"]["value"]=False
    d=evaluate_energy_001(x)
    assert d.alternatives[1]["scenario_feasibility"]=="BLOCK"

@pytest.mark.parametrize("mutation", ["negative", "duplicate", "unknown", "wrong_status", "missing"])
def test_invalid_inputs_rejected(mutation):
    x=fixture("S01")
    if mutation=="negative":x["alternatives"][0]["power_kw"]=-1
    if mutation=="duplicate":x["alternatives"][1]["state"]="READY"
    if mutation=="unknown":x["decision_context"]["thermal_permission"]["ECO"]={"value":True,"evidence":"UNKNOWN"}
    if mutation=="wrong_status":x["decision_context"]["thermal_permission"]["ECO"]["evidence"]="GUESS"
    if mutation=="missing":del x["decision_context"]["guaranteed_restart_notice_min"]
    with pytest.raises((ValueError,KeyError)):evaluate_energy_001(x)

def test_determinism_and_no_realised_claims():
    x=fixture("S01")
    a=evaluate_energy_001(x).to_dict();b=evaluate_energy_001(copy.deepcopy(x)).to_dict()
    assert a==b
    assert a["actual_outcome"]=={}
    assert a["expected_outcome"]["net_benefit_eur"] is None
    assert a["expected_outcome"]["realised_savings_claim"] is False

def test_p0_scenario_allow_is_not_operational_authorization():
    d=evaluate_energy_001(fixture("S01")).to_dict()
    deep=d["alternatives"][2]
    assert deep["scenario_feasibility"]=="ALLOW"
    assert deep["scenario_feasibility_scope"]=="CONDITIONAL_SYNTHETIC_ONLY"
    assert deep["realtime_status"]=="HOLD"
    assert d["governance"]["execution_permitted"] is False

def test_p0_restart_constraint_is_explained_with_numbers():
    d=evaluate_energy_001(fixture("S02")).to_dict()
    assert "8 min" in " ".join(d["alternatives"][2]["reasons"])
    assert "1 min" in " ".join(d["alternatives"][2]["reasons"])
    assert "2 min" in " ".join(d["alternatives"][1]["reasons"])

def test_p0_cost_is_energy_only_not_net_value():
    d=evaluate_energy_001(fixture("S01")).to_dict()
    outcome=d["expected_outcome"]
    assert outcome["conditional_avoided_energy_cost_eur"]==2.84
    assert outcome["cost_semantics"]=="CONDITIONAL_AVOIDED_ENERGY_COST_ONLY"
    assert outcome["production_impact_cost_eur"] is None
    assert outcome["net_benefit_eur"] is None

def test_p0_ready_unknown_must_not_be_recommended():
    x=fixture("S03")
    x["decision_context"]["thermal_permission"]["READY"]={"value":None,"evidence":"UNKNOWN"}
    d=evaluate_energy_001(x).to_dict()
    assert d["alternatives"][0]["realtime_status"]=="HOLD"
    assert d["governance"]["realtime_recommended_state"] is None

def test_p0_ready_prohibited_must_not_be_recommended():
    x=fixture("S01")
    x["decision_context"]["state_approval"]["READY"]["value"]=False
    d=evaluate_energy_001(x).to_dict()
    assert d["alternatives"][0]["realtime_status"]=="BLOCK"
    assert d["governance"]["realtime_recommended_state"] is None
