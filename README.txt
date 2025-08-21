virtauto — Layout Unification Package
=====================================

What’s inside
-------------
- contact.html         → New Contact page, styled to match Home
- blog.html            → Blog page pulling Medium posts via RSS → cards
- imprint.html         → Placeholder
- privacy.html         → Placeholder
- robots.txt           → With sitemap reference
- sitemap.xml          → Update whenever you add new pages
- styles_additions.css → Small, *additive* utilities (grid/cards/forms)
- partials/header.html → Header markup matching Home (menu order)
- partials/footer.html → Footer markup used on all pages

Important
---------
• Keep your existing Home (index.html) and Solutions (solutions.html) as-is.
• These pages already include a header with the correct look; if you want perfect
  parity, replace the <header>…</header> in Contact/Blog with `partials/header.html`.
• Do NOT overwrite solutions.html content (GEORGE etc. stays unchanged).

Hookup
------
1) Put all files into your repo web root.
2) Replace `YOUR_FORM_ID` in contact.html with your Formspree ID.
3) Ensure <link rel="stylesheet" href="/styles.css"> stays first, then add:
   <link rel="stylesheet" href="/styles_additions.css">
4) If you want a single source of truth for header/footer, use the partials
   in all pages.

SEO
---
Robots and sitemap included. Update sitemap when adding pages.

— Generated for Andreas Braun (virtauto®)
