// website/assets/agent-status.js
(function () {
  const SSOT_URL = "/ops/reports/system_status.json";
  const REFRESH_MS = 60000;

  const badge = document.getElementById("agentic-status");
  const chips = document.getElementById("agent-chips");

  const setBadge = (ok, text) => {
    if (!badge) return;
    badge.classList.toggle("ok", ok);
    badge.classList.toggle("issue", !ok);
    badge.innerHTML = `<span class="dot"></span> ${text}`;
  };

  const effectiveStatus = (a) => {
    const st = String(a?.status ?? "unknown").toLowerCase();
    const state = String(a?.state ?? "").toLowerCase();
    if (state === "planned") return "preparing";
    return st;
  };

  async function refresh() {
    try {
      const res = await fetch(SSOT_URL + "?_=" + Date.now(), { cache: "no-store" });
      if (!res.ok) throw new Error();
      const ssot = await res.json();

      const agents = ssot.agents || {};
      const entries = Object.entries(agents);

      const issues = entries.filter(([, a]) =>
        ["issue", "error", "blocked", "degraded"].includes(effectiveStatus(a))
      );

      setBadge(
        issues.length === 0,
        `Agentic Website — SSOT: ${ssot.generated_at || "n/a"}`
      );

      if (chips) {
        chips.innerHTML = entries.map(([id, a]) => `
          <span class="agent-chip ${effectiveStatus(a)}">
            <span class="dot"></span>${id}
          </span>
        `).join("");
      }

    } catch {
      setBadge(false, "Agentic Website — SSOT unavailable");
      if (chips) chips.innerHTML = "";
    }
  }

  refresh();
  setInterval(refresh, REFRESH_MS);
})();