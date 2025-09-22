async function loadEvents() {
  try {
    const response = await fetch('news.json?_=' + new Date().getTime());
    const data = await response.json();
    const list = document.getElementById('events');
    list.innerHTML = '';

    data.slice(0, 20).forEach(event => {
      const li = document.createElement('li');
      let cssClass = '';
      let icon = '';

      if (event.event.includes('success')) { cssClass = 'event-success'; icon = '🟢'; }
      else if (event.event.includes('failed')) { cssClass = 'event-failed'; icon = '🔴'; }
      else if (event.event.includes('Rollback')) { cssClass = 'event-rollback'; icon = '🟡'; }
      else { icon = 'ℹ️'; }

      li.className = cssClass;
      li.textContent = `[${event.ts}] ${event.event} — ${event.agent} :: ${event.summary}`;
      li.prepend(icon + ' ');
      list.appendChild(li);
    });

    document.getElementById('status').textContent = '✅ Live aktualisiert';
  } catch (err) {
    document.getElementById('status').textContent = '⚠️ Fehler beim Laden';
  }
}

// Auto-Refresh alle 30 Sekunden
setInterval(loadEvents, 30000);
loadEvents();
