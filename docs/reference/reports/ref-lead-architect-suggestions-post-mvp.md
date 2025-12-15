---
type: reference
id: REF-lead-architect-suggestions-post-mvp
title: "Skriptoteket Post-MVP Architecture Review"
status: active
owners: "agents"
created: 2025-12-15
topic: "architecture"
---

## Executive Summary

Skriptoteket's architecture is already set up for a clean post-MVP evolution: protocol-first DDD/Clean Architecture, clear bounded contexts (catalog, identity, suggestions, scripting), and an explicit DI composition root make deferred items straightforward to add without structural rewrites. The most "natural" next two epics are (1) finishing real-world identity/governance and adding operational visibility, followed by (2) scaling and hardening execution through policy, queueing, and runner isolation.

---

## Current Architecture Assessment

### Strengths

- **Strong separation of concerns with clear dependency direction.** The repo consistently leans on protocols (`typing.Protocol`) for repositories and handlers, with an explicit Dishka composition root wiring implementations (`di.py`). This supports testability, swap-in integrations (SSO, runner service), and avoids framework bleed into domain logic.
- **Well-formed scripting domain foundations.** The scripting domain models and state transitions (draft → in_review → active → archived) are explicit and immutable, with copy-on-activate publishing semantics and a stable runner contract defined (`result.json`, contract_version, artifact safety rules). This is the correct base for future scaling (queue/worker) without changing business invariants.
- **Pragmatic "MVP-safe" execution policy for v0.1.** ADR-0016's global concurrency cap + reject behavior avoids hidden queues and prevents event-loop blocking when Docker SDK calls are thread-offloaded. It is operationally safe for early adoption and sets a clear upgrade path to persistent queueing later.
- **Federation-ready identity model.** Identity already anticipates external identities (`auth_provider`, `external_id`) while keeping roles local, which makes HuleEdu SSO an additive change rather than a rewrite.

### Areas of Concern and Technical Debt

- **Operational/security debt around execution remains the dominant risk.** v0.1 accepts docker.sock access for sibling runner containers (explicitly noted as "acceptable for v0.1 only"), but that remains the largest blast-radius lever until a dedicated runner boundary exists.
- **Policy gaps for "real-world tools."** Two practical capabilities are explicitly deferred because there is no policy model yet:
  - per-tool **network enablement** (default `--network none`)
  - per-tool **secrets injection**

  These need a first-class execution policy model before they are implemented safely.
- **Retention/data-handling is not fully formalized.** The hybrid storage ADR proposes DB logs + filesystem artifacts and mentions different sandbox vs production retention defaults, but the "source of truth" retention policy and the operational cleanup mechanism need to be formalized and enforced. This is both an ops and privacy/compliance issue in a school setting.
- **User-facing reliability under load will eventually require async execution.** The current cap+reject approach is correct for early safety, but it will become user-hostile as adoption increases ("runner busy" retries) and is incompatible with truly long-running scripts unless you accept HTTP timeouts and poor UX.

### Cross-Cutting Risk Assessment (Post-MVP)

If deferred items are implemented in the wrong order, the main risks are:

1. **Security regression** (network/secrets added without a policy model + auditing + sanitization hardening).
2. **Operational instability** (queue introduced without clear scheduling/fairness/backpressure semantics).
3. **Compliance risk** (artifact/input retention defaults not explicit; inability to purge sensitive inputs/outputs predictably).
4. **Identity confusion** (SSO account-linking mistakes leading to wrong-user access if matching rules are not explicit).

---

## EPIC-05: Identity Federation and Operational Readiness

### EPIC-05 Outcome

Skriptoteket is "production-ready for a real school environment": users authenticate via HuleEdu SSO (while keeping local roles), admin governance (nomination/approval) is complete, and operators/admins have baseline visibility and controls (metrics + retention/cleanup) to run the platform safely day-to-day.

### EPIC-05 Proposed Stories

#### ST-05-01: HuleEdu SSO Integration (Federated Identity, Local Authorization)

- Implement HuleEdu login flow behind protocols consistent with ADR-0011: external identity provider supplies identity; Skriptoteket assigns/maintains roles locally.
- Recommended implementation shape (fits current architecture):
  - Add an `OidcProviderProtocol` (or `FederatedAuthProviderProtocol`) in `protocols/identity.py`.
  - Implement `HuleEduOidcProvider` in infrastructure.
  - Add a dedicated handler (e.g., `BeginOidcLoginHandler`, `CompleteOidcLoginHandler`) that creates a standard Skriptoteket server-side session after successful OIDC callback.
  - JIT provisioning rules (explicit and testable): if `(auth_provider=HULEEDU, external_id)` not found, create user with role `user` and `is_active=true`, leaving role promotion to admins/superusers.
- Deliverable UX: "Login with HuleEdu" button, plus local login for break-glass admin/superuser accounts.

#### ST-05-02: External Account Linking and Safe Matching Rules

- Add an explicit admin UI/workflow for:
  - viewing a user's `auth_provider` + `external_id`
  - linking/unlinking external identity (if you allow merges)
  - disabling accounts (`is_active=false`)
- Formalize matching rule: prefer immutable `external_id` as primary; treat email as informational (emails can change).

#### ST-05-03: Admin Nomination and Superuser Approval (Complete Governance Loop)

- Implement ST-02-02 as designed: nomination record (nominator, nominee, rationale, timestamp) + superuser decision record (approve/deny with actor/time), following the same append-only decision pattern used in suggestions.
- Include minimal UI:
  - Admin: "Nominate user for admin" (with rationale)
  - Superuser: "Pending nominations" list + approve/deny actions
- Add audit logging for role changes (even if stored as decision records in DB, the UI should show actor/time).

#### ST-05-04: Ops Dashboard v1 (Metrics and Operational Visibility)

- Provide an admin-facing dashboard derived from existing data (no Kafka required):
  - runs per day/week, success/failure/timeout rates
  - average duration (p50/p95 approximations)
  - top tools by runs
  - runner saturation indicators (count of "runner busy" rejections, if tracked)
- This directly addresses the "metrics/analytics dashboard deferred" note while staying consistent with "defer Kafka until needed."

#### ST-05-05: Artifact Retention and Cleanup Enforcement (Sandbox vs Production)

- Convert the retention intent into enforceable behavior:
  - explicit settings for sandbox vs production retention windows
  - a scheduled cleanup job (in-app background task or external cron) that prunes artifacts deterministically
  - explicit policy for production input files (default: do not retain), consistent with the hybrid storage ADR's intent
- Add admin "purge run" / "purge artifacts for run" capability for incident response and privacy requests.

#### ST-05-06: Baseline Security and Operational Hardening for Identity

- Close the gap between "MVP identity" and "school-safe identity":
  - secure cookie defaults by environment (COOKIE_SECURE true in production)
  - CSRF enforcement for state-changing form posts (sessions already carry CSRF token fields)
  - login rate limiting / lockout policy (even minimal) to reduce brute-force risk
  - session revocation UX (admin can revoke all sessions for a user)
- This aligns with ADR-0009's baseline security expectations for session auth.

### EPIC-05 Dependencies and Risks

#### EPIC-05 Dependencies

- Identity protocols and session-based auth foundations (already present)
- Clear "roles remain local" rule (ADR-0011)
- Run tracking persistence (tool_runs) to compute dashboard metrics

#### EPIC-05 Risks

- **Account matching mistakes** (email-based merges): mitigate by using immutable `external_id` as primary key and making linking explicit/admin-mediated.
- **Operational drift** (cleanup not actually running): mitigate by making retention observable (dashboard shows disk usage/oldest artifact age).
- **Security regressions** (SSO misconfiguration): mitigate via strict configuration validation at startup and integration tests against a mocked OIDC provider.

---

## EPIC-06: Execution Scale and Security Hardening

### EPIC-06 Outcome

Tool execution becomes robust under increased usage and stricter security needs: long-running runs don't require an interactive HTTP request, execution capabilities are governed by per-tool policy (network/secrets), and runner isolation reduces blast radius beyond the v0.1 docker.sock acceptance.

### EPIC-06 Proposed Stories

#### ST-06-01: Persistent Async Execution Queue (Supersede Cap+Reject Where Appropriate)

- Introduce a durable job model (PostgreSQL-backed) for production runs:
  - `tool_run_jobs` table (queued/running/succeeded/failed/timed_out/cancelled)
  - worker loop uses `SELECT … FOR UPDATE SKIP LOCKED` to claim jobs safely
  - explicit concurrency and fairness semantics (per-user and global caps)
- UI/UX:
  - POST run returns immediately with `run_id` and a "queued/running" page
  - user page polls for completion (HTMX partial refresh fits the server-driven UI style)
- Keep ADR-0016's cap+reject behavior as a fallback mode for sandbox or for deployments that disable workers.

#### ST-06-02: Dedicated Runner Service Boundary (Reduce docker.sock Blast Radius)

- Move Docker engine access out of the web app process/container:
  - Web app calls a Runner Service via a narrow protocol (`ToolRunnerProtocol` already anticipated in EPIC-04 docs).
  - Runner service holds docker.sock access; web app no longer needs it.
  - Maintain the same runner contract (`result.json`) to preserve compatibility and testability.
- Deployment: introduces a second container (runner) but stays within the "single system" monolith principle at the product level.

#### ST-06-03: Per-Tool Execution Policy Model (Network Enablement + Resource Overrides)

- Add an explicit domain model and persistence for execution policy, minimally:
  - `network_enabled: bool` (default false)
  - resource caps overrides (timeout/cpu/memory), bounded by global operator-defined maximums
  - optionally: allowed file types / max upload size per tool
- Governance rule recommendation:
  - enabling network is **admin-only** with optional superuser approval (configurable), because it materially increases exfiltration risk.

#### ST-06-04: Per-Tool Secrets Management and Injection

- Model secrets as named values attached to a tool/version/policy scope:
  - "tool secrets" (stable across versions) is usually the right level
  - injected as environment variables or a mounted file in `/work/secrets/…`
- Security properties required:
  - encryption at rest (application-level encryption or external secret store integration)
  - secrets never rendered in UI, never included in logs, never included in `error_summary`
  - audit trail for create/update/delete/rotation
- Permission model:
  - admin can manage secrets for their tools; superuser can view audit and revoke/rotate.

#### ST-06-05: Runner Hardening Profile v2

- Strengthen sandboxing beyond the existing minimums:
  - explicit seccomp/AppArmor profiles where available
  - stricter filesystem constraints and "deny by default" egress if network enabled (e.g., via an egress proxy pattern)
  - runner image supply-chain controls (pin base images, vulnerability scanning in CI)
- This story is explicitly about reducing residual risk after network/secrets exist.

#### ST-06-06: Reliability Controls: Cancellation, Retries, and Quotas

- Add:
  - cancel queued/running jobs (best-effort kill container + mark cancelled)
  - retry policy (admin-only, explicit) for transient control-plane failures
  - basic quotas/rate limits (per-user and per-tool) to prevent noisy-neighbor effects
- This becomes important once a queue exists (otherwise users can DoS themselves unintentionally).

### EPIC-06 Dependencies and Risks

#### EPIC-06 Dependencies

- Runner contract stability (ADR-0015) and clear async/backpressure semantics (ADR-0016)
- Artifact persistence and cleanup mechanism (ideally completed in EPIC-05)

#### EPIC-06 Risks

- **Operational complexity increase**: queue + runner service introduces multi-process/multi-container deployment and more failure modes. Mitigation: keep interfaces narrow; ship with strong health checks and clear operator docs.
- **Security risk amplification** if network/secrets are added without strict policy and audit: mitigate by making policies explicit, default-off, and requiring privileged approval.
- **Data leakage** via artifacts/logs when secrets exist: mitigate via output sanitization rules, "do not log secrets" guardrails, and strong review practices.

---

## New ADRs Recommended

These decisions are large enough to deserve formal ADRs before implementation:

1. **ADR: HuleEdu OIDC integration shape (session bridge vs stateless)**

   Define whether HuleEdu auth results in Skriptoteket server-side sessions (recommended for consistency with the current UI/CSRF model) and define account matching/linking rules.

2. **ADR: Artifact retention, data classification, and purge semantics**

   Formalize retention windows (sandbox vs production), whether production input files are ever retained, and the operator/user purge model. This complements the hybrid storage strategy.

3. **ADR: Execution policy model (network/secrets/resource caps)**

   Define the policy entity, defaults, approval workflow, and enforcement points (web guardrails plus handler-level defense in depth).

4. **ADR: Persistent execution queue and worker topology**

   Define scheduling/fairness, retry rules, cancellation semantics, and how it supersedes ADR-0016's reject behavior (or when reject still applies).

5. **ADR: Dedicated runner service boundary**

   Define the service interface, authentication between app and runner, deployment topology, and threat model improvements relative to docker.sock in the app container.

6. **ADR: Secrets storage and injection**

   Encryption approach, audit requirements, injection mechanism, and logging/sanitization constraints.

(Separately: keep the existing "defer Kafka until needed" stance unless queueing/integrations demonstrably require it.)

---

## Adjustments to Current PRD Recommended

The PRD is directionally correct, but post-MVP reality benefits from making a few items explicit:

1. **Make retention and data-handling a first-class requirement.**

   Add explicit statements for sandbox vs production retention, production input-file handling defaults, and a purge mechanism expectation.

2. **Add an "Identity integration milestone" and define the default role for new SSO users.**

   The PRD already anticipates federation; it should explicitly state whether first-time HuleEdu users are auto-provisioned and what role they get by default (recommend: `user`).

3. **Clarify the long-running execution experience.**

   Add a post-MVP requirement that long-running tools should not require holding an HTTP request open; this sets justification for EPIC-06 queueing without changing the MVP success metrics for "common scripts."

4. **Explicitly call out "network/secrets are policy-controlled, default-off."**

   This codifies the teacher-first safety posture and avoids ad-hoc exceptions later.

---

## Roadmap Alignment

This EPIC-05/EPIC-06 roadmap stays aligned with the PRD's core intent—**a teacher-first, curated script execution platform**—by prioritizing friction removal (SSO), governance completeness (admin nomination approval), and operational safety (metrics + retention) before introducing heavier scalability mechanisms. When scale/security work arrives (queue, runner service, network/secrets), it is framed as enabling broader tool value while preserving the product's safety constraints ("do not execute uploaded code," default isolation, and user-safe outputs).
