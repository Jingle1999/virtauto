/* virtauto dashboard logic (auto-refresh + filter + status mapping) */
(() => {
  const $ = (sel) => document.querySelector(sel);
  const list = $('#list');
  const q = $('#q');
  const filter = $('#filter');
  const limit = $('#limit');
  const refreshBtn = $('#refresh');
  const liveDot = $('#liveDot');
  const lastUpdated = $('#lastUpdated');

  const REFRESH_MS = 30_000;
  let timer;

  const iconFor = (event, summary='') => {
    const e = (event || '').toLowerCase();
    const s = (summary || '').toLowerCase();
    if (e.includes('success')) return 'ok';
    if (e.includes('start')) return 'info';
    if (e.includes('rollback')) return 'warn';
    if (e.includes('health') && (s.includes('fail') || s.includes('unreach'))) return 'err';
    if (e.includes('health')) return 'warn';
    return 'info';
  };

  const textIncludes = (hay, needle) =>
    (hay || '').toString().toLowerCase().includes((needle || '').toLowerCase());

  const meetsType = (ev, type) => {
    if (!type) return true;
    const e = (ev.event || '').toLowerCase();
    switch (type) {
      case 'start':   return e.includes('start');
      case 'success': return e.includes('success');
      case 'health':  return e.includes('health');
      case 'rollback':return e.includes('rollback');
      default: return true;
    }
  };

  const bust = () => `?t=${Date.now()}`;

  async function load() {
    try {
      liveDot.classList.remove('err','warn');
      // no-store + cache-bust
      const res = await fetch('news.json' + bust(), { cache: 'no-store' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      let data;
      try {
        data = await res.json();
        if (!Array.isArray(data)) throw new Error('JSON root is not an array');
      } catch (e) {
        throw new Error('JSON parse error: ' + e.message);
      }

      render(data);
      lastUpdated.textContent = new Date().toLocaleTimeString('de-DE') + ' Uhr';
      liveDot.classList.remove('warn','err');
    } catch (err) {
      console.error(err);
      lastUpdated.textContent = 'Fehler beim Laden – ' + (err && err.message ? err.message : err);
      liveDot.classList.add('err');
    }
  }

  function render(items) {
    const needle = q.value.trim();
    const type = filter.value;
    const max = parseInt(limit.value, 10) || 50;

    // Filter + sort (newest first if data has ts)
    const filtered = items
      .filter((x) =>
        meetsType(x, type) &&
        (
          !needle ||
          textIncludes(x.summary, needle) ||
          textIncludes(x.event, needle)   ||
          textIncludes(x.agent, needle)
        )
      )
      .sort((a,b) => String(b.ts).localeCompare(String(a.ts)))
      .slice(0, max);

    list.innerHTML = '';
    if (!filtered.length) {
      const li = document.createElement('li');
      li.innerHTML = '<span class="badge b-info"></span><div><div class="meta">Keine Einträge gefunden.</div></div>';
      list.appendChild(li);
      return;
    }

    const frag = document.createDocumentFragment();
    for (const it of filtered) {
      const badge = document.createElement('span');
      const ico = iconFor(it.event, it.summary);
      badge.className = `badge ${ico==='ok'?'b-ok': ico==='warn'?'b-warn': ico==='err'?'b-err':'b-info'}`;

      const li = document.createElement('li');
      const body = document.createElement('div');

      const head = document.createElement('div');
      head.textContent = `[${it.ts}] ${it.summary || it.event || ''}`;

      const meta = document.createElement('div');
      meta.className = 'meta';
      meta.textContent = `${it.event || '—'} — ${it.agent || 'CI/CD'}`;

      body.appendChild(head);
      body.appendChild(meta);

      li.appendChild(badge);
      li.appendChild(body);
      frag.appendChild(li);
    }
    list.appendChild(frag);
  }

  function startTimer() {
    clearInterval(timer);
    timer = setInterval(load, REFRESH_MS);
  }

  // events
  [q, filter, limit].forEach(el => el.addEventListener('input', () => load()));
  refreshBtn.addEventListener('click', load);

  // initial
  load();
  startTimer();
})();
