(function () {
  async function loadStatus() {
    const badge = document.getElementById('deploy-badge');
    const info  = document.getElementById('deploy-info');

    // Fallback, falls Elemente fehlen
    if (!badge || !info) return;

    const setBadge = (bg, label) => {
      badge.style.background = bg;
      badge.textContent = label;
    };

    try {
      const res = await fetch('status.json', { cache: 'no-store' });
      if (!res.ok) throw new Error('status.json not found');
      const data = await res.json();

      // Statusfarben/-texte
      if (data.status === 'ok') {
        setBadge('#16a34a', 'Deployment OK'); // grün
      } else if (data.status === 'rollback') {
        setBadge('#dc2626', 'Rollback aktiv'); // rot
      } else if (data.status === 'deploying') {
        setBadge('#ca8a04', 'Deploy läuft…'); // gelb
      } else {
        setBadge('#6b7280', 'Status unbekannt'); // grau
      }

      // Zusatzinfos (Zeit, Commit, Notiz)
      const ts     = data.timestamp ? new Date(data.timestamp).toLocaleString() : '';
      const commit = data.commit ? String(data.commit).slice(0, 7) : '';
      const parts  = [];
      if (ts) parts.push(ts);
      if (commit) parts.push(commit);
      if (data.note) parts.push(data.note);
      info.textContent = parts.length ? `(${parts.join(' • ')})` : '';
    } catch (e) {
      // Kein status.json vorhanden oder Fehler -> neutraler Fallback
      setBadge('#6b7280', 'Status unbekannt');
      info.textContent = '';
      // console.warn('status.js:', e);
    }
  }

  loadStatus();
})();
