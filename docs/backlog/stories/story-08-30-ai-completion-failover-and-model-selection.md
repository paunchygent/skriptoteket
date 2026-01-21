---
type: story
id: ST-08-30
title: "AI: inline completion failover + per-user completion provider selection"
status: done
owners: "agents"
created: 2026-01-18
updated: 2026-01-21
epic: "EPIC-08"
acceptance_criteria:
  - "Given inline completions are configured with an external primary (OpenAI `gpt-5-nano`) and a local fallback (Devstral), when the primary provider fails (connect/timeout/HTTP 429/HTTP 5xx), then the backend retries once against the fallback provider and returns a completion response."
  - "Given remote AI use is not allowed for the user (`allow_remote_fallback` is false or NULL), when the external completion provider is selected, then the backend does not call any remote provider and falls back to local completions."
  - "Given remote AI use is not allowed for the user and local completions are unavailable, the UI shows a system message guiding the user to enable external AI in Profile → AI settings (when admin policy allows)."
  - "Given remote providers are disabled by admin policy (`AI_REMOTE_PROVIDERS_ENABLED=false`), remote completion options are not selectable and the UI shows an admin-policy message."
  - "Given remote completion is configured and allowed, users can choose in their profile whether inline completions should use the local or external provider by default."
  - "Given remote completion is not configured, the profile UI does not offer an external completion option."
  - "Given a deployment config sets AI_DEFAULT_ALLOW_REMOTE_FALLBACK=true, newly created user profiles default to allow_remote_fallback=true (but remain user-editable)."
ui_impact: "Yes (profile AI settings + editor completion routing)."
data_impact: "Yes (persist per-user completion provider preference)."
dependencies:
  - "ADR-0043"
  - "ST-08-14"
---

## Context

We already support:

- Inline completions (ghost text) via an OpenAI-compatible backend proxy (ADR-0043 / ST-08-14).
- Chat/chat-ops provider failover with explicit opt-in for remote fallback (ST-08-26).

Inline completions are currently a single-provider setup and do not support:

- Automatic failover to a remote provider when local inference is down.
- Per-user selection of local vs external completions.

## Goal

- Prefer **OpenAI `gpt-5-nano`** for inline completions (when allowed) to reduce load on local inference.
- Keep **Devstral (local llama.cpp)** available as a fallback for inline completions when remote inference fails.
- Allow users to choose the inline completion provider in their profile (local vs external) when external completion is
  available.
- Keep privacy semantics consistent: remote providers are only used when allowed by environment policy and the user has
  explicitly enabled remote fallback (NULL counts as deny).

## Notes / constraints

- Inline completion requests are frequent; avoid per-request database lookups for profile settings in the hot path.
- External model choice for the “external” option is `gpt-5-nano` with `reasoning_effort=minimal` (GPT-5 request shaping).
