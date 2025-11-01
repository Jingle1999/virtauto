// website/assets/agents.js
(async () => {
  const $list = document.getElementById('agent-list');
  if (!$list) return;

  const regText = await (await fetch('/website/registry.yaml', { cache: 'no-store' })).text();
  const reg = jsyaml.load(regText) || { agents: [] };

    fetch('/status/status.json', { cache: 'no-store' })
  ]);

  const reg = regRes.status === 'fulfilled' ? await regRes.value.json() : { agents: [] };
  const st  = stRes.status  === 'fulfilled' ? await stRes.value.json()  : {};
  const stMap = new Map((st.agents || []).map(a => [String(a.agent).toLowerCase(), a]));

  const order = (s) => (s === 'error' ? 0 : s === 'issue' ? 1 : s === 'preparing' ? 2 : s === 'ok' ? 3 : 9);

  const agents = reg.agents
    .map(a => {
      const live = stMap.get(String(a.id || a.name || '').toLowerCase());
      const status = (live && live.status) ? String(live.status).toLowerCase() : String(a.status || 'unknown').toLowerCase();
      const http = live && live.http && Number.isFinite(live.http.code) ? live.http.code : undefined;
      return { ...a, status, http };
    })
    .sort((a, b) => order(a.status) - order(b.status) || a.name.localeCompare(b.name));

  $list.innerHTML = agents.map(a => {
    const cls = `agent-card ${a.status || 'unknown'}`;
    const tags = (a.tags || []).map(t => `<span class="tag">${t}</span>`).join('');
    const caps = (a.capabilities || []).slice(0,4).map(t => `<code>${t}</code>`).join(' ');
    const http = a.http ? ` • HTTP ${a.http}` : '';
    return `
      <article class="${cls}" title="${a.description || ''}">
        <header>
          <h3>${a.name}</h3>
          <span class="dot"></span>
        </header>
        <p class="desc">${a.description || ''}</p>
        <p class="meta">Owner: <strong>${a.owner || '-'}</strong> • Status: <strong>${a.status}</strong>${http}</p>
        <p class="caps">${caps}</p>
        <footer>${tags}</footer>
      </article>`;
  }).join('');
})();
