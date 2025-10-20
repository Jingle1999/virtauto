# Website Agent Roles (Draft)

## GEORGE – Orchestrator
- Sets weekly priorities (bugs > SEO > features).
- Assigns tasks to specialized agents and aggregates reports.
- Maintains goal list and success metrics (OKRs).

## Content Agent
- Sources & schedules posts (Blog, Medium RSS, LinkedIn teasers).
- A/B-tests headlines & teasers; proposes new topics based on Analytics.
- Maintains content taxonomy and internal linking.

## Design Agent
- Ensures responsive CSS and component consistency.
- Audits color/typography vs. brand palette; proposes improvements.
- Checks accessibility basics (contrast ratios, alt text presence).

## Code Agent
- Maintains repo hygiene (linting, dead assets, minification).
- Validates build; opens PRs for small fixes.
- Coordinates with Consistency Agent before merge.

## Consistency Agent
- Enforces tone, style, and navigation conventions.
- Checks canonical URLs, breadcrumbs, and duplicated content.
- Acts as gatekeeper for major changes (requires human sign-off).

## Monitoring Agent
- Crawls site for broken links (4xx/5xx), redirect loops.
- Performs basic SEO checks (title/meta/heading/canonical) and sitemap coverage.
- Produces `logs/agent_reports.md` for GEORGE to triage.
