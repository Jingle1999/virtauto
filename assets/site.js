/* assets/site.js
   - Smooth scroll for in-page anchors
   - Mobile navigation: burger toggles #menu /.menu open across all pages
*/

(() => {
  'use strict';

  const $  = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  function getMenu() {
    // your markup uses <nav class="menu" id="menu"> on all pages
    return $('#menu') || $('.menu');
  }

  function getBurger() {
    return $('.burger');
  }

  function isMobile() {
    // match your CSS breakpoint (styles_unify.css uses 992px)
    return window.matchMedia('(max-width: 992px)').matches;
  }

  function setMenuOpen(open) {
    const menu = getMenu();
    const burger = getBurger();
    if (!menu) return;

    menu.classList.toggle('open', open);

    if (burger) {
      burger.setAttribute('aria-expanded', open ? 'true' : 'false');
      // optional linkage for a11y
      if (!burger.getAttribute('aria-controls') && menu.id) {
        burger.setAttribute('aria-controls', menu.id);
      }
    }
  }

  function toggleMenu() {
    const menu = getMenu();
    if (!menu) return;
    setMenuOpen(!menu.classList.contains('open'));
  }

  // 1) Smooth scroll for in-page anchors (#...)
  document.addEventListener('click', (e) => {
    const a = e.target.closest('a[href^="#"]');
    if (!a) return;

    const href = a.getAttribute('href');
    if (!href || href === '#') return;

    const el = document.querySelector(href);
    if (!el) return;

    e.preventDefault();
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });

  // 2) Mobile nav wiring
  document.addEventListener('DOMContentLoaded', () => {
    const burger = getBurger();
    const menu = getMenu();

    if (burger) {
      burger.type = 'button';
      burger.setAttribute('aria-label', burger.getAttribute('aria-label') || 'Menu');
      burger.setAttribute('aria-expanded', 'false');

      burger.addEventListener('click', (e) => {
        e.preventDefault();
        toggleMenu();
      });
    }

    // Close after navigating (only on mobile)
    if (menu) {
      menu.addEventListener('click', (e) => {
        const link = e.target.closest('a');
        if (!link) return;
        if (isMobile()) setMenuOpen(false);
      });
    }

    // Click outside closes (mobile)
    document.addEventListener('click', (e) => {
      if (!isMobile()) return;

      const menuEl = getMenu();
      if (!menuEl || !menuEl.classList.contains('open')) return;

      const burgerEl = getBurger();
      const clickedInsideMenu = menuEl.contains(e.target);
      const clickedBurger = burgerEl && burgerEl.contains(e.target);

      if (!clickedInsideMenu && !clickedBurger) {
        setMenuOpen(false);
      }
    });

    // Resize to desktop => ensure menu isn't stuck open
    window.addEventListener('resize', () => {
      if (!isMobile()) setMenuOpen(false);
    }, { passive: true });
  });
})();
