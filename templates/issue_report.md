# [GEORGE] Site Health Report

**Date:** {{DATE}}

## Summary
- Lighthouse (avg over URLs):
  - Performance: {{LH_PERF}}
  - Accessibility: {{LH_A11Y}}
  - Best Practices: {{LH_BP}}
  - SEO: {{LH_SEO}}
- Broken links: {{BROKEN_LINKS}}
- Security headers (sample): see details below

> Gates: perf ≥ {{G_PERF}}, a11y ≥ {{G_A11Y}}, bp ≥ {{G_BP}}, seo ≥ {{G_SEO}}

---

## Lighthouse per URL
{{LH_TABLE}}

## Broken Links
{{LYCHEE_OUTPUT}}

## Security Headers (sample)
{{HEADERS_OUTPUT}}

---

_This issue was created by GEORGE Orchestrator._
