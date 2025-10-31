// assets/agent-status.js
(function () {
  const STATUS_URL = '/status/status.json';
  const REFRESH_MS = 60_000; // 60s

  const elBadge = document.getElementById('agentic-status');
  const elChips = document.getElementById('agent-chips');

  const setBadge = (ok, label, title = '') => {
    if (!elBadge) return;
    elBadge.classList.toggle('ok', !!ok);
    elBadge.classList.toggle('issue', !ok);
    elBadge.innerHTML = `<span class="dot"></span> ${label}`;
    if (title) elBadge.title = title;
  };

  const chipHtml = (a) => {
    const st = (a.status || '').toLowerCase();
    const cls = ['agent-chip', st || 'unknown'].join(' ');
    const code = a.http?.code ? ` · ${a.http.code}` : '';
    const note = a.notes ? ` — ${a.notes}` : '';
    const href = `/status/agents.html#${encodeURIComponent(a.agent || '').toLowerCase()}`;
    return `
      <a class="${cls}" href="${href}" title="${a.agent}${code}${note}">
        <span class="dot"></span>${a.agent || 'unknown'}
      </a>`;
  };

  const refresh = async () => {
    try {
      const base = location.pathname.startsWith('/virtauto') ? '/virtauto' : '';
      const r = await fetch(`${base}/status/status.json?_=${Date.now()}`, { cache: 'no-store' });
      if (!r.ok) throw new Error('status.json not found');
      const data = await r.json();
      const agents = Array.isArray(data.agents) ? data.agents : [];
      const ts = (agents[0]?.timestamp || data.timestamp || '').replace(' UTC', '') || '';
      const bad = agents.filter(a => ['issue', 'error'].includes(String(a.status).toLowerCase()));
      const prep = agents.filter(a => String(a.status).toLowerCase() === 'preparing');
      const okAll = agents.length > 0 && agents.every(a => ['ok', 'preparing'].includes(String(a.status).toLowerCase()));

      const label = `Agentic Website — last self-check: ${ts || '–'} · ${okAll ? 'OK' : 'ISSUE'}${prep.length ? ` (preparing ${prep.length})` : ''}`;
      setBadge(okAll, label, bad.length ? bad.map(a => `${a.agent}: ${a.status}${a.http?.code ? ` (${a.http.code})` : ''}`).join(' · ') : 'all agents healthy');

      if (elChips) {
        const order = v => (v === 'ok' ? 3 : v === 'preparing' ? 2 : v === 'issue' || v === 'error' ? 0 : 1);
        agents.sort((a, b) => order(String(a.status).toLowerCase()) - order(String(b.status).toLowerCase()));
        elChips.innerHTML = agents.map(chipHtml).join('');
      }
    } catch (e) {
      setBadge(false, 'Agentic Website — status unavailable', e.message);
      if (elChips) elChips.innerHTML = '';
    }
  };

  // initial + auto refresh
  window.addEventListener('DOMContentLoaded', refresh);
  setInterval(refresh, REFRESH_MS);
})();
