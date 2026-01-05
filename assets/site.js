/* virtauto site.js — unified behavior + agentic status (Single Source of Truth first)
   - Smooth anchor scroll (#...)
   - Mobile burger menu toggle
   - Agentic badge + agent chips (optional)
   - Mini dashboard (optional)
   - Activity feed from /ops/events.jsonl (optional)
*/

(function () {
  const TRUTH_PATH_PRIMARY = "/ops/reports/system_status.json"; // Single Source of Truth
  const TRUTH_PATH_FALLBACK = "/status/status.json";           // legacy fallback (if still present)

  const $ = (sel, root = document) => root.querySelector(sel);

  function safeText(el, txt) {
    if (!el) return;
    el.textContent = txt;
  }

  function setHTML(el, html) {
    if (!el) return;
    el.innerHTML = html;
  }

  function normalizeAgentsFromTruth(truth) {
    // Expected (truth-locked): { agents: { guardian:{state,...}, monitoring:{...}, ... }, generated_at, ... }
    const out = [];
    const obj = truth && truth.agents ? truth.agents : null;
    if (!obj || typeof obj !== "object") return out;

    for (const key of Object.keys(obj)) {
      const a = obj[key] || {};
      out.push({
        agent: a.name || a.label || key,
        key,
        // normalize to ok/issue/preparing/unknown-ish
        status: String(a.state || a.status || "unknown").toLowerCase(),
        autonomy_mode: a.autonomy_mode || a.autonomy || a.mode || "",
        notes: a.note || a.notes || "",
        timestamp: truth.generated_at || truth.generatedAt || truth.timestamp || ""
      });
    }
    return out;
  }

  function normalizeAgentsFromLegacy(legacy) {
    // Expected legacy: { agents: [ {agent,status,http:{code},notes,timestamp}, ... ] }
    const arr = legacy && Array.isArray(legacy.agents) ? legacy.agents : [];
    return arr.map(a => ({
      agent: a.agent || a.name || "unknown",
      key: (a.agent || a.name || "").toLowerCase(),
      status: String(a.status || "unknown").toLowerCase(),
      autonomy_mode: a.autonomy_mode || a.autonomy || a.mode || "",
      notes: a.notes || "",
      http: a.http,
      timestamp: a.timestamp || ""
    }));
  }

  async function fetchJSON(url) {
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status} for ${url}`);
    return await res.json();
  }

  async function getAgentData() {
    // 1) try truth source
    try {
      const truth = await fetchJSON(TRUTH_PATH_PRIMARY);
      const agents = normalizeAgentsFromTruth(truth);
      if (agents.length) return { source: "truth", url: TRUTH_PATH_PRIMARY, truth, agents };
      // if truth exists but no agents, still return (page might use only header)
      return { source: "truth", url: TRUTH_PATH_PRIMARY, truth, agents: [] };
    } catch (e1) {
      // 2) fallback legacy
      const legacy = await fetchJSON(TRUTH_PATH_FALLBACK);
      const agents = normalizeAgentsFromLegacy(legacy);
      return { source: "legacy", url: TRUTH_PATH_FALLBACK, legacy, agents };
    }
  }

  function classifyStatus(s) {
    const v = String(s || "").toLowerCase();
    if (["ok", "active", "online", "green", "initialized"].includes(v)) return "ok";
    if (["preparing", "mvp", "in_progress", "in-progress", "supervised", "warning", "warn"].includes(v)) return "preparing";
    if (["issue", "error", "failed", "down", "critical", "crit", "red", "block", "blocked"].includes(v)) return "issue";
    return "unknown";
  }

  function buildBadgeLabel(meta, agents) {
    const ts =
      (agents && agents[0] && agents[0].timestamp) ? String(agents[0].timestamp).replace(" UTC", "") : "—";

    const bad = (agents || []).filter(a => ["issue", "error"].includes(classifyStatus(a.status)));
    const prep = (agents || []).filter(a => classifyStatus(a.status) === "preparing");

    const okAll = (agents || []).length
      ? bad.length === 0 && (agents || []).every(a => ["ok", "preparing"].includes(classifyStatus(a.status)))
      : true;

    const statusWord = okAll ? "OK" : "ISSUE";
    const suffix = prep.length ? ` (preparing ${prep.length})` : "";

    return {
      okAll,
      label: `Agentic Website — last self-check: ${ts} — ${statusWord}${suffix}`,
      details: (bad.length ? bad : (agents || [])).map(a => {
        const note = a.notes ? ` — ${a.notes}` : "";
        const mode = a.autonomy_mode ? ` · ${a.autonomy_mode}` : "";
        return `${a.agent}: ${a.status}${mode}${note}`;
      }).join(" • ")
    };
  }

  function renderAgenticBadge(meta, agents) {
    const badgeEl = document.getElementById("agentic-status");
    if (!badgeEl) return;

    const { okAll, label, details } = buildBadgeLabel(meta, agents);

    badgeEl.classList.toggle("ok", okAll);
    badgeEl.classList.toggle("issue", !okAll);
    badgeEl.title = details || "";

    setHTML(badgeEl, `<span class="dot"></span> ${label}`);
  }

  function renderAgentChips(agents) {
    const chipsEl = document.getElementById("agent-chips");
    if (!chipsEl) return;

    const order = { issue: 0, error: 0, preparing: 1, ok: 2, active: 2 };
    const sorted = (agents || []).slice().sort((a, b) => {
      const aa = order[classifyStatus(a.status)] ?? 3;
      const bb = order[classifyStatus(b.status)] ?? 3;
      return aa - bb;
    });

    const chipHTML = sorted.map(a => {
      const st = classifyStatus(a.status);
      const cls = ["agent-chip", st].join(" ");
      const note = a.notes ? ` — ${a.notes}` : "";
      const mode = a.autonomy_mode ? ` · ${a.autonomy_mode}` : "";
      const href = "/status/"; // stable target
      return `<a class="${cls}" href="${href}" title="${a.agent}: ${a.status}${mode}${note}">
                <span class="dot"></span><span>${a.agent || "unknown"}</span>
              </a>`;
    }).join("");

    setHTML(chipsEl, chipHTML);
  }

  function renderMiniDashboard(meta, agents) {
    const box = document.getElementById("mini-dashboard");
    if (!box) return;

    const ok = (agents || []).filter(a => classifyStatus(a.status) === "ok").length;
    const issue = (agents || []).filter(a => classifyStatus(a.status) === "issue").length;
    const unknown = Math.max(0, (agents || []).length - ok - issue);

    setHTML(box, `
      <div><strong>${ok}</strong> OK</div>
      <div class="issue"><strong>${issue}</strong> Issues</div>
      <div><strong>${unknown}</strong> Unknown</div>
    `);
  }

  async function updateAgenticUI() {
    try {
      const meta = await getAgentData();
      const agents = meta.agents || [];
      renderAgenticBadge(meta, agents);
      renderAgentChips(agents);
      renderMiniDashboard(meta, agents);
    } catch (err) {
      const badgeEl = document.getElementById("agentic-status");
      if (badgeEl) {
        badgeEl.classList.remove("ok");
        badgeEl.classList.add("issue");
        setHTML(badgeEl, `<span class="dot"></span> Agentic Website — status unavailable`);
      }
      const box = document.getElementById("mini-dashboard");
      if (box) setHTML(box, `<span class="issue">Status unavailable</span>`);
      const chipsEl = document.getElementById("agent-chips");
      if (chipsEl) chipsEl.innerHTML = "";
      // eslint-disable-next-line no-console
      console.warn("Agentic UI update failed:", err);
    }
  }

  async function loadActivityFeed() {
    const list = document.getElementById("activity-list");
    if (!list) return;

    list.innerHTML = '<li class="activity-item activity-loading">Loading latest events…</li>';

    try {
      const res = await fetch("/ops/events.jsonl", { cache: "no-store" });
      if (!res.ok) throw new Error("HTTP " + res.status);

      const text = await res.text();
      const lines = text.split("\n").map(l => l.trim()).filter(Boolean);

      const events = lines.map(line => {
        try { return JSON.parse(line); } catch { return null; }
      }).filter(Boolean);

      events.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
      const latest = events.slice(0, 10);

      if (!latest.length) {
        list.innerHTML = '<li class="activity-item activity-empty">No recent events logged.</li>';
        return;
      }

      list.innerHTML = latest.map(ev => {
        const ts = ev.timestamp || "";
        const agent = ev.agent || ev.source || "unknown-agent";
        const evt = ev.event || ev.action || "event";
        const msg = ev.message || "";
        return `
          <li class="activity-item">
            <span class="activity-meta">${ts} · ${agent} · ${evt}</span>
            <span class="activity-message">${msg}</span>
          </li>
        `;
      }).join("\n");
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn("Activity feed error", err);
      list.innerHTML = '<li class="activity-item activity-error">Activity feed unavailable right now.</li>';
    }
  }

  function setupSmoothAnchors() {
    document.addEventListener("click", (e) => {
      const a = e.target.closest('a[href^="#"]');
      if (!a) return;
      const target = a.getAttribute("href");
      if (!target || target === "#") return;

      const el = document.querySelector(target);
      if (!el) return;

      e.preventDefault();
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  function setupBurger() {
    document.addEventListener("click", (e) => {
      const btn = e.target.closest(".burger");
      if (!btn) return;
      const menu = document.getElementById("menu");
      if (!menu) return;
      menu.classList.toggle("open");
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    setupSmoothAnchors();
    setupBurger();

    // Agentic widgets
    updateAgenticUI();
    setInterval(updateAgenticUI, 60000);

    // Activity feed if present
    loadActivityFeed();
    setInterval(loadActivityFeed, 60000);
  });
})();
