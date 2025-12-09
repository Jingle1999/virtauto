from ops.george_orchestrator_v2 import load_autonomy_config, get_agent_profile

def test_load_autonomy_config():
    cfg = load_autonomy_config()
    assert "agents" in cfg
    assert isinstance(cfg["agents"], dict)

def test_agent_profile_guardian():
    profile = get_agent_profile("guardian")
    assert profile["status"] in ["active", "planned"]
