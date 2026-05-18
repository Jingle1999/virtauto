// website/assets/agents.js
(async () => {
  const container = document.getElementById("agent-list");
  if (!container) return;

  const SSOT_URL = "/ops/reports/system_status.json?_=" + Date.now();

  const truthMissing = (msg) => {
    container.innerHTML = `
      <article class="agent-card unknown">
        <header>
          <h3>TRUTH MISSING</h3>
          <span class="dot"></span>
        </header>
        <p class="desc">${msg}</p>
        <p class="meta">Source: ops/reports/system_status.json</p>
      </article>`;
  };

  const titleCase = (s) =>
    String(s || "")
      .replace(/_/g, " ")
      .replace(/\b\w/g, (c) => c.toUpperCase());

  const displayName = (id) => {
    const key = String(id || "").toLowerCase();
    if (key === "george") return "GEORGE";
    if (key === "deploy_agent") return "Deploy Agent";
    if (key === "site_audit") return "Site Audit";
    return titleCase(key);
  };

  const effectiveStatus = (a) => {
    const st = String(a?.status ?? "unknown").toLowerCase();
    const state = String(a?.state ?? "").toLowerCase();
    if (state === "planned") return "preparing";
    return st || "unknown";
  };

  const order = (s) =>
    s === "error" ? 0 :
    s === "issue" ? 1 :
    s === "blocked" ? 2 :
    s === "degraded" ? 3 :
    s === "preparing" ? 4 :
    s === "ok" ? 5 :
    9;

  try {
    const res = await fetch(SSOT_URL, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const ssot = await res.json();

    const agentsObj =
      ssot &&
      ssot.agents &&
      typeof ssot.agents === "object" &&
      !Array.isArray(ssot.agents)
        ? ssot.agents
        : null;

    if (!agentsObj) {
      truthMissing("SSOT does not contain a valid agents object.");
      return;
    }

    const agents = Object.entries(agentsObj)
      .map(([id, a]) => ({
        id,
        name: displayName(id),
        status: effectiveStatus(a),
        role: a?.role ?? "-",
        mode: a?.autonomy_mode ?? "-",
        state: a?.state ?? "-"
      }))
      .sort((a, b) =>
        order(a.status) - order(b.status) ||
        a.name.localeCompare(b.name)
      );

    container.innerHTML = agents.map(a => `
      <article class="agent-card ${a.status}">
        <header>
          <h3>${a.name}</h3>
          <span class="dot"></span>
        </header>
        <p class="desc">
          Role: <strong>${a.role}</strong> · 
          Mode: <strong>${a.mode}</strong> · 
          State: <strong>${a.state}</strong>
        </p>
        <p class="meta">
          Status: <strong>${a.status}</strong> · 
          ID: <span class="mono">${a.id}</span>
        </p>
      </article>
    `).join("");

  } catch (e) {
    truthMissing("SSOT not reachable.");
  }
})();