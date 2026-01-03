/* virtauto site.js — unified UI behavior + truth-locked status
   - Smooth anchor scrolling
   - Mobile nav toggle
   - Agentic status + chips (truth source: /ops/reports/system_status.json)
   - Mini dashboard
   - Activity feed
*/

(() => {
  // -----------------------------
  // 0) Helpers
  // -----------------------------
  const $ = (sel) => document.querySelector(sel);

  async function fetchJSON(url) {
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) throw new Error(`${url} HTTP ${res.status}`);
    return res.json();
  }

  function safeText(v, fallback = "") {
    return typeof v === "string" && v.trim() ? v : fallback;
  }

  // -----------------------------
  // 1) Smooth scroll for hash links
  // -----------------------------
  document.addEventListener("click", (e) => {
    const a = e.target.closest('a[href^="#"]');
    if (!a) return;

    const href = a.getAttribute("href");
    const el = document.querySelector(href);
    if (!el) return;

    e.preventDefault();
    el.scrollIntoView({ behavior: "smooth" });
  });

  // -----------------------------
  // 2) Mobile nav toggle (works for all pages)
  // -----------------------------
  window.toggleMenu = function toggleMenu() {
    const menu = document.getElementById("menu");
    if (menu) menu.classList.toggle("open");
  };

  function initBurger() {
    // If burger exists and has inline onclick already, fine.
    // But ensure it works even if onclick wasn't wired.
    const burger = document.querySelector(".burger");
    const menu = document.getElementById("menu");
    if (!burger || !menu) return;

    if (!burger.__vaBound) {
      burger.addEventListener("click", () => menu.classList.toggle("open"));
      burger.__vaBound = true;
    }
  }

  // -----------------------------
  // 3) Truth-locked status (system_status.json)
  // -----------------------------
  const TRUTH_URL = "/ops/reports/system_status.json";

  function normalizeAgentList(systemStatus) {
    // supports multiple shapes
    // expected in your report: system_status.json has "agents": { "george": {...}, ... }
    const agentsObj = systemStatus?.agents;
    if (agentsObj && typeof agentsObj === "object" && !Array.isArray(agentsObj)) {
      return Object.entries(agentsObj).map(([name, a]) => ({
        agent: name,
        status: a?.status || a?.health || a?.state || "UNKNOWN",
        notes: a?.notes || "",
        http: a?.http || null,
        timestamp: a?.timestamp || systemStatus?.generated_at || systemStatus?.generated || "",
      }));
    }

    // fallback legacy: systemStatus.agents as array
    const agentsArr = systemStatus?.agents;
    if (Array.isArray(agentsArr)) return agentsArr;

    return [];
  }

  function computeMiniCounts(agents) {
    const norm = (s) => String(s || "").toLowerCase();

    const ok = agents.filter((a) => ["ok", "green", "healthy"].includes(norm(a.status))).length;
    const issue = agents.filter((a) => ["issue", "error", "red", "down"].includes(norm(a.status))).length;
    const unknown = Math.max(0, agents.length - ok - issue);

    return { ok, issue, unknown };
  }

  function setAgenticBadge(state, html, title = "") {
    const badgeEl = document.getElementById("agentic-status");
    if (!badgeEl) return;

    badgeEl.classList.toggle("ok", state === "ok");
    badgeEl.classList.toggle("issue", state === "issue");
    badgeEl.innerHTML = `<span class="dot"></span> ${html}`;
    if (title) badgeEl.title = title;
  }

  function renderChips(agents) {
    const chipsEl = document.getElementById("agent-chips");
    if (!chipsEl) return;

    const norm = (s) => String(s || "").toLowerCase();
    const order = { issue: 0, error: 0, down: 0, red: 0, preparing: 1, ok: 2, green: 2, healthy: 2 };

    const chipHTML = (agent) => {
      const st = norm(agent.status) || "unknown";
      const cls = ["agent-chip", st].join(" ");
      const code = agent.http?.code ? ` (${agent.http.code})` : "";
      const note = agent.notes ? ` — ${agent.notes}` : "";
      const href = "/status/agents.html#" + encodeURIComponent(String(agent.agent || "")).toLowerCase();

      return `<a class="${cls}" href="${href}" title="${agent.agent}: ${agent.status}${code}${note}">
        <span class="dot"></span><span>${agent.agent || "unknown"}</span>
      </a>`;
    };

    const sorted = [...agents].sort((a, b) => {
      const ao = order[norm(a.status)] ?? 3;
      const bo = order[norm(b.status)] ?? 3;
      return ao - bo;
    });

    chipsEl.innerHTML = sorted.map(chipHTML).join("");
  }

  function renderMiniDashboard(agents) {
    const box = document.getElementById("mini-dashboard");
    if (!box) return;

    const { ok, issue, unknown } = computeMiniCounts(agents);

    box.innerHTML = `
      <div><strong>${ok}</strong> OK</div>
      <div class="issue"><strong>${issue}</strong> Issues</div>
      <div><strong>${unknown}</strong> Unknown</div>
    `;
  }

  function renderAgenticSummary(systemStatus, agents) {
    // We want: "www.virtauto.de is operated as a governed agentic system and exposes its live operational state transparently."
    // plus autonomy + mode (truth locked)
    const autonomyPct =
      systemStatus?.autonomy_score?.percent ??
      Math.round((systemStatus?.autonomy_score?.value ?? 0) * 100);

    const mode =
      safeText(systemStatus?.autonomy_score?.mode) ||
      safeText(systemStatus?.system?.autonomy_mode) ||
      safeText(systemStatus?.autonomy) ||
      "—";

    const generated =
      safeText(systemStatus?.generated_at) ||
      safeText(systemStatus?.generated) ||
      safeText(systemStatus?.timestamp) ||
      "—";

    const norm = (s) => String(s || "").toLowerCase();
    const bad = agents.filter((a) => ["issue", "error", "down", "red"].includes(norm(a.status)));

    const okAll = bad.length === 0 && agents.length > 0;

    const details = (bad.length ? bad : agents)
      .slice(0, 8)
      .map((a) => {
        const code = a.http?.code ? ` (${a.http.code})` : "";
        const note = a.notes ? ` — ${a.notes}` : "";
        return `${a.agent}: ${a.status}${code}${note}`;
      })
      .join(" • ");

    const autonomyStr = Number.isFinite(autonomyPct) ? `${autonomyPct}% (${mode})` : `— (${mode})`;

    const label =
      `Governed agentic system — live state: ${autonomyStr} — generated: ${generated}` +
      (okAll ? " — OK" : " — ISSUE");

    setAgenticBadge(okAll ? "ok" : "issue", label, details || "status loaded");
  }

  async function updateTruthLockedStatus() {
    try {
      const data = await fetchJSON(TRUTH_URL);
      const agents = normalizeAgentList(data);

      renderAgenticSummary(data, agents);
      renderChips(agents);
      renderMiniDashboard(agents);
    } catch (err) {
      setAgenticBadge("issue", "Governed agentic system — status unavailable");
      const chipsEl = document.getElementById("agent-chips");
      if (chipsEl) chipsEl.innerHTML = "";
      const box = document.getElementById("mini-dashboard");
      if (box) box.innerHTML = `<span class="issue">Status unavailable</span>`;
    }
  }

  // -----------------------------
  // 4) Activity feed (ops/events.jsonl)
  // -----------------------------
  async function loadActivityFeed() {
    const list = document.getElementById("activity-list");
    if (!list) return;

    list.innerHTML = '<li class="activity-item activity-loading">Loading latest events…</li>';

    try {
      const res = await fetch("/ops/events.jsonl", { cache: "no-store" });
      if (!res.ok) throw new Error("HTTP " + res.status);

      const text = await res.text();
      const lines = text.split("\n").map((l) => l.trim()).filter(Boolean);

      const events = lines
        .map((line) => {
          try { return JSON.parse(line); } catch { return null; }
        })
        .filter(Boolean)
        .sort((a, b) => new Date(b.timestamp || 0) - new Date(a.timestamp || 0))
        .slice(0, 10);

      if (!events.length) {
        list.innerHTML = '<li class="activity-item activity-empty">No recent events logged.</li>';
        return;
      }

      list.innerHTML = events.map((ev) => {
        const ts = safeText(ev.timestamp, "").replace("T", " ").replace("Z", "");
        const agent = safeText(ev.agent || ev.source, "unknown-agent");
        const evt = safeText(ev.event || ev.action, "event");
        const msg = safeText(ev.message, "");
        return `
          <li class="activity-item">
            <span class="activity-meta">${ts} · ${agent} · ${evt}</span>
            <span class="activity-message">${msg}</span>
          </li>
        `;
      }).join("");
    } catch (err) {
      list.innerHTML =
        '<li class="activity-item activity-error">Activity feed unavailable right now.</li>';
    }
  }

  // -----------------------------
  // 5) Init
  // -----------------------------
  function init() {
    initBurger();

    // status + activity only if placeholders exist
    updateTruthLockedStatus();
    loadActivityFeed();

    // refresh status periodically (lightweight)
    setInterval(updateTruthLockedStatus, 60_000);

    // refresh activity feed periodically only if list exists
    if (document.getElementById("activity-list")) {
      setInterval(loadActivityFeed, 60_000);
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})();
