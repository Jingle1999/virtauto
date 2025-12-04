// assets/status.js
(async () => {
  const root = document.getElementById("status-app");
  if (!root) return; // Falls die ID auf der Seite nicht existiert

  try {
    // Statusdaten aus ops/status.json holen
    const res = await fetch("ops/status.json", { cache: "no-store" });
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }

    const s = await res.json();

    const agentsList = (s.agents_online_list || []).join(", ");
    const lastUpdate = s.last_update
      ? new Date(s.last_update).toLocaleString("de-DE", {
          timeZone: "Europe/Berlin",
        })
      : "n/a";

    // Einfache, aber “wertige” Status-Kacheln
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
          <p class="muted">${agentsList || "No agent list provided"}</p>
        </div>

        <div class="card">
          <div class="kicker">WORKFLOWS</div>
          <h3>${s.workflows} CI/CD workflows</h3>
          <p class="muted">Actively monitored by virtauto.OS</p>
        </div>

        <div class="card">
          <div class="kicker">LAST UPDATE</div>
          <h3>${lastUpdate}</h3>
          <p class="muted">Source: ops/status.json</p>
        </div>
      </div>
    `;
  } catch (e) {
    console.error("status.js error:", e);
    root.innerHTML =
      '<p class="muted">Status data not available right now. Please try again later.</p>';
  }
})();
