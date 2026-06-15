import asyncio
import json

from virtauto_agents.peak_guard_agent import PeakGuardAgent
from virtauto_agents.idle_loss_agent import IdleLossAgent
from virtauto_core.george_router import GeorgeRouter


async def main():
    with open("schemas/energy_event.json", "r") as f:
        event = json.load(f)

    agents = [
        PeakGuardAgent("peak_guard"),
        IdleLossAgent("idle_loss"),
    ]

    decisions = []

    for agent in agents:
        observed = await agent.observe(event)
        decision = await agent.evaluate(observed)
        await agent.emit(decision)
        await agent.log_trace(decision)
        decisions.append(decision)

    george = GeorgeRouter()
    final_decision = george.route(decisions)
    with open("george_decision.json", "w") as f:
        json.dump(final_decision, f, indent=2)
    
    print("Decision written to george_decision.json")


asyncio.run(main())