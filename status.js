/* status.js – lädt news.json, filtert & rendert Liste, Auto-Refresh */
(() => {
  const $ = (sel) => document.querySelector(sel);
  const eventsEl = $("#events");
  const emptyEl = $("#empty");
  const errorEl = $("#error");
  const lastUpdEl = $("#last-upd");
  const liveDot = $("#live-dot");

  const qEl = $("#q");
  const typeEl = $("#type");
  const limitEl = $("#limit");
  const refreshEl = $("#refresh");

  let data = [];
  let timer = null;

  const STATUS = {
    "Deployment success": "ok",
    "Deploy start": "warn",
    "Healthcheck failed": "err",
    "Rollback": "warn"
  };

  function fmtTs(iso) {
    try {
      const d = new Date(iso);
      const z = (n) => String(n).padStart(2,"0");
      const y = d.getFullYear(), m = z(d.getMonth()+1), da = z(d.getDate());
      const h = z(d.getHours()), mi = z(d.getMinutes()), s = z(d.getSeconds());
      return `[${y}-${m}-${da}T${h}:${mi}:${s}Z]`;
    } catch { return iso; }
  }

  function badgeCls(ev) {
    return STATUS[ev] || "warn";
  }

  function render() {
    const q = qEl.value.trim().toLowerCase();
    const t = typeEl.value;
    const lim = parseInt(limitEl.value,10) || 50;

    const filtered = data.filter(it => {
      const hay = `${it.summary||""} ${it.event||""} ${it.agent||""}`.toLowerCase();
      const matchText = !q || hay.includes(q);
      const matchType = !t || (it.event === t);
      return matchText && matchType;
    }).slice(0, lim);

    eventsEl.innerHTML = "";
    if (filtered.length === 0) {
      emptyEl.hidden = false;
      return;
    } else {
      emptyEl.hidden = true;
    }

    const frag = document.createDocumentFragment();
    for (const it of filtered) {
      const li = document.createElement("li");
      li.className = "event";

      const ts = document.createElement("div");
      ts.className = "ts";
      ts.textContent = fmtTs(it.ts || it.time || "");
      li.appendChild(ts);

      const sum = document.createElement("div");
      sum.className = "summary";

      const badge = document.createElement("span");
      badge.className = `badge ${badgeCls(it.event)}`;
      badge.textContent = it.event || "Event";
      sum.appendChild(badge);

      const text = document.createElement("span");
      text.textContent = " " + (it.summary || it.message || "");
      sum.appendChild(text);

      const chips = document.createElement("div");
      chips.className = "chips";
      if (it.agent) {
        const c = document.createElement("span");
        c.className = "chip";
        c.textContent = `Agent: ${it.agent}`;
        chips.appendChild(c);
      }
      li.appendChild(sum);
      li.appendChild(chips);

      frag.appendChild(li);
    }
    eventsEl.appendChild(frag);
  }

  async function load() {
    errorEl.hidden = true;
    liveDot.style.opacity = "0.5";
    // cache-bust to avoid stale CDN cache
    const url = `news.json?cb=${Date.now()}`;
    try {
      const res = await fetch(url, {cache:"no-store"});
      if (!res.ok) throw new Error(res.statusText);
      const json = await res.json();
      if (Array.isArray(json)) {
        data = json;
      } else if (Array.isArray(json.items)) {
        data = json.items;
      } else {
        data = [];
      }
      lastUpdEl.textContent = new Date().toLocaleTimeString("de-DE");
      render();
    } catch (e) {
      console.error("news.json error", e);
      errorEl.hidden = false;
    } finally {
      liveDot.style.opacity = "1";
    }
  }

  function schedule() {
    if (timer) clearInterval(timer);
    const sec = parseInt(refreshEl.value,10);
    if (sec > 0) {
      timer = setInterval(load, sec * 1000);
    }
  }

  // wire up
  qEl.addEventListener("input", render);
  typeEl.addEventListener("change", render);
  limitEl.addEventListener("change", render);
  refreshEl.addEventListener("change", () => { schedule(); });

  // init
  load();
  schedule();
})();