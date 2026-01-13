/* assets/agent-status.js
   Desktop contract (>=992px):
   - render ONLY a single navigational chip: "Agentic Website" -> /status/
   - NO polling / NO dynamic updates on desktop
   Mobile:
   - keep existing detailed agent strip + polling
*/
"use strict";

/* =========================
   Config
========================= */
const TRUTH_PATH = "/ops/reports/system_status.json";
const REFRESH_MS = 30 * 1000; // 30s

/* =========================
   Tiny helpers
========================= */
const $ = (sel, root = document) => root.querySelector(sel);

function isDesktopInitially() {
  // Static-at-load semantics (no resize re-render)
  return window.innerWidth >= 992;
}

function safe(v, fallback = "") {
  return v === undefined || v === null ? fallback : v;
}

function upper(v, fallback = "") {
  return String(safe(v, fallback)).toUpperCase();
}

function fmtPct(v) {
  const n = Number(v);
  if (!Number.isFinite(n)) return null;
  // Accept either 0..1 or 0..100
  const pct = n <= 1 ? n * 100 : n;
  return `${pct.toFixed(1)}%`;
}

function fmtTs(ts) {
  if (!ts) return null;
  // If already ISO-ish string, keep it short
  const s = String(ts);
  // avoid throwing on weird inputs
  try {
    const d = new Date(s);
    if (Number.isNaN(d.getTime())) return s;
    // yyyy-mm-dd hh:mm:ss (local)
    const pad = (x) => String(x).padStart(2, "0");
    return (
      `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ` +
      `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
    );
  } catch {
    return s;
  }
}

/* =========================
   Classification
========================= */
function classifySignal(state) {
  const s = upper(state, "");
  // ok-ish
  if (
    ["ACTIVE", "OK", "GREEN", "ONLINE", "PASS", "OPERATIONAL", "ENFORCED"].some(
      (k) => s.includes(k)
    )
  )
    return "ok";
  // warning-ish
  if (["WARN", "IN_PROGRESS", "UNKNOWN", "SUPERVISED", "MANUAL", "LIMITED"].some((k) => s.includes(k)))
    return "warn";
  // critical-ish
  if (["FAIL", "FAILED", "DOWN", "CRITICAL", "ISSUE", "BLOCK"].some((k) => s.includes(k)))
    return "crit";
  return "warn";
}

function classifyAgentState(state) {
  const s = upper(state, "");
  if (["OPERATIONAL", "ONLINE", "ACTIVE", "OK", "PASS"].some((k) => s.includes(k))) return "ok";
  if (["DEGRADED", "ERROR", "FAIL", "FAILED", "OFFLINE", "DOWN"].some((k) => s.includes(k))) return "crit";
  return "warn"; // UNKNOWN / anything else
}

/* =========================
   Agent mapping
========================= */
const AGENTS = [
  { id: "status", label: "Status Agent", aliases: ["status", "status_agent", "monitor", "monitoring", "self_monitoring"] },
  { id: "audit", label: "Audit Agent", aliases: ["audit", "audit_agent", "site_audit", "quality_audit"] },
  { id: "security", label: "Security Agent", aliases: ["security", "security_agent", "guardian", "self_guardian"] },
  { id: "consistency", label: "Consistency Agent", aliases: ["consistency", "consistency_agent", "self_consistency", "self_knowledge"] },
  { id: "content", label: "Content Agent", aliases: ["content", "content_agent", "self_content", "self_creation"] },
  { id: "release", label: "Release Agent", aliases: ["release", "release_agent", "deploy", "deploy_agent"] },
  { id: "sre", label: "Site Reliability", aliases: ["sre", "site_reliability", "reliability", "reliability_agent"] },
];

function resolveAgentKey(agentsObj, aliases) {
  if (!agentsObj) return null;
  const keys = Object.keys(agentsObj);
  const lower = new Map(keys.map((k) => [k.toLowerCase(), k]));
  for (const a of aliases) {
    const hit = lower.get(String(a).toLowerCase());
    if (hit) return hit;
  }
  return null;
}

/* =========================
   DOM targets
========================= */
function ensureContainer() {
  return document.getElementById("agent-chips");
}

/* =========================
   Desktop: single chip
========================= */
function renderDesktopFlag(container) {
  container.innerHTML = `
    <div class="agent-flag">
      <a href="/status/" class="agent-link">Agentic Website</a>
    </div>
  `;
}

/* =========================
   Mobile: full strip
========================= */
function renderSkeleton(container) {
  container.innerHTML = `
    <div class="agentic-strip" role="group" aria-label="Agent status strip">
      <div class="agentic-strip__left" aria-label="System indicators"></div>
      <div class="agentic-strip__right" aria-label="Agent health"></div>
    </div>
  `;
}

function renderSystemIndicators(container, status) {
  const left = $(".agentic-strip__left", container);
  if (!left) return;

  const generatedAt =
    status?.generated_at ||
    status?.generatedAt ||
    status?.timestamp ||
    status?.generated ||
    null;

  const sysState =
    status?.system?.state ||
    status?.system_state ||
    status?.systemState ||
    status?.state ||
    null;

  const sysMode =
    status?.system?.mode ||
    status?.system_mode ||
    status?.systemMode ||
    status?.mode ||
    null;

  const healthSignal =
    status?.health?.signal ||
    status?.health_signal ||
    status?.healthSignal ||
    null;

  const healthScore =
    status?.health?.overall_score ||
    status?.health?.score ||
    status?.health_overall_score ||
    status?.health_score ||
    null;

  const autonomyObj = status?.autonomy_score || status?.autonomy || null;
  const autonomyPct =
    autonomyObj?.percent ?? autonomyObj?.pct ?? autonomyObj?.value ?? null;

  const links = status?.links || {};
  const traceAvail = Boolean(links?.decision_trace || links?.decision_trace_json || links?.latest_decision);

  const sysCls = classifySignal(healthSignal || sysState);

  const healthScoreText = fmtPct(healthScore);
  const autonomyText = fmtPct(autonomyPct);
  const updatedText = fmtTs(generatedAt);

  // Keep labels short & “governance-safe”
  left.innerHTML = `
    <span class="agentic-pill ${sysCls}" title="System state from truth source">
      <span class="dot"></span>
      ${upper(sysState, "ACTIVE")}${sysMode ? ` · ${upper(sysMode)}` : ""}
    </span>

    <span class="agentic-pill ${classifySignal(healthSignal)}" title="Health signal from truth source">
      <span class="dot"></span>
      HEALTH ${upper(healthSignal, "UNKNOWN")}${healthScoreText ? ` · ${healthScoreText}` : ""}
    </span>

    ${autonomyText ? `
      <span class="agentic-pill ok" title="Confirmed autonomy from truth source (not a claim beyond evidence)">
        <span class="dot"></span>
        AUTONOMY ${autonomyText}
      </span>
    ` : ""}

    <span class="agentic-pill ${traceAvail ? "ok" : "warn"}" title="Governance visibility (evidence links)">
      <span class="dot"></span>
      GOVERNANCE ${traceAvail ? "TRACE-AVAILABLE" : "LIMITED"}
    </span>

    ${updatedText ? `<span class="agentic-meta" title="Truth source freshness">updated ${updatedText}</span>` : ""}
  `;
}

function renderAgents(container, status) {
  const right = $(".agentic-strip__right", container);
  if (!right) return;

  const agentObj = status?.agents || status?.agent || status?.agent_status || {};
  const generatedAt =
    status?.generated_at ||
    status?.generatedAt ||
    status?.timestamp ||
    status?.generated ||
    null;

  const items = AGENTS.map((spec) => {
    const key = resolveAgentKey(agentObj, spec.aliases);
    const data = key ? agentObj[key] : null;

    const rawState = data?.state ?? data?.status ?? "UNKNOWN";
    const rawMode = data?.autonomy_mode ?? data?.autonomy ?? data?.mode ?? null;

    const cls = classifyAgentState(rawState);

    // Keep copy governance-safe: only OPERATIONAL / DEGRADED / UNKNOWN
    const labelState =
      cls === "ok" ? "OPERATIONAL" : cls === "crit" ? "DEGRADED" : "UNKNOWN";

    const titleBits = [
      spec.label,
      `state=${upper(rawState)}`,
      rawMode ? `mode=${upper(rawMode)}` : null,
      `truth=${TRUTH_PATH}`,
      generatedAt ? `updated=${fmtTs(generatedAt)}` : null,
    ].filter(Boolean);

    const title = titleBits.join(" · ");

    return `
      <span class="agent-chip ${cls}" title="${title}">
        <span class="dot"></span>
        <span class="agent-chip__name">${spec.label}</span>
        <span class="agent-chip__state">${labelState}</span>
      </span>
    `;
  }).join("");

  right.innerHTML = items;
}

function render(container, status) {
  if (!container.querySelector(".agentic-strip")) renderSkeleton(container);
  renderSystemIndicators(container, status);
  renderAgents(container, status);
}

function renderDegraded(container, err) {
  const msg = safe(err?.message, "truth unavailable");
  container.innerHTML = `
    <div class="agentic-strip" role="group" aria-label="Agent status strip">
      <div class="agentic-strip__left" aria-label="System indicators">
        <span class="agentic-pill warn" title="Truth source not reachable">
          <span class="dot"></span>
          SYSTEM UNKNOWN
        </span>
        <span class="agentic-meta">${safe(msg)}</span>
      </div>
      <div class="agentic-strip__right" aria-label="Agent health">
        <span class="agent-chip warn" title="${safe(msg)}">
          <span class="dot"></span>
          <span class="agent-chip__name">Agent Strip</span>
          <span class="agent-chip__state">UNKNOWN</span>
        </span>
      </div>
    </div>
  `;
}

/* =========================
   Truth fetch + boot
========================= */
async function fetchTruth() {
  const res = await fetch(TRUTH_PATH, { cache: "no-store" });
  if (!res.ok) throw new Error(`Truth source not reachable (${res.status})`);
  const json = await res.json();
  if (!json || typeof json !== "object") throw new Error("Truth source returned invalid JSON");
  return json;
}

async function bootOnce() {
  const container = ensureContainer();
  if (!container) return;

  // Desktop short-circuit (authoritative)
  if (isDesktopInitially()) {
    renderDesktopFlag(container);
    return;
  }

  // Mobile: normal behavior
  try {
    const status = await fetchTruth();
    render(container, status);
  } catch (err) {
    // eslint-disable-next-line no-console
    console.error("[agent-status]", err);
    renderDegraded(container, err);
  }
}

// Static-at-load: decide polling based on initial width only
document.addEventListener("DOMContentLoaded", () => {
  const container = ensureContainer();
  if (!container) return;

  if (isDesktopInitially()) {
    renderDesktopFlag(container);
    return; // no polling on desktop
  }

  bootOnce();
  window.setInterval(bootOnce, REFRESH_MS);
});
