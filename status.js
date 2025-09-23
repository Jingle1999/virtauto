async function loadStatus() {
  try {
    const response = await fetch('news.json?_=' + new Date().getTime());
    const data = await response.json();
    const filter = document.getElementById('filter').value.toLowerCase();
    const list = document.getElementById('statusList');
    list.innerHTML = '';
    data.slice(0, 50).forEach(item => {
      const text = `[${item.ts}] ${item.event} — ${item.agent} :: ${item.summary}`;
      if (text.toLowerCase().includes(filter)) {
        const li = document.createElement('li');
        if (item.event.includes('Deploy start')) li.className = 'yellow';
        else if (item.event.includes('Deployment success')) li.className = 'green';
        else if (item.event.includes('Rollback')) li.className = 'yellow';
        else if (item.event.includes('Healthcheck failed')) li.className = 'red';
        li.textContent = text;
        list.appendChild(li);
      }
    });
  } catch (e) {
    console.error('Fehler beim Laden der Statusdaten:', e);
  }
}
document.getElementById('filter').addEventListener('input', loadStatus);
setInterval(loadStatus, 30000);
loadStatus();