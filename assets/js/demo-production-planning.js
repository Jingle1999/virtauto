(async function () {
  // 1) API first (local dev), then fallback to static demo files
  const API_BASE = "http://localhost:8000";
  const FALLBACK_BASE = "assets/demo/production-planning";

  const elVerdict = document.getElementById("pp-verdict");
  const elDecisionId = document.getElementById("pp-decision-id");
  const elLastRun = document.getElementById("pp-last-run");
  const elRows = document.getElementById("pp-plan-rows");
  const elTrace = document.getElementById("pp-trace");

  function esc(s) {
    return String(s ?? "").replace(/[&<>"']/g, m => ({
      "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
    }[m]));
  }

  async function fetchJson(url) {
    const r = await fetch(url, { cache: "no-store" });
    if (!r.ok) throw new Error("HTTP " + r.status);
    return r.json();
  }

  async function fetchText(url) {
    const r = await fetch(url, { cache: "no-store" });
    if (!r.ok) throw new Error("HTTP " + r.status);
    return r.text();
  }

  async function loadWithFallback(apiUrl, fallbackUrl, asText=false) {
    try {
      return asText ? await fetchText(apiUrl) : await fetchJson(apiUrl);
    } catch (_) {
      return asText ? await fetchText(fallbackUrl) : await fetchJson(fallbackUrl);
    }
  }

  try {
    const latest = await loadWithFallback(
      `${API_BASE}/pp/latest`,
      `${FALLBACK_BASE}/latest.json`
    );

    const status = await loadWithFallback(
      `${API_BASE}/pp/status`,
      `${FALLBACK_BASE}/system_status.json`
    );

    const traceText = await loadWithFallback(
      `${API_BASE}/pp/trace?limit=200`,
      `${FALLBACK_BASE}/decision_trace.jsonl`,
      true
    );

    // header
    elVerdict.textContent = status.governance_verdict || "—";
    elDecisionId.textContent = status.decision_id || latest.decision_id || "—";
    elLastRun.textContent = status.last_run_utc || "—";

    // plan table
    const plan = Array.isArray(latest.plan) ? latest.plan : [];
    elRows.innerHTML = plan.slice(0, 20).map(j => {
      const risk = j?.risk?.lateness_risk ? `${j.risk.lateness_risk}` : "—";
      return `<tr>
        <td style="padding:.5rem;border-bottom:1px solid #243255">${esc(j.order_id)}</td>
        <td style="padding:.5rem;border-bottom:1px solid #243255">${esc(j.variant)}</td>
        <td style="padding:.5rem;border-bottom:1px solid #243255">${esc(j.shift_id)}</td>
        <td style="padding:.5rem;border-bottom:1px solid #243255">${esc(j.start_utc)}</td>
        <td style="padding:.5rem;border-bottom:1px solid #243255">${esc(j.end_utc)}</td>
        <td style="padding:.5rem;border-bottom:1px solid #243255">${esc(j.due_utc)}</td>
        <td style="padding:.5rem;border-bottom:1px solid #243255">${esc(risk)}</td>
      </tr>`;
    }).join("");

    // trace
    elTrace.textContent = traceText.trim() || "—";
  } catch (e) {
    elVerdict.textContent = "—";
    elDecisionId.textContent = "—";
    elLastRun.textContent = "—";
    elRows.innerHTML = `<tr><td colspan="7" class="muted" style="padding:.75rem">Demo unavailable: ${esc(e?.message || String(e))}</td></tr>`;
    elTrace.textContent = "—";
  }
})();
