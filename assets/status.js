// assets/status.js
(async () => {
  const root = document.getElementById("status-app");
  if (!root) return;

  try {
    // Authoritative status data from SSOT
    const res = await fetch("/ops/reports/system_status.json?v=" + Date.now(), {
      cache: "no-store",
    });

    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }

    const s = await res.json();

    // 🔒 Phase 9: Hard SSOT Validation
    if (
      typeof s.autonomy_level !== "number" ||
      typeof s.autonomy_target !== "number" ||
      typeof s.agents_online !== "number" ||
      typeof s.agents_total !== "number" ||
      typeof s.workflows !== "number"
    ) {
      throw new Error("SSOT schema invalid");
    }

    const agentsList = Array.isArray(s.agents_online_list)
      ? s.agents_online_list.join(", ")
      : "No agent list provided";

    const lastUpdate = s.last_update
      ? new Date(s.last_update).toLocaleString("de-DE", {
          timeZone: "Europe/Berlin",
        })
      : "n/a";

    root.innerHTML = `
      <div class="status-cards">
        <div class="card">
          <div class="kicker">SYSTEM KPIs</div>
          <h3>Autonomy level: ${s.autonomy_level}%</h3>
          <p class="muted">Target: ${s.autonomy_target}% autonomous operations</p>
        </div>

        <div class="card">
          <div class="kicker">AGENTS</div>
          <h3>${s.agents_online} / ${s.agents_total} agents online</h3>
          <p class="muted">${agentsList}</p>
        </div>

        <div class="card">
          <div class="kicker">WORKFLOWS</div>
          <h3>${s.workflows} CI/CD workflows</h3>
          <p class="muted">Actively monitored by virtauto.OS</p>
        </div>

        <div class="card">
          <div class="kicker">LAST UPDATE</div>
          <h3>${lastUpdate}</h3>
          <p class="muted">Source: ops/reports/system_status.json</p>
        </div>
      </div>
    `;
  } catch (e) {
    console.error("status.js error:", e);

    // 🔒 No fallback rendering → SSOT hard enforcement
    root.innerHTML = `
      <div class="status-cards">
        <div class="card">
          <div class="kicker">TRUTH STATE</div>
          <h3>Truth unavailable</h3>
          <p class="muted">
            The Single Source of Truth (ops/reports/system_status.json) is missing or invalid.
          </p>
        </div>
      </div>
    `;
  }
})();
