
(async function() {
  const el = document.getElementById('status-list');
  const search = document.getElementById('search');
  const typeSel = document.getElementById('type');
  const limitSel = document.getElementById('limit');
  const pill = (t, cls) => `<span class="badge ${cls}">${t}</span>`;

  let data = [];
  async function load() {
    try {
      const res = await fetch('news.json', { cache:'no-store' });
      data = await res.json();
    } catch (e) {
      data = [];
    }
    render();
  }

  function render() {
    const q = (search.value || '').toLowerCase();
    const type = typeSel.value;
    const limit = parseInt(limitSel.value || '50', 10);
    const items = data
      .filter(d => (type === 'all' || (d.type || '').toLowerCase() === type))
      .filter(d => JSON.stringify(d).toLowerCase().includes(q))
      .slice(0, limit);

    el.innerHTML = items.map(d => {
      const status = (d.status || 'info').toLowerCase();
      const cls = status === 'success' ? 'ok' : (status === 'failure' ? 'err' : 'info');
      const ts = d.timestamp || d.time || '';
      return `<div class="item">
        ${pill(d.type || 'event', cls)}
        <div>
          <div>${d.summary || d.message || '—'}</div>
          <small>[${ts}] • source: ${d.agent || 'CI/CD'}</small>
        </div>
      </div>`;
    }).join('');
  }

  document.getElementById('refresh').addEventListener('click', load);
  [search, typeSel, limitSel].forEach(c => c.addEventListener('input', render));

  // Auto refresh
  const ar = document.getElementById('autorefresh');
  let timer = null;
  function setAR() {
    if (timer) clearInterval(timer);
    const s = parseInt(ar.value,10);
    if (s > 0) timer = setInterval(load, s * 1000);
  }
  ar.addEventListener('change', setAR);

  await load();
  setAR();
})();
