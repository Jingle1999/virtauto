(async () => {
  const badgeEl = document.getElementById('agent-chips');
  if (!badgeEl) return;

  try {
    const r = await fetch('/status/status.json', { cache: 'no-store' });
    const data = await r.json();
    const agents = data.agents || [];

    // Status sortieren (Issue/Error zuerst)
    const order = s => ({ error: 0, issue: 1, preparing: 2, ok: 3 }[s?.toLowerCase()] ?? 9);
    agents.sort((a, b) => order(a.status) - order(b.status));

    // HTML erzeugen
    badgeEl.innerHTML = agents.map(a => `
      <span class="agent-chip ${a.status?.toLowerCase() || 'unknown'}" title="${a.agent}: ${a.notes || ''}">
        <span class="dot"></span>${a.agent}
      </span>
    `).join('');
  } catch (e) {
    badgeEl.innerHTML = '<span class="agent-chip error">status unavailable</span>';
  }
})();
