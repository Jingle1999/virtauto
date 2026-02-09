# Decision Trace for PR #521

## Decision / Intent
Make the Production Planning demo UI resilient and governance-aligned by:
- Loading data **API-first** (local dev), and
- Falling back to **static, versioned demo artifacts** when the API is unavailable.

The UI remains **read-only** and does not simulate operations client-side.

## Authority
Repository maintainer.

## Scope (files/modules touched)
- assets/js/demo-production-planning.js

## Context
The production-planning showcase must reliably render a governed decision space in the browser.
In practice, the local API endpoint may not be available (e.g., GitHub Pages, offline demos, shared links).
Without a deterministic fallback, the UI would fail or degrade unpredictably, harming the credibility of the governed demo.

Key constraints:
- No privileged writes from the browser.
- No hidden “simulation” or client-side timers that fabricate state.
- Deterministic behavior across environments (dev vs. static hosting).

## Considered Options
1) **API-only (hard dependency)**
   - Rejected: breaks on static hosting and reduces demo reliability.

2) **Static-only (no API integration)**
   - Rejected: blocks local iteration and removes the intended “API-first” integration path.

3) **API-first with deterministic static fallback**
   - Chosen: keeps the dev workflow, ensures the hosted demo always renders, and preserves truthfulness (read-only rendering).

## Decision
Adopt **API-first + static fallback** loading strategy in `assets/js/demo-production-planning.js`:
- Try fetch from `http://localhost:8000` first (dev convenience).
- On failure, load from static demo files under `assets/demo/production-planning`.
- Use cache-busting (`?t=`) to avoid stale reads during iteration.
- Keep rendering logic read-only; no generated operations or fabricated state in the browser.

## Expected Outcome
- The demo renders reliably on GitHub Pages and other static hosts.
- Local development continues to use the API when available.
- The showcased decision state remains auditable and consistent with governed artifacts.
- Failures are handled deterministically (fallback), not silently “smoothed over.”

## Validation / How to Verify
1) **Static hosting test**
   - Open the page on GitHub Pages (no local API running).
   - Verify the UI loads data from the fallback demo files and renders without errors.

2) **Local dev test**
   - Start local API at `http://localhost:8000`.
   - Reload and confirm the UI uses API responses (and still renders correctly).

3) **Failure-path test**
   - Stop the API while the page is open and reload.
   - Confirm it falls back to static artifacts and still displays a coherent snapshot.

4) **Governance integrity**
   - Confirm no write endpoints are invoked from the browser.
   - Confirm the UI does not introduce simulated operations/timers to “fake” freshness or state.
