// assets/site.js
(() => {
  'use strict';

  const $ = (sel, root = document) => root.querySelector(sel);

  function getMenu() {
    return document.getElementById('menu') || $('.menu');
  }

  function getBurger() {
    return $('.burger');
  }

  function isSmallScreen() {
    // Align with your CSS intent; doesn't have to be perfect because toggling is unconditional
    return window.matchMedia('(max-width: 992px)').matches;
  }

  function setMenuOpen(open) {
    const menu = getMenu();
    const burger = getBurger();
    if (!menu) return;

    menu.classList.toggle('open', open);

    if (burger) {
      burger.setAttribute('aria-expanded', open ? 'true' : 'false');
      // optional accessibility wiring
      if (!burger.getAttribute('aria-controls')) {
        burger.setAttribute('aria-controls', menu.id || 'menu');
      }
    }
  }

  function toggleMenu() {
    const menu = getMenu();
    if (!menu) return;
    setMenuOpen(!menu.classList.contains('open'));
  }

  // 1) Smooth scroll for in-page anchors only (#...)
  document.addEventListener('click', (e) => {
    const a = e.target.closest('a[href^="#"]');
    if (!a) return;

    const href = a.getAttribute('href');
    if (!href || href === '#' || href === '#!') return;

    const el = document.querySelector(href);
    if (!el) return;

    e.preventDefault();
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });

  // 2) Mobile nav wiring
  function wireMobileNav() {
    const burger = getBurger();
    const menu = getMenu();

    // Avoid double-binding when header is injected after initial load
    if (burger && burger.dataset && burger.dataset.wired === '1') return;


    if (burger) {
      burger.type = 'button';
      burger.setAttribute('aria-label', burger.getAttribute('aria-label') || 'Menu');
      burger.setAttribute('aria-expanded', 'false');
      burger.dataset.wired = '1';

      burger.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation(); // IMPORTANT: prevents "click outside" from firing on same tap
        toggleMenu();
      });
    }

    if (menu) {
      // Clicking inside menu should not count as "outside"
      menu.addEventListener('click', (e) => {
        e.stopPropagation();

        // On small screens: close after choosing a link
        const link = e.target.closest('a');
        if (link && isSmallScreen()) {
          setMenuOpen(false);
        }
      });
    }

    // Click outside closes menu (when open)
    document.addEventListener('click', () => {
      const menuEl = getMenu();
      if (!menuEl) return;
      if (!menuEl.classList.contains('open')) return;

      setMenuOpen(false);
    });

    // On resize to desktop: ensure menu isn't stuck in open-state
    window.addEventListener(
      'resize',
      () => {
        if (!isSmallScreen()) setMenuOpen(false);
      },
      { passive: true }
    );
  
  }

  document.addEventListener('DOMContentLoaded', wireMobileNav);
  window.addEventListener('virtauto:header-mounted', wireMobileNav);
})();
