<script>
// --- Agent dashboard wiring (reads /status/status.json + /status/agent_reports.md) ---

// 1) Welche Agenten & Tags angezeigt werden
const AGENTS = [
  { key: "monitoring",   label: "Monitoring Agent", tags: ["uptime","http","crawl","HTTP 200"] },
  { key: "self_guardian",label: "Guardian Agent",   tags: ["policies","integrity","headers"] },
  { key: "audit",        label: "Audit Agent",      tags: ["evidence","controls","links"] },
  { key: "deploy",       label: "Deploy Agent",     tags: ["build","publish","rollback"] },
  { key: "content",      label: "Content Agent",    tags: ["ingest","draft","review"] }
];

// 2) Status -> CSS Klasse
function statusClass(s) {
  const x = (s || "").toLowerCase();
  if (x === "ok" || x === "success" || x === "passing") return "status-ok";
  if (x === "fail" || x === "failed" || x === "error" || x === "failing") return "status-fail";
  return "status-unknown";
}

// 3) Karte rendern
function cardHtml(meta, st) {
  const klass = statusClass(st.status);
  const http  = st.http ? ` ${st.http.code ? "HTTP " + st.http.code : ""}` : "";
  const ts    = st.timestamp ? new Date(st.timestamp).toISOString() : "";
  const base  = st.base_url || "";
  const metaLine = [ts, base].filter(Boolean).join(" · ");
  const tags = (meta.tags || []).map(t => `<span class="tag">${t}</span>`).join("");

  return `
    <div class="card">
      <div class="row">
        <div class="agent">${meta.label}</div>
        <div class="meta ${klass}">${(st.status || "UNKNOWN").toUpperCase()}${http}</div>
      </div>
      <div class="row tags">${tags}</div>
      ${metaLine ? `<div class="row meta small">${metaLine}</div>` : ``}
    </div>
  `;
}

// 4) Laden & Refresh
async function refreshDashboard() {
  // 4a) status.json laden
  let status = { agents: [] };
  try {
    const r = await fetch("/ops/reports/system_status.json", { cache: "no-store" });
    if (r.ok) status = await r.json();
  } catch (_) {}

  // 4b) Map by key
  const byKey = Object.fromEntries((status.agents || []).map(a => [a.agent || a.key || a.name, a]));

  // 4c) Karten injizieren
  const grid = document.getElementById("agents");
  if (grid) {
    grid.innerHTML = AGENTS.map(meta => cardHtml(meta, byKey[meta.key] || {status:"unknown"})).join("");
  }

  // 4d) Latest Markdown Report (optional)
  try {
    const rep = await fetch("/status/agent_reports.md", { cache: "no-store" });
    if (rep.ok) {
      const txt  = await rep.text();
      const pre  = document.getElementById("report");
      const meta = document.getElementById("repMeta");
      if (pre)  pre.textContent  = txt || "No report yet.";
      if (meta) meta.textContent = status.last_update ? `updated ${status.last_update}` : "";
    }
  } catch (_) {}
}

// Initial paint + Auto-Refresh
refreshDashboard();
setInterval(refreshDashboard, 60_000);
</script>
