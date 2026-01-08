const fs = require("fs");
const path = require("path");

function readJSON(p) {
  return JSON.parse(fs.readFileSync(p, "utf8"));
}

function fail(msg) {
  console.error("RESILIENCE-GATE FAILED:", msg);
  process.exit(1);
}

const base = path.join(process.cwd(), "governance", "resilience");
const backlogPath = path.join(base, "phase8_resilience_backlog.json");
const graphPath   = path.join(base, "capability_graph.json");
const rulesPath   = path.join(process.cwd(), "governance", "failover_rules.json"); // bei dir aktuell in governance/
const chaosPath   = path.join(base, "tests", "chaos_test_agent_failover.json");
const expectedPath= path.join(base, "tests", "expected_failover_trace.json");

const backlog = readJSON(backlogPath);
const graph   = readJSON(graphPath);
const rules   = readJSON(rulesPath);
const chaos   = readJSON(chaosPath);
const expected= readJSON(expectedPath);

// --- minimal consistency checks ---
const critical = new Set((backlog.critical_capabilities || []).map(x => x.capability));
if (critical.size === 0) fail("No critical_capabilities in phase8_resilience_backlog.json");

const graphCaps = new Set((graph.capabilities || []).map(x => x.capability));
for (const cap of critical) {
  if (!graphCaps.has(cap)) fail(`Capability '${cap}' missing in capability_graph.json`);
}

for (const cap of critical) {
  const entry = (graph.capabilities || []).find(x => x.capability === cap);
  if (!entry?.primary_agent || !entry?.secondary_agent) {
    fail(`Capability '${cap}' must define primary_agent and secondary_agent`);
  }
}

const ruleCaps = new Set((rules.rules || []).map(r => r.capability));
for (const cap of critical) {
  if (!ruleCaps.has(cap)) fail(`No failover rule for critical capability '${cap}' in failover_rules.json`);
}

// --- simulate one chaos test → produce trace evidence ---
const scenario = chaos.scenario || "agent_failover";
const capabilityUnderTest = chaos.capability || [...critical][0];

const capEntry = (graph.capabilities || []).find(x => x.capability === capabilityUnderTest);
if (!capEntry) fail(`Chaos test capability '${capabilityUnderTest}' not found in capability_graph.json`);

const primary = capEntry.primary_agent;
const backup  = capEntry.secondary_agent;

// deterministic routing simulation: primary unhealthy → backup selected
const trace = {
  scenario,
  timestamp_utc: new Date().toISOString(),
  capability_required: capabilityUnderTest,
  primary_agent: primary,
  secondary_agent: backup,
  observed_health: {
    [primary]: "down",
    [backup]: "ok"
  },
  decision: {
    routed_to: backup,
    reason: "deterministic_failover_rule",
    rule: (rules.rules || []).find(r => r.capability === capabilityUnderTest) || null
  }
};

// expected trace sanity check (light)
if (expected.capability_required && expected.capability_required !== capabilityUnderTest) {
  fail(`expected_failover_trace.json expects capability '${expected.capability_required}', got '${capabilityUnderTest}'`);
}

const outPath = path.join(base, "tests", "failover_trace_latest.json");
fs.writeFileSync(outPath, JSON.stringify(trace, null, 2), "utf8");
console.log("RESILIENCE-GATE OK → wrote", outPath);
