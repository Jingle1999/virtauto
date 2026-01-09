// assets/agent-status.js
(() => {
  'use strict';

  // ===== Config =====
  const TRUTH_PATH = '/ops/reports/system_status.json';
  const REFRESH_MS = 60_000; // 1 min (low noise, still "alive")

  // ===== Utilities =====
  const $ = (sel, root = document) => root.querySelector(sel);

  function safe(v, fallback = '—') {
    return (v === undefined || v === null || v === '') ? fallback : String(v);
  }

  function upper(v, fallback = '—') {
    return safe(v, fallback).toUpperCase();
  }

  function fmtPct(v) {
    if (v === undefined || v === null) return '—';
    const n = Number(v);
    if (!Number.isFinite(n)) return '—';
    const pct = (n <= 1) ? (n * 100) : n;
    return `${pct.toFixed(1)}%`;
  }

  function fmtWhen(iso) {
    if (!iso) return '—';
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return String(iso);
    // compact UTC-ish display
    return d.toISOString().slice(0, 19).replace('T', ' ');
  }

  function classifySignal(signal) {
    const s = String(signal || '').toUpperCase();
    if (s.includes('FAIL') || s.includes('CRIT') || s.includes('RED')) return 'crit';
    if (s.includes('WARN') || s.includes('DEGRADED') || s.includes('YELLOW') || s.includes('REVIEW')) return 'warn';
    return 'ok';
  }

  function classifyAgentState(state) {
    const s = String(state || '').toUpperCase();
    if (['ACTIVE', 'OK', 'GREEN', 'ONLINE', 'PASS', 'OPERATIONAL'].includes(s)) return 'ok';
    if (['PLANNED', 'MVP', 'IN_PROGRESS', 'UNKNOWN', 'SUPERVISED', 'MANUAL', 'LIMITED'].includes(s)) return 'warn';
    if (['FAIL', 'FAILED', 'DOWN', 'CRITICAL', 'ISSUE', 'BLOCK'].includes(s)) return 'crit';
    return 'warn';
  }

  async function fetchTruth() {
    const res = await fetch(TRUTH_PATH, { cache: 'no-store' });
    if (!res.ok) throw new Error(`Truth source not reachable (${res.status})`);
    const json = await res.json();
    if (!json || typeof json !== 'object') throw new Error('Truth source returned invalid JSON.');
    return json;
  }

  // ===== Agent roster + alias mapping =====
  // We resolve "canonical agent" -> first matching key in status.agents
  const AGENTS = [
    { id: 'status',      label: 'Status Agent',       aliases: ['status', 'status_agent', 'monitor', 'monitoring', 'self_monitoring'] },
    { id: 'audit',       label: 'Audit Agent',        aliases: ['audit', 'audit_agent', 'site_audit', 'quality_audit'] },
    { id: 'security',    label: 'Security Agent',     aliases: ['security', 'security_agent', 'guardian', 'self_guardian'] },
    { id: 'consistency', label: 'Consistency Agent',  aliases: ['consistency', 'consistency_agent', 'lint', 'terminology'] },
    { id: 'content',     label: 'Content Agent',      aliases: ['content', 'content_agent', 'self_content'] },
    { id: 'release',     label: 'Release Agent',      aliases: ['release', 'release_agent', 'deploy', 'deploy_agent'] },
    { id: 'sre',         label: 'Site Reliability',   aliases: ['sre', 'site_reliability', 'reliability', 'reliability_agent'] },
  ];

  function resolveAgentKey(agentsObj, aliases) {
    if (!agentsObj) return null;
    const keys = Object.keys(agentsObj);
    const lower = new Map(keys.map(k => [k.toLowerCase(), k]));
    for (const a of aliases) {
      const hit = lower.get(String(a).toLowerCase());
      if (hit) return hit;
    }
    return null;
  }

  // ===== Render =====
  function ensureContainer() {
    const el = document.getElementById('agent-chips');
    return el || null;
  }

  function renderSkeleton(container) {
    container.innerHTML = `
      <div class="agentic-strip" role="group" aria-label="Agent status strip">
        <div class="agentic-strip__left" aria-label="System indicators"></div>
        <div class="agentic-strip__right" aria-label="Agent health"></div>
      </div>
    `;
  }

  function renderSystemIndicators(container, status) {
    const left = $('.agentic-strip__left', container);
    if (!left) return;

    const generatedAt = status.generated_at || status.generatedAt || status.timestamp || null;

    const sysState =
      (status.system && status.system.state) ||
      (status.system_state && status.system_state.state) ||
      status.system_state ||
      '—';

    const sysMode =
      (status.system && status.system.mode) ||
      status.mode ||
      '—';

    const healthSignal = (status.health && status.health.signal) || '—';
    const healthScore = (status.health && (status.health.overall_score || status.health.score)) ?? null;

    const autonomyObj = status.autonomy_score || status.autonomy || {};
    const autonomyPct = autonomyObj.percent ?? autonomyObj.value ?? autonomyObj.current_level ?? null;

    // governance visibility: if we have decision trace links, we can claim "trace available"
    const links = status.links || {};
    const traceAvail = Boolean(links.decision_trace || links.decision_trace_jsonl || links.latest_decision);

    const sysCls = classifySignal(healthSignal);

    left.innerHTML = `
      <span class="agentic-pill ${sysCls}" title="System state from truth source">
        <span class="dot"></span>
        ${upper(sysState)} · ${upper(sysMode)}
      </span>

      <span class="agentic-pill ${sysCls}" title="Health signal from truth source">
        <span class="dot"></span>
        HEALTH ${upper(healthSignal)}${healthScore !== null ? ` · ${fmtPct(healthScore)}` : ''}
      </span>

      <span class="agentic-pill" title="Confirmed autonomy from truth source (not a claim beyond evidence)">
        <span class="dot"></span>
        AUTONOMY ${fmtPct(autonomyPct)}
      </span>

      <span class="agentic-pill ${traceAvail ? 'ok' : 'warn'}" title="Governance visibility (evidence links)">
        <span class="dot"></span>
        GOVERNANCE ${traceAvail ? 'TRACE-AVAILABLE' : 'LIMITED'}
      </span>

      <span class="agentic-meta" title="Truth source freshness">
        updated ${fmtWhen(generatedAt)}
      </span>
    `;
  }

  function renderAgents(container, status) {
    const right = $('.agentic-strip__right', container);
    if (!right) return;

    const agentsObj = status.agents || {};
    const generatedAt = status.generated_at || status.generatedAt || status.timestamp || null;

    const items = AGENTS.map(spec => {
      const key = resolveAgentKey(agentsObj, spec.aliases);
      const data = key ? agentsObj[key] : null;

      const state = data ? (data.state || data.status || 'UNKNOWN') : 'UNKNOWN';
      const mode = data ? (data.autonomy_mode || data.autonomy || '') : '';
      const cls = classifyAgentState(state);

      // Keep copy governance-safe: "operational/degraded/unknown" – no "autonomous"
      const labelState =
        cls === 'ok' ? 'OPERATIONAL' :
        cls === 'crit' ? 'DEGRADED' :
        'UNKNOWN';

      const title = [
        spec.label,
        `state=${upper(state)}`,
        mode ? `mode=${upper(mode)}` : null,
        `truth=${TRUTH_PATH}`,
        generatedAt ? `updated=${fmtWhen(generatedAt)}` : null
      ].filter(Boolean).join(' • ');

      return `
        <span class="agent-chip ${cls}" title="${title}">
          <span class="dot"></span>
          <span class="agent-chip__name">${spec.label}</span>
          <span class="agent-chip__state">${labelState}</span>
        </span>
      `;
    }).join('');

    right.innerHTML = items;
  }

  function render(container, status) {
    if (!container.querySelector('.agentic-strip')) renderSkeleton(container);
    renderSystemIndicators(container, status);
    renderAgents(container, status);
  }

  function renderDegraded(container, err) {
    if (!container) return;
    container.innerHTML = `
      <div class="agentic-strip" role="group" aria-label="Agent status strip">
        <div class="agentic-strip__left">
          <span class="agentic-pill warn" title="Truth source not reachable">
            <span class="dot"></span>
            SYSTEM UNKNOWN
          </span>
          <span class="agentic-meta">truth unavailable</span>
        </div>
        <div class="agentic-strip__right">
          <span class="agent-chip warn" title="${safe(err && err.message ? err.message : err)}">
            <span class="dot"></span>
            <span class="agent-chip__name">Agent Strip</span>
            <span class="agent-chip__state">UNKNOWN</span>
          </span>
        </div>
      </div>
    `;
  }

  // ===== Boot =====
  async function bootOnce() {
    const container = ensureContainer();
    if (!container) return;

    try {
      const status = await fetchTruth();
      render(container, status);
    } catch (err) {
      console.error('[agent-status] ', err);
      renderDegraded(container, err);
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    bootOnce();
    window.setInterval(bootOnce, REFRESH_MS);
  });
})();
