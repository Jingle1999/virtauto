/* ============================================================
   agent-status.js
   Rendering authority: JavaScript
   Desktop: static single chip, no polling
   Mobile: full dynamic agent rendering
   ============================================================ */

'use strict';

/* -------------------- CONFIG -------------------- */
const TRUTH_PATH = '/ops/reports/system_status.json';
const REFRESH_MS = 30_000;
const DESKTOP_BREAKPOINT = 992;

/* -------------------- ENV CHECK -------------------- */
const IS_DESKTOP = window.innerWidth >= DESKTOP_BREAKPOINT;

/* ============================================================
   DESKTOP SHORT-CIRCUIT (STATIC AT LOAD TIME)
   ============================================================ */
if (IS_DESKTOP) {
  document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('agent-chips');
    if (!container) return;

    container.innerHTML = `
      <div class="agent-flag" role="navigation" aria-label="Agent status">
        <a href="/status/" class="agent-link">Agentic Website</a>
      </div>
    `;
  });

  // Hard stop: no polling, no fetches, no observers
  return;
}

/* ============================================================
   MOBILE IMPLEMENTATION (UNCHANGED BEHAVIOR)
   ============================================================ */

/* -------------------- HELPERS -------------------- */
const $ = (sel, root = document) => root.querySelector(sel);

function safe(v, fallback = '') {
  return (v === undefined || v === null) ? fallback : String(v);
}

function upper(v, fallback = '') {
  return safe(v, fallback).toUpperCase();
}

function pct(v) {
  if (v === undefined || v === null) return '—';
  const n = Number(v);
  if (Number.isNaN(n)) return '—';
  return `${Math.round(n)}%`;
}

/* -------------------- CLASSIFIERS -------------------- */
function classifyHealth(signal) {
  const s = upper(signal);
  if (['OK', 'GREEN', 'PASS', 'OPERATIONAL'].includes(s)) return 'ok';
  if (['WARN', 'YELLOW', 'DEGRADED', 'LIMITED'].includes(s)) return 'warn';
  return 'crit';
}

function classifyAgentState(state) {
  const s = upper(state);
  if (['ACTIVE', 'OK', 'GREEN', 'ONLINE', 'PASS', 'OPERATIONAL'].includes(s)) return 'ok';
  if (['WARN', 'DEGRADED', 'UNKNOWN', 'SUPERVISED', 'LIMITED'].includes(s)) return 'warn';
  return 'crit';
}

/* -------------------- FETCH -------------------- */
async function fetchTruth() {
  const res = await fetch(TRUTH_PATH, { cache: 'no-store' });
  if (!res.ok) throw new Error('Truth source not reachable');
  const json = await res.json();
  if (typeof json !== 'object') throw new Error('Invalid truth payload');
  return json;
}

/* -------------------- AGENT MAP -------------------- */
const AGENTS = [
  { key: 'status', label: 'Status Agent', aliases: ['status', 'status_agent', 'monitor'] },
  { key: 'audit', label: 'Audit Agent', aliases: ['audit', 'audit_agent'] },
  { key: 'security', label: 'Security Agent', aliases: ['security', 'guardian'] },
  { key: 'consistency', label: 'Consistency Agent', aliases: ['consistency'] },
  { key: 'content', label: 'Content Agent', aliases: ['content'] },
  { key: 'release', label: 'Release Agent', aliases: ['release', 'deploy'] },
  { key: 'sre', label: 'Site Reliability', aliases: ['sre', 'reliability'] }
];

function resolveAgent(obj, aliases) {
  if (!obj) return null;
  const keys = Object.keys(obj).map(k => k.toLowerCase());
  for (const a of aliases) {
    const hit = keys.find(k => k.includes(a));
    if (hit) return obj[hit];
  }
  return null;
}

/* -------------------- RENDER -------------------- */
function ensureContainer() {
  return document.getElementById('agent-chips');
}

function renderSkeleton(container) {
  container.innerHTML = `
    <div class="agent-strip" role="group" aria-label="Agent status strip">
      <div class="agent-strip_left" aria-label="System indicators"></div>
      <div class="agent-strip_right" aria-label="Agent health"></div>
    </div>
  `;
}

function renderSystem(container, status) {
  const left = $('.agent-strip_left', container);
  if (!left) return;

  const health = classifyHealth(status?.health?.signal);
  const score = pct(status?.health?.overall_score);
  const autonomy = pct(status?.autonomy?.score);

  left.innerHTML = `
    <span class="agent-pill ${health}" title="System health from truth source">
      <span class="dot"></span>
      HEALTH ${score}
    </span>
    <span class="agent-pill" title="Confirmed autonomy">
      <span class="dot"></span>
      AUTONOMY ${autonomy}
    </span>
  `;
}

function renderAgents(container, status) {
  const right = $('.agent-strip_right', container);
  if (!right) return;

  const agentsObj = status?.agents || {};

  right.innerHTML = AGENTS.map(spec => {
    const data = resolveAgent(agentsObj, spec.aliases) || {};
    const state = data.state || 'UNKNOWN';
    const cls = classifyAgentState(state);

    return `
      <span class="agent-chip ${cls}" title="${upper(state)}">
        <span class="dot"></span>
        <span class="agent-chip_name">${spec.label}</span>
        <span class="agent-chip_state">${upper(state)}</span>
      </span>
    `;
  }).join('');
}

function render(container, status) {
  if (!container.querySelector('.agent-strip')) {
    renderSkeleton(container);
  }
  renderSystem(container, status);
  renderAgents(container, status);
}

/* -------------------- BOOT -------------------- */
async function boot() {
  const container = ensureContainer();
  if (!container) return;

  try {
    const status = await fetchTruth();
    render(container, status);
  } catch (err) {
    console.error('[agent-status]', err);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  boot();
  setInterval(boot, REFRESH_MS);
});