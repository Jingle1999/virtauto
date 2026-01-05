/* virtauto — site.js
   Purpose: Mobile nav toggle + UX (close on outside / link click) + smooth anchor scroll.
*/

(function () {
  // ---------- Smooth scroll for in-page anchors ----------
  document.addEventListener('click', (e) => {
    const a = e.target.closest('a[href^="#"]');
    if (!a) return;

    const href = a.getAttribute('href');
    if (!href || href === '#') return;

    const el = document.querySelector(href);
    if (!el) return;

    e.preventDefault();
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });

    // If we clicked a menu link on mobile, close menu
    closeMenu();
  });

  // ---------- Mobile menu helpers ----------
  function getMenuEl() {
    // Prefer id="menu" (your pages use this)
    return document.getElementById('menu') || document.querySelector('nav.menu');
  }

  function getBurgerEl() {
    // Prefer .burger
    return document.querySelector('.burger');
  }

  function isMenuOpen(menuEl) {
    return !!menuEl && menuEl.classList.contains('open');
  }

  function setAriaExpanded(expanded) {
    const burger = getBurgerEl();
    if (burger) burger.setAttribute('aria-expanded', expanded ? 'true' : 'false');
  }

  function openMenu() {
    const menu = getMenuEl();
    if (!menu) return;
    menu.classList.add('open');
    setAriaExpanded(true);
    document.body.classList.add('menu-open');
  }

  function closeMenu() {
    const menu = getMenuEl();
    if (!menu) return;
    menu.classList.remove('open');
    setAriaExpanded(false);
    document.body.classList.remove('menu-open');
  }

  // Expose for inline onclick="toggleMenu()"
  window.toggleMenu = function toggleMenu(ev) {
    if (ev && typeof ev.preventDefault === 'function') ev.preventDefault();
    const menu = getMenuEl();
    if (!menu) return;

    if (isMenuOpen(menu)) closeMenu();
    else openMenu();
  };

  // ---------- Close menu when tapping outside ----------
  document.addEventListener('click', (e) => {
    const menu = getMenuEl();
    if (!menu) return;
    if (!isMenuOpen(menu)) return;

    const burger = getBurgerEl();

    const clickedInsideMenu = e.target.closest('#menu') || e.target.closest('nav.menu');
    const clickedBurger = burger && (e.target === burger || e.target.closest('.burger'));

    if (!clickedInsideMenu && !clickedBurger) {
      closeMenu();
    }
  });

  // ---------- Close on ESC ----------
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeMenu();
  });

  // ---------- On load: make sure aria-expanded exists ----------
  document.addEventListener('DOMContentLoaded', () => {
    const burger = getBurgerEl();
    if (burger && !burger.hasAttribute('aria-expanded')) {
      burger.setAttribute('aria-expanded', 'false');
    }
  });
})();
