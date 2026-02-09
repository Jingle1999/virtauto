# Decision Contract v1  
## Production Planning — Door Release after Quality Gate (Stage 5)

---

## 1. Purpose

This contract defines a **bounded, governable decision** for a single industrial domain:

> **Decision:**  
> *May a BIW Door (TVL – Front Left) be released after the Quality Gate (Stage 5)?*

The contract is **decision-first**, **audit-first**, and **block-capable**.  
It does **not** optimize, predict, or execute production actions.

---

## 2. Decision Scope

- **Domain:** Bodyshop → Doorline FL (TVL)
- **Decision Class:** Door Release after Quality Gate
- **Stage:** 5 (Geometry & Surface)
- **Outcome Space:**  
  - `ALLOW`  
  - `HOLD`  
  - `BLOCK`

This contract governs **admissibility**, not execution.

---

## 3. Decision Intent

```json
{
  "decision_id": "pp-door-release-v1",
  "intent": "Release door after quality gate only if complete evidence exists",
  "stage": 5
}
