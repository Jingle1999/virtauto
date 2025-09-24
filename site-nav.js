// Inject a single top navigation bar. If one already exists, do nothing.
(function () {
  if (document.getElementById('virtauto-topnav')) return;

  const nav = document.createElement('header');
  nav.id = 'virtauto-topnav';
  nav.innerHTML = `
    <style>
      #virtauto-topnav {
        position: sticky; top: 0; z-index: 9999;
        background: #0f172a; color: #e2e8f0; border-bottom: 1px solid #1f2937;
        font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
      }
      #virtauto-topnav .wrap {
        max-width: 1120px; margin: 0 auto; display:flex; align-items:center; gap:24px;
        padding: 10px 16px;
      }
      #virtauto-topnav a { color: #e2e8f0; text-decoration: none; padding: 6px 10px; border-radius: 8px; }
      #virtauto-topnav a:hover { background:#1f2937; }
      #virtauto-topnav .brand { font-weight:700; letter-spacing:.2px; margin-right:6px; }
      #virtauto-topnav .spacer { flex: 1 1 auto; }
      #virtauto-topnav .active { background:#334155; }
    </style>
    <div class="wrap">
      <a class="brand" href="home.html">virtauto</a>
      <nav class="links" aria-label="Hauptnavigation">
        <a href="home.html" data-id="home">Home</a>
        <a href="solutions.html" data-id="solutions">Solutions</a>
        <a href="george.html" data-id="george">GEORGE</a>
        <a href="contact.html" data-id="contact">Kontakt</a>
        <a href="index.html" data-id="dashboard">Status</a>
      </nav>
      <div class="spacer"></div>
    </div>
  `;
  document.body.prepend(nav);

  // Activate current link by simple URL match
  const map = {
    'home.html': 'home',
    'solutions.html': 'solutions',
    'george.html': 'george',
    'contact.html': 'contact',
    'index.html': 'dashboard'
  };
  const path = (location.pathname.split('/').pop() || 'index.html');
  const id = map[path] || null;
  if (id) {
    const el = document.querySelector(`#virtauto-topnav a[data-id="${id}"]`);
    if (el) el.classList.add('active');
  }
})();
