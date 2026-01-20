# Session Handoff

Keep this file updated so the next session can pick up work quickly.

## Editing Rules (do not break structure)

- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files instead.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines; move history to `.agent/readme-first.md` + `docs/`.

## Snapshot

- Date: 2026-01-20
- Branch: `main` + local changes
- Current sprint: None (between sprints; last: `SPR-2026-01-05` (done))
- Production: Full Vue SPA
- Completed: recent — ST-14-11/12 done; ST-14-19 done; ST-14-20 done; ST-14-23 done; ST-08-24 done; ST-08-28 done; ST-08-29 done (history: `.agent/readme-first.md`)

## Current Session (2026-01-20)

- Drafted EPIC-19 foundations (request.json + file refs + promotions + runner contract v3) and rewired ST-14-24/ST-14-36 dependencies (docs-only planning, no code changes yet).
  - New docs: `docs/backlog/epics/epic-19-runner-io-and-file-references-foundations.md`,
    `docs/backlog/stories/story-19-01-runner-request-envelope.md`,
    `docs/backlog/stories/story-19-02-file-refs-resolver-and-promotion.md`,
    `docs/backlog/stories/story-19-03-runner-contract-v3-structured-errors-state-update-and-promotions.md`.
  - Updated stories: `docs/backlog/stories/story-14-24-ui-contract-file-references.md`,
    `docs/backlog/stories/story-14-36-user-file-vault-and-picker.md`.
- PR-0047 inline completion normalization: added cursor-boundary overlap stripping + eval telemetry + timing logs; updated harness metrics + Playwright ghost-text diagnostic to capture overlap.
  - Key files: `src/skriptoteket/application/editor/completion_handler.py`, `src/skriptoteket/protocols/llm.py`,
    `src/skriptoteket/web/api/v1/editor/completions.py`, `tests/unit/application/test_editor_inline_completion_handler.py`,
    `tests/unit/web/test_editor_inline_completion_api.py`, `scripts/llm_harness/inline_completion_harness.py`,
    `scripts/diagnose_ghost_text.py`, `docs/backlog/prs/pr-0047-ai-inline-completion-normalization-and-caps.md`.
- Playwright diagnostic timeout raised to 15s and request/response captured via event listeners; ghost-text capture is
  now resilient to slower local completions. See `scripts/diagnose_ghost_text.py`.
- Inline completion logs now include token counts (`system_prompt_tokens`, `prefix_tokens`, `suffix_tokens`,
  `prompt_budget_tokens`) per request for local/remote providers. See `src/skriptoteket/application/editor/completion_handler.py`.
- Added `prompt_tokens_total` (system + prefix + suffix) to inline completion logs + capture payload.
- Playwright diagnostic now supports `--cursor-anchor-mode inline` + `--cursor-delete-line-tail` to insert inline
  holes for completions; `--cursor-mode middle` still scrolls mid-file. File: `scripts/diagnose_ghost_text.py`.
- Config: raised inline completion system prompt budget default to 2048; see `src/skriptoteket/config.py` and
  `docs/reference/ref-ai-completion-architecture.md`.
- Docs: updated `docs/runbooks/runbook-huleedu-integration.md` to use `OPENAI_LLM_COMPLETION_API_KEY` (replaces
  outdated `OPENAI_API_KEY` reference).
- Playwright inline-hole diagnostic now supports inline anchor + deleting line tail; ran obvious inline hole in a
  1000+ line script and got short, correct completions from both local and GPT‑5 (details in Verification).
- Ran three targeted inline-hole anchors (render_options / if-not guard / notice f-string) against long script:
  local and GPT‑5 both produced off-target or empty completions for 2–3, suggesting ambiguity/echo handling issues.
- Added `--cursor-delete-next-lines` to the Playwright diagnostic to carve true holes in the suffix for inline
  completion testing.
- Execution queue implementation shipped: ST-18-01 / PR-0039 (Postgres `tool_run_jobs` + worker loop + adopt-first stale-lease recovery); see `docs/backlog/prs/pr-0039-execution-queue-worker-loop.md`.
  - Key files: `src/skriptoteket/workers/execution_queue_worker.py`, `src/skriptoteket/infrastructure/repositories/tool_run_job_repository.py`, `migrations/versions/0027_tool_run_jobs_execution_queue.py`, `migrations/versions/0028_tool_runs_started_at_drop_default.py`.
- AI inline completions failover + per-user provider selection: ST-08-30 / PR-0041; see `docs/backlog/prs/pr-0041-ai-completion-failover-and-model-selection.md`.
  - Key files: `src/skriptoteket/application/editor/completion_handler.py`, `src/skriptoteket/web/api/v1/profile.py`, `frontend/apps/skriptoteket/src/components/profile/ProfileEditAiSettings.vue`, `frontend/apps/skriptoteket/src/composables/editor/skriptoteketGhostText.ts`.
  - Migration: `migrations/versions/0029_profile_inline_completion_provider.py` (+ docker idempotency test `tests/integration/test_migration_0029_profile_inline_completion_provider_idempotent.py`).
- PR-0043 implemented: inline completion consent hardening + SRP consolidation; see `docs/backlog/prs/pr-0043-ai-inline-completions-consent-hardening.md`.
  - Backend: session-cached AI settings (no request-level consent flags); tri-state consent (unset prompts, deny doesn’t); model-aware inline completion retries.
  - Frontend: `auth.profile` is source of truth; AI store is derived view-model; 24h localStorage TTL for “remote fallback required” notice.
  - Migration: `migrations/versions/0030_sessions_cache_ai_settings.py` (+ docker idempotency test `tests/integration/test_migration_0030_sessions_cache_ai_settings_idempotent.py`).
- Docs: updated ST-08-33 + PR-0047 for inline completion normalization + shared 64-token budget + validation checklist; see `docs/backlog/stories/story-08-33-ai-inline-completion-normalization-and-caps.md` and `docs/backlog/prs/pr-0047-ai-inline-completion-normalization-and-caps.md`.
- Fix: ghost text no longer disappears when OpenAI Responses returns `finish_reason=length|incomplete`; we now normalize and return best-effort output (truncation is logged but not hard-discarded). Key file: `src/skriptoteket/application/editor/completion_handler.py`.
- SPA updated for queued runs (polling + status rendering + timestamps); see `frontend/apps/skriptoteket/src/views/MyRunsListView.vue` and `frontend/apps/skriptoteket/src/views/ToolRunView.vue`.
- Docs status: ADR-0062 accepted, EPIC-18 active, review approved; ST-18-01 set to `in_progress` (PR-0039 done; PR-0040 pending for coverage).
- Verification:
  - Playwright (real editor request): `pdm run python -m scripts.diagnose_ghost_text --base-url http://127.0.0.1:8001`
    (artifacts in `.artifacts/diagnose-ghost-text/result.json`); prefix `def run_tool`, completion starts with `(`,
    `cursor_overlap_chars=0`, ghost text present.
  - Backend log correlation (uvicorn :8001): `ai_inline_completion_truncated` + `ai_inline_completion_normalized`
    with `prefix_overlap_chars=12` and correlation id `1a504b18-48f6-47e6-a2d0-2fc8c92eb97a` (from session logs).
  - Tee'd backend log (uvicorn :8002): `LLM_COMPLETION_SYSTEM_PROMPT_MAX_TOKENS=2048` +
    `VITE_DEV_SERVER_URL=http://127.0.0.1:5173` -> `.artifacts/inline-completion-verify.log` shows
    `inline_completion_payload_shape` (`prompt_format="fim"`) and `ai_inline_completion_normalized`
    (correlation id `2a58aba5-dac8-4b16-ac74-f1e8b7a2ab1e`, `provider_ms ~3.6s`).
  - Playwright inline-hole run (local): `pdm run python -m scripts.diagnose_ghost_text --base-url http://127.0.0.1:8002 --tool-slug html-to-pdf-preview --cursor-anchor "render_options: dict[str, object] = " --cursor-anchor-mode inline --cursor-text "{" --cursor-delete-line-tail`
    produced suffix tokens (512) but normalized completion dropped as contiguous echo (correlation id `f7beb17a-1e9a-46ed-8e8e-c88beeb70645`).
  - GPT-5 inline-hole run (same anchor, provider preference `external`): `prompt_format="delimited"` and
    `ai_inline_completion_normalized` dropped as contiguous echo (correlation id `a14dc765-61f6-496d-b797-e6b379021709`).
  - Obvious inline-hole run (long script, local): `pdm run python -m scripts.diagnose_ghost_text --base-url http://127.0.0.1:8005 --tool-slug html-to-pdf-preview --cursor-anchor "return _handle_preview(input_files=" --cursor-anchor-mode inline --cursor-text "" --cursor-delete-line-tail`
    → completion `input_files=input_files,\n)` with ghost text present; `prompt_format="fim"`, `normalized_chars=30`
    (correlation id `aa95da5b-c4de-4980-8361-b2487a75dc37`).
  - Obvious inline-hole run (long script, GPT‑5): same command with provider preference `external`
    → completion `input_files)` with ghost text present; `prompt_format="delimited"`, `normalized_chars=12`
    (correlation id `d4f15f1b-b903-4f9b-a478-3557f90efeb8`).
  - Targeted anchors (long script):
    - `render_options: dict[str, object] = {` → Local and GPT‑5 returned unrelated blocks (see
      `.artifacts/diagnose-ghost-text/result.json` after each run).
    - `if not html_sources:` → Local returned unrelated block; GPT‑5 returned empty (likely contiguous echo dropped).
    - `_notice(level, f"{ok_count} PDF skapades` → Local returned unrelated block; GPT‑5 returned empty.
  - Targeted anchors with suffix holes (new flag):
    - Local: `pdm run python -m scripts.diagnose_ghost_text --base-url http://127.0.0.1:8000 --tool-slug html-to-pdf-preview --cursor-anchor "render_options: dict[str, object] = " --cursor-anchor-mode inline --cursor-text "{" --cursor-delete-line-tail --cursor-delete-next-lines 5`
      → completion still off-target (inserted unrelated options dict).
    - Local: `pdm run python -m scripts.diagnose_ghost_text --base-url http://127.0.0.1:8000 --tool-slug html-to-pdf-preview --cursor-anchor "if not html_sources:" --cursor-anchor-mode inline --cursor-text "" --cursor-delete-line-tail --cursor-delete-next-lines 8`
      → completion still off-target (enum options block).
    - Local: `pdm run python -m scripts.diagnose_ghost_text --base-url http://127.0.0.1:8000 --tool-slug html-to-pdf-preview --cursor-anchor "_notice(level, f\"{ok_count} PDF skapades" --cursor-anchor-mode inline --cursor-text "" --cursor-delete-line-tail`
      → completion still off-target (table rows block).
    - GPT‑5: same anchors via Vite proxy (`--base-url http://127.0.0.1:5173`) against `:8006` backend → 1–3 still
      empty or off-target (see `.artifacts/diagnose-ghost-text/result.json` after each run).
  - `pdm run lint`
  - `pdm run typecheck`
  - `pdm run test`
  - `pdm run fe-test`
  - Manual: `POST /api/v1/editor/completions` with `X-Skriptoteket-Eval: 1` returns non-empty `completion` even when `X-Skriptoteket-Eval-Outcome=truncated`; correlate via `x-correlation-id` with `docker logs skriptoteket_web --since 5m | rg ai_inline_completion_(request|truncated|normalized)`.
  - `pdm run db-upgrade` (applied `0030_sessions_cache_ai_settings` to local dev DB)
  - `pdm run pytest -m docker --override-ini addopts=''`
  - `pdm run test`
  - `pdm run typecheck`
  - `pdm run lint`
  - `pdm run fe-gen-api-types`
  - `pdm run fe-test`
  - `pdm run pytest tests/unit/application/test_editor_inline_completion_handler.py -q`
  - `pdm run ui-editor-smoke -- --base-url http://127.0.0.1:5173` (artifacts in `.artifacts/ui-editor-smoke/`)

## How to Run

```bash
# Setup
docker compose up -d db && pdm run db-upgrade

# Development (backend + SPA)
ARTIFACTS_ROOT=/tmp/skriptoteket/artifacts pdm run dev-local

# Quality gates
pdm run format
pdm run lint
pdm run typecheck
pdm run test
```

## Known Issues / Risks

- Local Devstral inline completions remain slower than ideal; backend logs show `provider_ms ~3.5-5.2s` and the
  UI auto-trigger debounce adds 1.5s, so ghost text can take ~5-7s to appear on local FIM.
- Large local worktree from PR-0033 refactors; verify intent before staging changes outside that scope.
- Queue-enabled runs require a worker process; if `RUNNER_QUEUE_ENABLED` is enabled without `run-execution-worker` running, runs will remain `queued`.
- Playwright on macOS may require elevated sandbox permissions (Chromium MachPortRendezvous permission denied) in some terminals/agents.
- Production needs DB migrations applied:
  - `0028_tool_runs_started_at_drop_default` (removes `tool_runs.started_at DEFAULT now()`, otherwise queued run creation can 500)
  - `0029_profile_inline_completion_provider` (adds `user_profiles.inline_completion_provider`, required for PR-0041)
  - `0030_sessions_cache_ai_settings` (adds `sessions.allow_remote_fallback` + `sessions.inline_completion_provider`, required for PR-0043)

## Next Steps

- Execute PR-0040 (execution queue test coverage): `docs/backlog/prs/pr-0040-execution-queue-test-coverage.md`.
