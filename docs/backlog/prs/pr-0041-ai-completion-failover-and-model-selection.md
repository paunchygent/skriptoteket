---
type: pr
id: PR-0041
title: "AI inline completions: OpenAI-first + local fallback + profile selection"
status: ready
owners: "agents"
created: 2026-01-18
updated: 2026-01-18
stories:
  - "ST-08-30"
tags: ["backend", "frontend", "ai", "reliability"]
acceptance_criteria:
  - "Inline completions default to the external provider (OpenAI `gpt-5-nano`) when configured, allowed by the environment, and allowed by the user."
  - "Inline completions fall back to the local provider (Devstral) on eligible failures (connect/timeout/429/5xx), with one retry."
  - "Remote providers are never used unless remote providers are enabled for the environment and the user has explicitly enabled allow_remote_fallback=true (NULL counts as deny)."
  - "Users can select local vs external completions in Profile when external completion is available, but cannot select external unless allow_remote_fallback=true."
  - "When local completions are unavailable and remote is blocked, the UI shows a system message guiding users to Profile → AI settings (or admin policy when remote is disabled)."
  - "Docs + OpenAPI types are updated; tests cover routing behavior."
---

## Problem

Inline completions (ghost text) are currently a single-provider setup. When local inference is unavailable, completions
silently degrade and we cannot exercise the same reliability/opt-in semantics we already have for chat/chat-ops.

## Goal

- Make inline completions **external-first** (OpenAI `gpt-5-nano`) to reduce load on local GPU infrastructure.
- Add a **local fallback provider** (Devstral via llama.cpp) to keep completions functional during remote outages.
- Preserve privacy semantics: **no off-box** prompt/code leakage unless the environment allows remote providers and the user explicitly opts in (`allow_remote_fallback=true`).
- Add a **profile-level selector** for completion provider (local vs external) when external completions are configured.

## Non-goals

- Exposing arbitrary model selection beyond the configured local/external options.
- Cross-process circuit breaking for completions (in-process only).

## Implementation plan

1. Backend config / policy:
   - Add `AI_REMOTE_PROVIDERS_ENABLED` to hard-enable/disable remote AI usage for the environment.
   - Add `LLM_COMPLETION_FALLBACK_*` settings for an optional fallback provider.
   - Add `AI_DEFAULT_ALLOW_REMOTE_FALLBACK` to control default profile opt-in at creation time.
2. Backend behavior:
   - Implement completion routing: external vs local, with one retry on eligible failures.
   - Treat `allow_remote_fallback=NULL` as **deny** for completions.
   - Gate any remote completion usage behind both:
     - `AI_REMOTE_PROVIDERS_ENABLED=true` (admin policy), and
     - `allow_remote_fallback=true` (explicit per-user preference).
3. Profile + SPA:
   - Persist a per-user completion provider preference.
   - Update Profile UI to select local vs external completions when external completions are available.
   - Grey out remote AI settings when `AI_REMOTE_PROVIDERS_ENABLED=false`.
   - Prevent selecting external completions unless `allow_remote_fallback=true`.
4. Editor UX:
   - When inline completions degrade due to policy/consent, show a rate-limited system message pointing to Profile AI settings.
5. Docs:
   - Update ADR-0043 and `.env.example*` with the new config keys and recommended defaults.
6. Tests:
   - Backend unit tests for completion routing + opt-in behavior.
   - Frontend tests for Profile AI settings and completion request payload wiring.

## Test plan

- `pdm run test`
- `pdm run fe-test`
- `pdm run typecheck`
- `pdm run lint`

## Rollback plan

- Remove the fallback provider config and keep inline completions single-provider (local-only).
- Remove the profile completion preference field and fall back to local-only completions.
