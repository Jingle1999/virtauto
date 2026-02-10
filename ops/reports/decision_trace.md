# Decision Trace – Content Publish BLOCK Example

**Trace ID:** `trace_content_publish_0001`  
**Decision Class:** CONTENT_PUBLISH  
**Spec Reference:** industrymodel.html#spec-v1  
**Status:** BLOCKED  

---

## Decision Intent
Publish updated website content to the public channel.

---

## Actors Involved
- Content Agent (request)
- GEORGE (orchestration & final decision)
- Guardian (policy enforcement)

---

## Decision Flow

1. **Route**  
   Publish request routed by GEORGE.

2. **Execute**  
   Content Agent prepared static publish plan.

3. **Guardian Check**  
   Policy `CONTENT_PUBLISH_GUARDIAN` applied.  
   All structural checks passed, but required decision trace documentation was missing.

4. **Finalize**  
   Decision blocked.  
   No content published.

---

## Block Reason
Required `decision_trace.md` update missing at time of submission.

---

## Outcome
BLOCKED  
No execution performed.

---

## Governance Principle Demonstrated
> No decision without trace.  
> No execution without explainability.
