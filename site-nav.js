
// virtauto site navigation injector
(function () {
  try {
    const style = document.createElement("style");
    style.textContent = `
      :root {
        --vt-bg: #0b1220;
        --vt-card: #121a2a;
        --vt-text: #e6eefc;
        --vt-muted: #9fb3d6;
        --vt-accent: #4cc9f0;
        --vt-accent-2: #12b886;
        --vt-border: #21304b;
      }
      #vt-nav {
        position: sticky; top: 0; z-index: 9999;
        background: linear-gradient(180deg, rgba(11,18,32,0.95), rgba(11,18,32,0.8));
        backdrop-filter: blur(6px);
        border-bottom: 1px solid var(--vt-border);
      }
      #vt-nav .vt-wrap {
        max-width: 1100px; margin: 0 auto; padding: 12px 16px;
        display: flex; align-items: center; gap: 14px;
      }
      #vt-nav a { color: var(--vt-text); text-decoration: none; }
      #vt-brand { display: flex; align-items: center; gap: 10px; font-weight: 800; letter-spacing: 0.3px; }
      #vt-brand .dot { width: 8px; height: 8px; border-radius: 50%; background: #12b886; box-shadow: 0 0 10px #12b886aa; }
      #vt-links { display: flex; gap: 18px; margin-left: auto; flex-wrap: wrap; }
      #vt-links a { padding: 6px 10px; border-radius: 8px; color: var(--vt-muted); transition: all .18s ease; border: 1px solid transparent; }
      #vt-links a:hover { color: var(--vt-text); border-color: var(--vt-border); background: #0f1728; }
      @media (max-width: 680px){ #vt-links { gap: 10px; } }
      body { scroll-padding-top: 64px; }
    `;
    const header = document.createElement("header");
    header.id = "vt-nav";
    header.innerHTML = `
      <div class="vt-wrap">
        <a id="vt-brand" href="/home.html" title="virtauto">
          <span class="dot"></span><span>virtauto</span>
        </a>
        <nav id="vt-links" aria-label="Hauptnavigation">
          <a href="/home.html">Home</a>
          <a href="/solutions.html">Solutions</a>
          <a href="/george.html">GEORGE</a>
          <a href="/contact.html">Kontakt</a>
          <a href="/" title="Status Dashboard">Status</a>
        </nav>
      </div>`;
    document.head.appendChild(style);
    document.body.prepend(header);
  } catch(e){ console.warn("vt-nav inject failed:", e); }
})();
