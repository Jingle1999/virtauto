// assets/site.js — unified, defensive, works on every page
document.addEventListener('DOMContentLoaded', () => {
  const menu   = document.getElementById('menu');
  const burger = document.querySelector('.burger');

  const isOpen = () => menu && menu.classList.contains('open');
  const open   = () => menu && menu.classList.add('open');
  const close  = () => menu && menu.classList.remove('open');
  const toggle = () => (isOpen() ? close() : open());

  // 1) Mobile nav toggle
  if (burger && menu) {
    burger.addEventListener('click', (e) => {
      e.preventDefault();
      toggle();
    });

    // Close menu when clicking a link inside (mobile UX)
    menu.addEventListener('click', (e) => {
      const link = e.target.closest('a');
      if (link) close();
    });

    // Close menu when clicking outside
    document.addEventListener('click', (e) => {
      if (!isOpen()) return;
      const clickedBurger = e.target.closest('.burger');
      const clickedMenu   = e.target.closest('#menu');
      if (!clickedBurger && !clickedMenu) close();
    });

    // Close on Escape
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') close();
    });
  }

  // 2) Smooth scroll for anchor links (#...)
  document.addEventListener('click', (e) => {
    const a = e.target.closest('a[href^="#"]');
    if (!a) return;

    const href = a.getAttribute('href');
    if (!href || href === '#') return;

    const el = document.querySelector(href);
    if (!el) return;

    e.preventDefault();
    el.scrollIntoView({ behavior: 'smooth' });
  });
});
