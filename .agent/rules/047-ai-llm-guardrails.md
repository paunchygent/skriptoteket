---
id: "047-ai-llm-guardrails"
type: "implementation"
created: 2026-01-22
scope: "backend"
---

# 047: AI / LLM Guardrails (Editor: completions + chat + edit-ops)

This repo includes optional AI editor features (ghost text completions, streaming chat, edit-ops). These features are
security-sensitive and easy to regress.

## Non-negotiables (REQUIRED)

- **Never log prompts or tool code** to stdout/stderr or databases. Keep logs metadata-only.
- **Captures are OFF by default**. If enabled, treat captures as sensitive:
  - Controlled by settings like `LLM_CAPTURE_ON_ERROR_ENABLED`
  - Stored under `ARTIFACTS_ROOT/llm-captures/`
- **Remote providers are gated**:
  - Global toggle: `AI_REMOTE_PROVIDERS_ENABLED`
  - Per-user consent: `profile.allow_remote_fallback` (NULL counts as deny)
- **Do not mix OpenAI API shapes**:
  - Chat Completions uses `response_format`
  - Responses API uses `text.format`
  - Mixing shapes causes hard upstream 400s; validate before sending.

## Source of truth (use these docs)

- OpenAI params + caching + structured output shapes:
  - `docs/runbooks/runbook-openai-responses-api.md`
- Editor AI architecture + debugging entrypoints:
  - `docs/runbooks/runbook-editor-ai-pipeline.md`
  - `docs/reference/reports/codemaps/ai-api-surfaces-tool-editor.md`

## Change protocol (recommended)

When changing LLM/AI code:

- Run focused unit tests under `tests/unit/infrastructure/llm/`.
- For end-to-end regressions, use the Playwright diagnose scripts documented in
  `docs/runbooks/runbook-editor-ai-pipeline.md`.
