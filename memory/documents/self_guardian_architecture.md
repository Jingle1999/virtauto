# Self-Guardian Architecture – virtauto.de

## 1. Role in the virtauto.OS ecosystem

The Self-Guardian is the protective nervous system of virtauto.de.  
Its core purpose is to **continuously verify, protect, and stabilize** the autonomous behaviour of the website.

It is not a content agent and not a deployment agent.  
The Self-Guardian acts as:

- **Security watchdog** – detects risky changes and enforces safeguards.  
- **Consistency guardian** – keeps conventions, structure and files in a valid state.  
- **Governance enforcer** – ensures that rules and policies are applied before changes go live.

In short: the Self-Guardian makes sure that virtauto.de can evolve **safely**.

---

## 2. High-level architecture

At a high level the Self-Guardian is built from four building blocks:

1. **Guardian Workflows (GitHub Actions)**  
   - Scheduled and event-based workflows that scan the repository.  
   - Execute checks for security, integrity, and policy compliance.  
   - Create or update Pull Requests with automated fixes or warnings.

2. **Policy & Governance Layer (YAML / rules)**  
   - Policy files that define what “good” looks like.  
   - Rules for paths, naming, security headers, status files, and agent metadata.  
   - Central place to evolve the guardrails of the system.

3. **Status & Telemetry Outputs**  
   - Structured status files (e.g. JSON / Markdown reports) written into the repo.  
   - Information is consumed by the **Self-Agent Dashboard** and the website header.  
   - Makes the internal health of the system visible to humans and agents.

4. **Human Review & Override**  
   - Every Guardian change still goes through protected branches and review gates.  
   - Humans can approve, reject or extend the automated suggestions.  
   - This keeps the system **aligned** instead of purely self-modifying.

---

## 3. Triggers & event flow

The Self-Guardian reacts to the following trigger types:

- **Scheduled scans**  
  - Run in regular intervals (e.g. hourly / daily).  
  - Re-validate security headers, key configuration files and status objects.  

- **On-push / on-pull-request**  
  - Reacts when new commits or PRs touch critical areas (config, security, status, memory).  
  - Validates that changes comply with the defined policies.  

- **Manual runs (emergency / debug)**  
  - Can be executed by a maintainer to force a complete check.  
  - Used for incident response or after bigger refactors.

**Flow (simplified):**

1. Trigger fires (schedule, push, PR or manual).  
2. Guardian workflow collects relevant files and configuration.  
3. Policies are loaded (security, governance, consistency rules).  
4. Checks are executed → results are classified into **OK / ISSUE / UNKNOWN**.  
5. Outputs are written:
   - Status JSON / Markdown report.  
   - Optional automated PRs with fixes or recommendations.  

---

## 4. Checks & responsibilities

The Self-Guardian focuses on a small but critical set of responsibilities:

### 4.1 Security & configuration checks

- Validate that required **security headers** are present in the deployed site.  
- Check that important configuration files are not removed or corrupted.  
- Guard access to critical workflows (deployment, rollback, content ingestion).  

### 4.2 Integrity & structure checks

- Ensure that important folders and files exist (status, memory, policies, agents).  
- Validate JSON / YAML structure where possible.  
- Detect broken references between index files and documents (e.g. memory index).  

### 4.3 Governance & policy checks

- Enforce branch protection and review-gate rules.  
- Verify that new automation or agents are registered in the correct registries.  
- Ensure that new content or knowledge entries include minimal metadata.

---

## 5. Outputs & integration points

The Self-Guardian writes information back into virtauto.de so that other components can use it:

- **Status files**  
  - Summaries of the latest scan: what passed, what failed, what is unknown.  
  - Used by the Self-Agent Dashboard and the status banner on the website.

- **Pull Requests**  
  - Automated PRs that adjust configuration, fix small issues, or add missing fields.  
  - PR titles and descriptions explain what was detected and what is being changed.  

- **Log & audit trail**  
  - History of Guardian activities that prove the autonomy and self-protection behaviour.  
  - Important for future customers, audits and compliance.

---

## 6. Failure modes & safeguards

Even the Guardian can fail – therefore it is designed with explicit safeguards:

- **Fail-closed on critical checks**  
  - For high-risk areas, failures block deployment until reviewed.  

- **Readable failure messages**  
  - Errors are written as human-readable explanations, not only machine logs.  

- **No direct writes to production without review**  
  - Guardian PRs still require human confirmation via protected branches.  

- **Emergency override**  
  - Maintainers can temporarily bypass non-critical checks in case of incidents.  

---

## 7. Roadmap – from V1.0 to advanced Self-Protection

The current Self-Guardian implementation already provides:

- Continuous scans of the repository.  
- Automated PRs for configuration and content.  
- Status integration into the Self-Agent dashboard.  

Planned extensions for future versions:

- Deeper **policy-as-code** coverage (more areas of the repo).  
- Integration with the **RAG Knowledge Layer** to explain Guardian decisions.  
- Tighter coupling with the **CDT Layer** so that long-term behaviour is tracked.  
- Risk-based scoring of changes to prioritize human attention.

---

## 8. Summary

The Self-Guardian is the **immune system** of virtauto.de.  
It combines:

- GitHub Actions workflows,  
- policy files and governance rules,  
- and visible status outputs  

to protect a live, agentic, autonomous website.

Without the Self-Guardian, virtauto.de would be “just another automated site”.  
With it, virtauto.de becomes a **self-observing, self-protecting digital organism**.
