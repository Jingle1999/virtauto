// assets/site.js
// virtauto — site helpers (mobile nav + smooth scrolling)
// Drop-in: works with pages that use onclick="toggleMenu()" OR inline class toggles.

(function () {
  "use strict";

  function qs(sel, root = document) {
    return root.querySelector(sel);
  }

  function qsa(sel, root = document) {
    return Array.from(root.querySelectorAll(sel));
  }

  function getMenu() {
    // primary expected id
    const menu = qs("#menu");
    if (menu) return menu;

    // fallback: any nav.menu
    const fallback = qs("nav.menu");
    return fallback || null;
  }

  function getBurger() {
    // common: button.burger
    return qs("button.burger") || null;
  }

  function isOpen(menu) {
    return menu.classList.contains("open");
  }

  function openMenu(menu, burger) {
    menu.classList.add("open");
    if (burger) {
      burger.setAttribute("aria-expanded", "true");
      burger.setAttribute("aria-label", "Close menu");
    }
  }

  function closeMenu(menu, burger) {
    menu.classList.remove("open");
    if (burger) {
      burger.setAttribute("aria-expanded", "false");
      burger.setAttribute("aria-label", "Menu");
    }
  }

  function toggleMenuInternal() {
    const menu = getMenu();
    const burger = getBurger();
    if (!menu) return;

    if (isOpen(menu)) closeMenu(menu, burger);
    else openMenu(menu, burger);
  }

  // Expose for pages that call onclick="toggleMenu()"
  window.toggleMenu = toggleMenuInternal;

  // Smooth anchor scrolling (keep your original behavior, but safer)
  document.addEventListener("click", (e) => {
    const a = e.target.closest('a[href^="#"]');
    if (!a) return;

    const href = a.getAttribute("href");
    if (!href || href === "#") return;

    const el = qs(href);
    if (!el) return;

    e.preventDefault();
    el.scrollIntoView({ behavior: "smooth", block: "start" });

    // if user tapped an anchor from the mobile menu, close it
    const menu = getMenu();
    const burger = getBurger();
    if (menu && isOpen(menu)) closeMenu(menu, burger);
  });

  // Make burger work even if inline onclick is missing/broken
  document.addEventListener("DOMContentLoaded", () => {
    const burger = getBurger();
    const menu = getMenu();
    if (!menu) return;

    // normalize burger ARIA
    if (burger) {
      if (!burger.hasAttribute("aria-expanded")) burger.setAttribute("aria-expanded", "false");
      // ensure click handler exists (in addition to any inline onclick)
      burger.addEventListener("click", (e) => {
        // let inline run too, but we ensure it works regardless
        // avoid double toggle if inline already toggles "open"
        // by toggling in next tick based on computed state change:
        setTimeout(() => {
          // if inline already toggled, do nothing; else toggle
          const nowOpen = isOpen(menu);
          // We can't detect intent reliably, but this keeps behavior stable:
          // If menu didn't change within the tick, toggle it.
          // We approximate by toggling only if menu is still closed AND burger press happened.
          // Simpler: just ensure it's open/closed by toggling once:
          // However that may double-toggle. So we do a conservative check:
          // If menu is closed AND burger aria-expanded is false -> toggle open
          // If menu is open AND burger aria-expanded is true -> do nothing
          const aria = burger.getAttribute("aria-expanded");
          const ariaOpen = aria === "true";
          if (nowOpen !== ariaOpen) {
            // sync ARIA to real state
            if (nowOpen) openMenu(menu, burger);
            else closeMenu(menu, burger);
          } else {
            // state didn’t change, so toggle ourselves
            toggleMenuInternal();
          }
        }, 0);
      });
    }

    // Close menu when clicking outside (mobile)
    document.addEventListener("click", (e) => {
      const m = getMenu();
      const b = getBurger();
      if (!m || !b) return;
      if (!isOpen(m)) return;

      const clickedInsideMenu = e.target.closest("#menu") || e.target.closest("nav.menu");
      const clickedBurger = e.target.closest("button.burger");
      if (!clickedInsideMenu && !clickedBurger) closeMenu(m, b);
    });

    // ESC closes menu
    document.addEventListener("keydown", (e) => {
      if (e.key !== "Escape") return;
      const m = getMenu();
      const b = getBurger();
      if (m && isOpen(m)) closeMenu(m, b);
    });

    // On resize to desktop, close menu (avoids stuck open states)
    window.addEventListener("resize", () => {
      const m = getMenu();
      const b = getBurger();
      if (!m) return;
      if (window.innerWidth > 992 && isOpen(m)) closeMenu(m, b);
    });
  });
})();

