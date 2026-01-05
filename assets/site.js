// assets/site.js
// - Smooth scroll for in-page anchors
// - Mobile navigation: burger toggles #menu.open across all pages
// - Close menu on link click, outside click, ESC, and when switching to desktop

(function () {
  "use strict";

  function $(sel, root = document) {
    return root.querySelector(sel);
  }
  function $all(sel, root = document) {
    return Array.from(root.querySelectorAll(sel));
  }

  function getMenu() {
    // works with <nav id="menu" class="menu">...</nav>
    return document.getElementById("menu") || $(".menu");
  }

  function getBurger() {
    return $(".burger");
  }

  function isMenuOpen(menu) {
    return menu && menu.classList.contains("open");
  }

  function setMenuOpen(open) {
    const menu = getMenu();
    const burger = getBurger();
    if (!menu) return;

    menu.classList.toggle("open", !!open);

    if (burger) {
      burger.setAttribute("aria-expanded", open ? "true" : "false");
      // Optional: aria-controls is helpful for accessibility
      if (!burger.getAttribute("aria-controls")) burger.setAttribute("aria-controls", "menu");
    }
  }

  function toggleMenu() {
    const menu = getMenu();
    if (!menu) return;
    setMenuOpen(!isMenuOpen(menu));
  }

  function isMobile() {
    // keep aligned with your CSS breakpoint for mobile nav
    return window.matchMedia("(max-width: 992px)").matches;
  }

  // --- Smooth scroll for in-page anchors (#...)
  document.addEventListener("click", (e) => {
    const a = e.target.closest('a[href^="#"]');
    if (!a) return;

    const href = a.getAttribute("href");
    if (!href || href === "#") return;

    const el = document.querySelector(href);
    if (!el) return;

    e.preventDefault();
    el.scrollIntoView({ behavior: "smooth", block: "start" });

    // if a click happens inside the mobile menu, close it after navigating
    if (isMobile()) setMenuOpen(false);
  });

  document.addEventListener("DOMContentLoaded", () => {
    const burger = getBurger();
    const menu = getMenu();

    if (burger) {
      // Ensure button doesn't submit forms etc.
      burger.type = "button";

      // Ensure ARIA
      burger.setAttribute("aria-label", burger.getAttribute("aria-label") || "Menu");
      burger.setAttribute("aria-expanded", "false");
      if (!burger.getAttribute("aria-controls")) burger.setAttribute("aria-controls", "menu");

      // Toggle on burger click
      burger.addEventListener("click", (e) => {
        e.preventDefault();
        toggleMenu();
      });
    }

    // Close menu when clicking a normal navigation link (page navigation)
    // (not only #anchors; this covers links to agents.html etc.)
    if (menu) {
      $all("a[href]", menu).forEach((link) => {
        link.addEventListener("click", () => {
          if (isMobile()) setMenuOpen(false);
        });
      });
    }

    // Close menu on outside click (mobile only)
    document.addEventListener("click", (e) => {
      if (!isMobile()) return;
      const menuEl = getMenu();
      if (!menuEl || !isMenuOpen(menuEl)) return;

      const burgerEl = getBurger();
      const clickedInsideMenu = e.target.closest("#menu") || e.target.closest(".menu");
      const clickedBurger = burgerEl && (e.target === burgerEl || e.target.closest(".burger"));

      if (!clickedInsideMenu && !clickedBurger) setMenuOpen(false);
    });

    // Close on ESC
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") setMenuOpen(false);
    });

    // If viewport becomes desktop, ensure menu isn't stuck in "open"
    window.addEventListener("resize", () => {
      if (!isMobile()) setMenuOpen(false);
    });
  });

  // Expose a global helper (optional, keeps compatibility if any page still calls toggleMenu())
  window.toggleMenu = toggleMenu;
})();
