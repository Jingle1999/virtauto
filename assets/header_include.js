// assets/header_include.js
(() => {
  'use strict';

  const HEADER_URL = '/partials/header.html';

  function normalizePath(pathname) {
    // strip trailing slash except root
    if (pathname.length > 1 && pathname.endsWith('/')) return pathname.slice(0, -1);
    return pathname;
  }

  function navKeyFromPath(pathname) {
    const p = normalizePath(pathname);
    if (p === '' || p === '/') return 'home';
    if (p === '/index.html' || p === '/home.html') return 'home';
    if (p.endsWith('/agents.html') || p.endsWith('/self-agents.html')) return 'agents';
    if (p.endsWith('/architecture.html')) return 'architecture';
    if (p.endsWith('/industrymodel.html')) return 'industry';
    if (p === '/status' || p.startsWith('/status/')) return 'status';
    if (p.endsWith('/contact.html')) return 'contact';
    if (p.endsWith('/solutions.html') || p.endsWith('/use-cases.html') || p.endsWith('/usecases.html')) return 'solutions';
    return null;
  }

  function setActiveNav(root) {
    const key = navKeyFromPath(window.location.pathname);
    if (!key) return;

    const links = root.querySelectorAll('a[data-nav]');
    links.forEach(a => a.classList.remove('active'));

    // Prefer direct match
    const direct = root.querySelector(`a[data-nav="${key}"]`);
    if (direct) {
      direct.classList.add('active');
      return;
    }

    // Fallback: match by href pathname
    const norm = normalizePath(window.location.pathname);
    links.forEach(a => {
      try {
        const u = new URL(a.getAttribute('href'), window.location.origin);
        if (normalizePath(u.pathname) === norm) a.classList.add('active');
      } catch (_) {}
    });
  }

  async function mountHeader() {
    const mount = document.getElementById('site-header');
    if (!mount) return;

    try {
      const res = await fetch(`${HEADER_URL}?v=${Date.now()}`, { cache: 'no-store' });
      if (!res.ok) throw new Error(`Header fetch failed: ${res.status}`);
      const html = await res.text();
      mount.innerHTML = html;
      setActiveNav(mount);
      window.dispatchEvent(new Event('virtauto:header-mounted'));
    } catch (err) {
      // Fail open: do not block page render
      console.warn('[header] include failed', err);
    }
  }

  // Defer scripts run before DOMContentLoaded, so mount happens early enough for site.js wiring.
  mountHeader();
})();
