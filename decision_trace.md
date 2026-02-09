# decision_trace.md — industrymodel.html (AEO Stage 1) PR #523

## Summary
This change replaces `industrymodel.html` with **Patch 1** to align the page with **AEO Layer — Stage 1 (Bounded Domain)**:
- One domain: **Bodyshop Doorline (TVL)**
- One decision class: **Door Release Gate**
- One authority path: **Edge → Orchestrator → GEORGE → Guardian**
- Explicit, explainable **BLOCK** case
- **Decision-first, Audit-first, PR-driven** (no “OS/platform” claims)

---

## Change intent
**Why now**
- We need a visible, credible showcase that demonstrates *governed decision-making* (ALLOW/HOLD/BLOCK) before adding “value agents” (Content Agent, Knowledge Curator).
- `industrymodel.html` is positioned as the **first visible AEO node**, not the full virtauto OS.

**What this page is**
A machine-readable, decision-first “world model” slice for a BIW doorline, designed to:
- declare an industrial decision class
- show authority & governance constraints
- make BLOCK legitimate and explainable
- produce audit-grade trace objects

**What this page is not**
- Not a digital twin marketing demo
- Not an optimizer/simulator showcase
- Not a platform/OS claim
- Not a multi-domain roadmap

---

## Files changed
- `industrymodel.html` (full replacement)

No other files are intended to be modified.

---

## Decision graph (Stage 1)
**Decision Class:** `door_release_gate`  
**Domain:** `biw_doorline_tvl`  
**Outcomes:** `ALLOW | HOLD | BLOCK`

**Nodes**
1. **PROPOSE** — release proposal created with Door ID + ruleset version
2. **CHECK** — deterministic checks over evidence + constraints
3. **GOVERN** — authority/policy enforcement via GEORGE + Guardian
4. **VERDICT** — ALLOW/HOLD/BLOCK published (audit object)

---

## Governance & authority
**Authority path**
- **Edge:** generates signals / measurements (no policy authority)
- **Orchestrator:** assembles proposal and sequences checks
- **GEORGE:** enforces contracts/policies (governing layer)
- **Guardian:** blocks on violated invariants (no bypass)

**Non-negotiables enforced by narrative**
- No decision without trace
- No silent autonomy
- Fail-safe behavior on missing evidence (HOLD/BLOCK)

---

## Evidence model (minimal)
**Required evidence refs for release gate (Stage 5 example)**
- geometry scan ref (structured light / 3D)
- surface scan ref (line scan / surface vision)
- gap/flush measurement ref
- ruleset version

---

## BLOCK case (explicit)
**Trigger**
- Any required evidence missing/unverifiable (e.g., surface evidence ref unresolved)

**Expected outcome**
- `guardian_check = FAIL`
- `verdict = BLOCK`
- `door.state = HOLD`

**Reason**
- `missing_required_evidence:<type>`

---

## Acceptance criteria
✅ The page states clearly:
- “AEO Stage 1 / bounded decision space”
- “not the OS / not the platform / not a full world model core”
- decision-first + audit-first framing
- explicit authority path and BLOCK semantics

✅ The BLOCK case is:
- explicit
- explainable
- represented as a deterministic audit record (example JSON)

✅ No scope creep:
- no agent catalog promises
- no multi-domain expansion
- no “AI runs production” claims

---

## Risks & mitigations
**Risk:** Overpromising beyond Stage 1  
**Mitigation:** Tightened copy: single domain + single decision class + explicit non-claims

**Risk:** Page becomes “documentation only”  
**Mitigation:** Structured as executable/auditable decision artifact (decision graph + audit records)

---

## Rollback plan
Revert PR to restore previous `industrymodel.html` if:
- wording is too aggressive/weak for positioning,
- layout breaks on production,
- governance claims conflict with current repo contracts.

---

## PR metadata (suggested)
**Title:** `industrymodel: AEO Stage 1 bounded decision space + explicit BLOCK case`  
**Labels:** `governed, aeo-stage-1, showcase, industrymodel`  
**Review focus:**
1) scope discipline (Stage 1 only)  
2) clarity of decision class + authority path  
3) BLOCK semantics and audit object examples

