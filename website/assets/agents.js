// website/assets/agents.js
(async () => {
  const $list = document.getElementById('agent-list');
  if (!$list) return;

  const SSOT_URL = '/ops/reports/system_status.json?_=' + Date.now();

  const truthMissing = (msg) => {
    $list.innerHTML = `
      <article class="agent-card unknown" style="border:1px dashed #2a3850;">
        <header>
          <h3>TRUTH MISSING</h3>
          <span class="dot"></span>
        </header>
        <p class="desc">${msg}</p>
        <p class="meta">Source: <strong>ops/reports/system_status.json</strong></p>
      </article>
    `;
  };

  try {
    const res = await fetch(SSOT_URL, { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const ssot = await res.json();

    // HARD SSOT rule: agent list must come from SSOT
    const agents = Array.isArray(ssot.agents) ? ssot.agents : null;
    if (!agents) {
      truthMissing(`Expected <code>agents[]</code> in SSOT, but it is missing.`);
      return;
    }
    if (agents.length === 0) {
      truthMissing(`SSOT contains <code>agents[]</code>, but it is empty.`);
      return;
    }

    // Normalize status ordering (deterministic)
    const order = (s) => (
      s === 'error' ? 0 :
      s === 'issue' ? 1 :
      s === 'preparing' ? 2 :
      s === 'ok' ? 3 :
      s === 'degraded' ? 4 :
      s === 'blocked' ? 5 :
      s === 'unknown' ? 6 : 9
    );

    const norm = (a) => {
      const status = String(a.status ?? a.state ?? 'unknown').toLowerCase();
      const name = String(a.name ?? a.agent ?? a.id ?? 'Unnamed Agent');
      const owner = String(a.owner ?? '-');
      const desc = String(a.description ?? '');
      const tags = Array.isArray(a.tags) ? a.tags : [];
      const caps = Array.isArray(a.capabilities) ? a.capabilities : [];
      const httpCode =
        a.http && Number.isFinite(a.http.code) ? a.http.code :
        Number.isFinite(a.http) ? a.http :
        undefined;

      return { raw: a, name, owner, desc, status, tags, caps, httpCode };
    };

    const view = agents
      .map(norm)
      .sort((a, b) => order(a.status) - order(b.status) || a.name.localeCompare(b.name));

    $list.innerHTML = view.map(a => {
      const cls = `agent-card ${a.status || 'unknown'}`;
      const tags = a.tags.map(t => `<span class="tag">${String(t)}</span>`).join('');
      const caps = a.caps.slice(0, 4).map(t => `<code>${String(t)}</code>`).join(' ');
      const http = a.httpCode ? ` • HTTP ${a.httpCode}` : '';
      const safeTitle = (a.desc || '').replace(/"/g, '&quot;');

      return `
        <article class="${cls}" title="${safeTitle}">
          <header>
            <h3>${a.name}</h3>
            <span class="dot"></span>
          </header>
          <p class="desc">${a.desc}</p>
          <p class="meta">Owner: <strong>${a.owner}</strong> • Status: <strong>${a.status}</strong>${http}</p>
          <p class="caps">${caps}</p>
          <footer>${tags}</footer>
        </article>`;
    }).join('');

  } catch (e) {
    console.error('agents.js error:', e);
    truthMissing(`SSOT not available (${String(e.message || e)}).`);
  }
})();