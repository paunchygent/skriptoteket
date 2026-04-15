---
type: pr
id: PR-0043
title: "AI inline completions: consent enforcement + failover hardening + SRP consolidation"
status: done
owners: "agents"
created: 2026-01-18
updated: 2026-01-21
stories:
  - "ST-08-30"
tags: ["backend", "frontend", "ai", "security", "reliability", "performance"]
acceptance_criteria:
  - "Inline completion remote usage is consented purely via server-side state (profile/session): remote providers are never called unless `AI_REMOTE_PROVIDERS_ENABLED=true` AND the persisted profile allows it (`profile.allow_remote_fallback=true`; NULL counts as deny)."
  - "Inline completions re-compute token budgeting and system prompt when failing over between providers (primary ↔ fallback), using the selected provider's model/token counter."
  - "Profile → AI settings shows completion provider choices (local/external) but disables unavailable options based on `ai_policy` (`completion_local_available`, `completion_external_available`), and keeps the external option disabled unless remote providers are enabled and the user explicitly allows remote fallback."
  - "Frontend state does not drift after saving AI settings (server response becomes the source of truth for `auth.profile` + AI store)."
  - "When `profile.allow_remote_fallback` is NULL and local completions are unavailable but a remote completion provider is configured, the UI shows a system message prompting the user to explicitly approve/deny remote providers. The prompt is rate-limited across reloads (localStorage TTL = 24h) and reappears on later failover opportunities until the user makes an explicit choice."
  - "Tests cover consent enforcement, provider selection, and failover behavior without requiring a real LLM or Docker."
  - "The definition of “remote provider” is explicit, documented, and unit-tested: LAN/private endpoints are treated as local/trusted; admin policy gates only non-local providers."
---

## Problem

PR-0041 delivered OpenAI-first inline completions with local fallback plus a per-user setting for remote fallback and
completion provider preference.

While reviewing PR-0041 for correctness and long-term maintainability, we found a few subtle correctness/UX issues and
some avoidable complexity that increase cognitive load and make it easier for behavior to drift from docs.

This PR scopes follow-up work to (in recommended priority order) and is intended to be implemented after PR-0042
(payload compatibility for OpenAI-backed completions):

- Fix consent enforcement so the backend never relies on a client-supplied boolean for privacy-critical decisions.
- Make inline completion failover model-aware (prompt budgeting and system prompt) to match the chat/edit-ops pipeline.
- Tighten UI and state management so availability and selection rules are clear and consistent.
- Consolidate duplicated policy + routing logic to reduce SRP violations and improve the mental model.

## Goal

- Enforce consent and admin policy server-side for inline completions (and align other editor AI surfaces if needed).
- Keep inline completions reliable during outages by using a correct, model-aware failover path.
- Improve UI clarity: users only see options that can work, and are guided correctly when policy blocks usage.
- Reduce duplicated logic and “slot math” in inline completion routing to simplify future changes.

## Non-goals

- Exposing arbitrary model selection beyond the configured local/external options.
- Adding cross-process circuit breaking (in-process only).
- Reworking the editor AI request/response shapes unless strictly required for enforcement correctness.

## Decisions (final)

All decisions below are confirmed. Rejected alternatives are removed to keep this PR scope unambiguous.

### DP-1: Server-side consent enforcement for remote inline completions (privacy-critical)

**Desired behavior / perceived problem**

- Remote AI providers must never be called unless:
  - admin policy allows it (`AI_REMOTE_PROVIDERS_ENABLED=true`), and
  - the user explicitly opted in (`profile.allow_remote_fallback=true`; NULL counts as deny),
  regardless of what the client sends.

**Assumptions**

- We treat “privacy-critical gating” as server-trust only (client input is not consent).
- We want to preserve the note in ST-08-30: avoid per-request DB lookups in the inline completion hot path.
  - Therefore, consent for inline completions is purely profile/session-driven (no request-level consent flag).

**Validated drift**

- `remote_allowed` currently depends on the request payload (`allow_remote_fallback`) + settings, not persisted profile.
  - `src/skriptoteket/application/editor/completion_handler.py`
  - `src/skriptoteket/web/api/v1/editor/completions.py`

**Decision**

- Consent is profile/session-driven; inline completions do not take request-level consent flags.
- Cache consent in the server-side session for the inline completion hot path.
- Compute `effective_remote_allowed = AI_REMOTE_PROVIDERS_ENABLED AND session.allow_remote_fallback is True` (NULL counts as deny).
- When a user switches to deny, apply the change immediately to all active sessions.

### DP-2: Inline completion failover must be model-aware (prompt budget + system prompt)

**Desired behavior / perceived problem**

- When failing over from provider A → provider B, we must recompute:
  - token counter, system prompt, and budgeted prefix/suffix for provider B’s model.
  This should match how chat/edit-ops handles provider changes.

**Assumptions**

- Primary and fallback providers can have different models and different context/tokenization behavior.
- The latency overhead of recomputing budgets only happens on failover (rare) or can be computed lazily per attempt.

**Validated drift**

- Inline completions compute system prompt + budget once (primary model) and reuse it for fallback.
  - `src/skriptoteket/application/editor/completion_handler.py`

**Decision**

- Recompute token counter, system prompt, and prompt budgets per attempt (provider A, then provider B on eligible failover), matching chat/edit-ops behavior.

### DP-3: Define what “remote provider” means (avoid policy bypass via LAN/private endpoints)

**Desired behavior / perceived problem**

- “Remote providers disabled” should reliably prevent sending prompts/code to any provider that is considered off-box
  for the environment, not only public internet endpoints.

**Assumptions**

- LAN/private endpoints are treated as local/trusted by design (application logic), and are not an admin policy concern.
- Trusted endpoints are defined via code and deployment wiring (e.g., compose base URLs), not via per-environment admin
  toggles.

**Validated drift**

- `is_remote_llm_endpoint()` treats private/link-local IPs as local (non-remote).
  - `src/skriptoteket/infrastructure/llm/provider_sets.py`

**Decision**

- LAN/private endpoints are local/trusted (application semantics).
- Keep current endpoint classification (`is_remote_llm_endpoint`) and lock it in with unit tests + explicit docs.
- Trusted endpoints are defined via code/deployment wiring (compose base URLs), not via an admin-configurable allowlist.

### DP-4: Profile UI should reflect actual availability (local vs external completions)

**Desired behavior / perceived problem**

- Users should not be able to select a completion provider that cannot work in the current environment.
- UI should clearly explain why an option is disabled (policy vs missing provider).

**Assumptions**

- We keep the “availability detection” via `ai_policy` as the source of truth for what the environment supports.

**Validated drift**

- UI gates “external” but not “local”; `completion_local_available` is available but unused.
  - `src/skriptoteket/web/api/v1/auth.py`
  - `frontend/apps/skriptoteket/src/stores/ai.ts`
  - `frontend/apps/skriptoteket/src/components/profile/ProfileEditAiSettings.vue`

**Decision**

- Show but disable unavailable completion provider options based on `ai_policy` (`completion_local_available`, `completion_external_available`).
- Only allow selecting external completions when both admin policy and user consent allow it.

### DP-5: After saving AI settings, frontend state must be server-authoritative (no drift)

**Desired behavior / perceived problem**

- After `/profile/ai-settings` PATCH, the UI should reflect the persisted server profile immediately and consistently.

**Assumptions**

- The server is the source of truth; we want fewer stores with competing state.

**Validated drift**

- The AI store ignores the response body from `/profile/ai-settings`, and manually mutates local store state.
  - `src/skriptoteket/web/api/v1/profile.py`
  - `frontend/apps/skriptoteket/src/stores/ai.ts`

**Decision**

- `auth.profile` is the single source of truth for profile AI fields (`allow_remote_fallback`, `inline_completion_provider`).
- The AI store becomes a thin view-model (derived state + persistence actions), not an owner of duplicated profile fields.
- Saving AI settings hydrates from the server response and updates `auth.profile` (no optimistic duplication).

### DP-6: Consolidate policy + routing logic to reduce SRP violations (cleanup)

**Desired behavior / perceived problem**

- Policy evaluation and blocked messaging should be consistent across inline completions/chat/edit-ops without each
  handler re-implementing its own version.

**Assumptions**

- We want a single mental model: “admin gate” + “user consent” → effective permission.
  - Inline completions do not use a request-level consent gate (profile/session only).
  - “Request/session deny” only applies as a UX concept (cooldown / avoid repeated prompting), not as consent.
  - Persisted consent is the only thing that can enable remote providers.

**Decision**

- Consolidate consent evaluation + notice selection into small shared helpers (SRP direction), without introducing a full “AI service” in this PR.
- Apply the same consent semantics across inline completions, chat, and edit-ops:
  - `profile.allow_remote_fallback=true`: remote providers may be used when needed (still gated by `AI_REMOTE_PROVIDERS_ENABLED`).
  - `profile.allow_remote_fallback=false`: remote providers are never used and no consent prompt is shown.
  - `profile.allow_remote_fallback=NULL`: treat as deny for execution, but return a notice prompting the user to explicitly approve/deny on failover opportunities where a remote provider would help.
- The frontend rate-limits the prompt across reloads (localStorage TTL = 24h); visiting Profile without saving does not count as answered.

## Implementation plan

### Phase 1 — Consent enforcement (profile/session-driven)

1. Introduce an editor-AI request context in the web layer (or a protocol-first provider in application layer) that
   exposes:
   - `actor: User`
   - `session: Session`
   - `profile_ai: { allow_remote_fallback: bool | None, inline_completion_provider: ... }`
2. Cache `profile.allow_remote_fallback` and `profile.inline_completion_provider` in the server-side session (nullable)
   so editor AI hot paths do not require per-request profile lookups.
3. Compute `effective_remote_allowed` server-side from:
   - `settings.AI_REMOTE_PROVIDERS_ENABLED`, and
   - session-cached consent (`session.allow_remote_fallback is True`; NULL counts as deny).
4. Ensure deny applies immediately across all active sessions when the user updates AI settings.
5. Apply the same consent semantics across inline completions, chat, and edit-ops:
   - deny: no remote calls and no consent prompt,
   - unset: treat as deny for execution, but return a notice on failover opportunities prompting the user to choose.
6. Remove request-level consent from editor AI request payloads (completions/chat/edit-ops). The backend derives consent
   from session/profile; any legacy client flags are treated as no-ops.

Performance note:

- Implement session-level cached fields for editor AI hot paths:
  - `sessions.allow_remote_fallback` (nullable boolean; NULL = unset/deny)
  - `sessions.inline_completion_provider` (nullable string; NULL = unset)
  Keep them in sync at login and when `/profile/ai-settings` is updated.

### Phase 2 — Failover hardening (model-aware recompute)

1. When switching providers (primary ↔ fallback), recompute:
   - model selection (per provider slot),
   - token counter,
   - system prompt (template + model),
   - prompt budgets (prefix/suffix trimming).
2. Keep the retry policy the same (one retry on eligible failures), but ensure the second attempt is fully
   model-consistent.
3. Add structured logs/metrics to make failover observable (provider kind, model, outcome, retry reason).

### Phase 3 — UI + state alignment (availability + auth.profile truth)

1. Use `completion_local_available` to gate the “Local (Devstral)” radio:
   - If not available, disable it with a short environment-level explanation.
2. Keep the external option disabled unless:
   - `remoteProvidersEnabled=true` (admin), and
   - the user explicitly enabled remote fallback (`selection === "allow"`).
3. Make the server response authoritative after saving AI settings:
   - `persistAiSettings()` returns the updated `ProfileResponse`.
   - Update `auth.profile` from the response; the AI store derives state from `auth.profile` + `ai_policy`.
4. Implement the “unset consent” prompt cooldown in frontend:
   - Store last-seen timestamps per user + notice code in localStorage with TTL = 24h.
   - Continue prompting on future failover opportunities until an explicit allow/deny is saved (visiting Profile without saving does not count as answered).

### Phase 4 — Remote endpoint classification lock-in (LAN is local/trusted)

1. Keep existing classification semantics (LAN/private endpoints are local/trusted).
2. Add/adjust unit tests to lock the classification rules.
3. Update docs (`.env.example*`, ADR-0043 if needed) to make the semantics explicit (“admin gate” is for non-local
   providers).

### Phase 5 — Consolidation cleanup (SRP direction, no AI service yet)

1. Factor consent/policy evaluation and “blocked notice” selection into a small shared helper used across
   completions/chat/edit-ops.
2. Refactor inline completions routing into an explicit attempt plan (candidate list + one retry), reducing branching.
3. (Optional) Add a single “editor auth context” dependency to avoid duplicate session fetching.

## Test plan

Backend:

- New unit tests for consent enforcement (remote never called when profile deny/unset, regardless of request payload).
- New unit tests for failover re-budgeting correctness (fallback attempt uses fallback model/token counter/system prompt).
- Existing suite remains green:
  - `pdm run test`
  - `pdm run typecheck`
  - `pdm run lint`

Frontend:

- Unit tests for Profile AI settings gating based on `ai_policy` availability fields.
- Unit tests for “unset consent” notice cooldown (localStorage TTL = 24h).
- `pdm run fe-test`

## Rollback plan

- If consent enforcement causes unexpected behavior, temporarily force inline completions to local-only in config while
  keeping the UI settings intact (so we do not lose user preferences).
- If failover hardening introduces regressions, disable fallback by clearing `LLM_COMPLETION_FALLBACK_*` in env.

## Checklist

- [ ] Enforce server-side consent (profile/session-driven; NULL counts as deny).
- [ ] Cache consent + completion preference in `sessions` and sync on login + `/profile/ai-settings`.
- [ ] Apply deny immediately across all active sessions.
- [ ] Make inline completion failover model-aware (prompt + budget per attempt).
- [ ] Implement “unset consent” notice + 24h localStorage cooldown; keep prompting until explicit choice.
- [ ] Make `auth.profile` the single source of truth; AI store becomes derived view-model + persistence.
- [ ] Gate Profile UI provider choices by `ai_policy` and disable unavailable options.
- [ ] Lock in LAN/private endpoint classification semantics via unit tests + docs.
- [ ] Consolidate consent evaluation + notice selection helpers (SRP direction; no AI service introduced).
- [ ] Verification: `pdm run test`, `pdm run fe-test`, `pdm run typecheck`, `pdm run lint`.
- [ ] Documentation: update PR-0041 and/or ADR-0043 if behavior/semantics change; run `pdm run docs-validate`.
- [ ] If UI changes: perform live UI functional check and record in `.codex/handoff.md`.
