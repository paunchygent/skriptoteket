# Session Handoff

Keep this file updated so the next session can pick up work quickly.

## Editing Rules (do not break structure)

- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files instead.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines; move history to `.agent/readme-first.md` + `docs/`.

## Snapshot

- Date: 2026-01-22
- Branch: `main` + local changes
- Current sprint: None (between sprints; last: `SPR-2026-01-05` (done))
- Production: Full Vue SPA
- Completed: history in `.agent/readme-first.md`

## Current Session (2026-01-22)

- PR-0049 SRP splits completed: `src/skriptoteket/application/editor/edit_ops/`, `src/skriptoteket/web/api/v1/editor/models/`,
  `src/skriptoteket/infrastructure/runner/docker/`, `src/skriptoteket/workers/execution_queue/`,
  `src/skriptoteket/di/infrastructure/` (container wiring updated in `src/skriptoteket/di/__init__.py`).
- Added pre-EPIC-19 runner seam stories: `docs/backlog/stories/story-19-04-runner-request-factory-seam.md`,
  `docs/backlog/stories/story-19-05-runner-result-parser-seam.md`,
  `docs/backlog/stories/story-19-06-runner-contract-selection-seam.md` (EPIC-19 + docs index updated).
- EPIC-19 approved (runner request envelope + FileRefs + promotions + runner contract v3 foundations).
  - Files: `docs/backlog/epics/epic-19-runner-io-and-file-references-foundations.md`,
    `docs/backlog/reviews/review-epic-19-runner-io-and-file-references-foundations.md`.
  - ADRs: `docs/adr/adr-0063-runner-request-envelope-v1.md`, `docs/adr/adr-0064-file-references-and-resolver.md`,
    `docs/adr/adr-0065-runner-contract-v3-state-update-errors-and-session-promotions.md`.
  - Alignment: `docs/backlog/stories/story-19-01-runner-request-envelope.md`,
    `docs/backlog/stories/story-19-02-file-refs-resolver-and-promotion.md`,
    `docs/backlog/stories/story-19-03-runner-contract-v3-structured-errors-state-update-and-promotions.md`,
    `docs/backlog/stories/story-14-24-ui-contract-file-references.md`,
    `docs/backlog/stories/story-14-36-user-file-vault-and-picker.md`.
  - Conflicts resolved in ADRs: `docs/adr/adr-0024-tool-sessions-and-ui-payload-persistence.md`,
    `docs/adr/adr-0031-multi-file-input-contract.md`, `docs/adr/adr-0039-session-file-persistence.md`.
- PR-0047: softened contiguous-echo drop, added right-side replace metadata, and tightened inline prompts.
  - Backend normalization + replace hint: `src/skriptoteket/application/editor/completion_handler.py`.
  - Response field + API plumbing: `src/skriptoteket/protocols/llm/`, `src/skriptoteket/web/api/v1/editor/models/`,
    `src/skriptoteket/web/api/v1/editor/completions.py`.
  - Frontend acceptance replace window: `frontend/apps/skriptoteket/src/composables/editor/skriptoteketGhostText.ts`.
  - Prompt tweaks: `src/skriptoteket/application/editor/system_prompts/inline_completion_v1.txt`,
    `src/skriptoteket/application/editor/system_prompts/inline_completion_gpt5_v1.txt`.
- Frontend warning cleanup (withDefaults + router + onBeforeUnmount):
  - Removed `withDefaults` imports in SFCs (macro is global).
  - Added `/profile` route in test router to avoid Vue Router warnings: `frontend/apps/skriptoteket/src/test/utils.ts`.
  - Switched cleanup to `onScopeDispose` to avoid lifecycle warnings in tests: `frontend/apps/skriptoteket/src/composables/editor/useEditorChat.ts`.
- Tests added/updated for replace_suffix_chars + overlap: `tests/unit/application/test_editor_inline_completion_handler.py`,
  `tests/unit/web/test_editor_inline_completion_api.py`, `frontend/apps/skriptoteket/src/composables/editor/skriptoteketGhostText.spec.ts`.
- PR doc updated with new validation notes + checklist: `docs/backlog/prs/pr-0047-ai-inline-completion-normalization-and-caps.md`.
- Quality gates run: `pdm run lint`, `pdm run typecheck`, `pdm run test`, `pdm run fe-test`, `pdm run docs-validate`.
- PR-0050: enforce strict separation of Chat vs Responses structured outputs (Option B).
  - Code: `src/skriptoteket/infrastructure/llm/openai/grammars.py`,
    `src/skriptoteket/infrastructure/llm/openai/payloads.py`,
    `src/skriptoteket/infrastructure/llm/openai/chat_ops_provider.py`,
    `src/skriptoteket/infrastructure/llm/openai/types.py`.
  - Tests: `tests/unit/infrastructure/llm/test_openai_payloads.py`,
    `tests/unit/infrastructure/llm/test_openai_chat_ops_provider_grammar.py`.
  - Docs: `docs/runbooks/runbook-openai-responses-api.md`,
    `docs/backlog/prs/pr-0050-openai-responses-structured-output-shape-fix.md`.
- Docs-sync pass: marked completed backlog items as `done`.
  - PRs: PR-0040, PR-0041, PR-0042, PR-0043, PR-0046, PR-0047, PR-0048, PR-0050.
  - Stories: ST-08-30, ST-08-31, ST-08-32, ST-08-33, ST-18-01.
  - Epics updated: `docs/backlog/epics/epic-08-contextual-help-and-onboarding.md`,
    `docs/backlog/epics/epic-18-execution-queue-and-worker-loop.md`.
- Docs-sync pass (next 15): marked PR-0030, PR-0031, PR-0032, PR-0033, PR-0036, PR-0038, and ST-07-06 as `done`
  (EPIC-07 updated).
- Runner contract seams shipped (ST-19-04/05/06): request factory + result parser + DI contract selector wired in
  `src/skriptoteket/infrastructure/runner/docker/` + `src/skriptoteket/di/infrastructure/runner.py`, seam tests in
  `tests/unit/infrastructure/runner/test_runner_contract_seams.py`, docker runner tests split into
  `tests/unit/infrastructure/runner/test_docker_runner_execute.py` and
  `tests/unit/infrastructure/runner/test_docker_runner_adoption.py`.
- V3 scaffolding helpers added (PR-0051): runner contract schemas in
  `src/skriptoteket/infrastructure/runner/contracts/`, archive builder helper in
  `src/skriptoteket/infrastructure/runner/docker/workdir_archive.py`, and
  `RunnerRequest` now carries optional `request_json_bytes` for V3.
- Promotions validation moved into `validate_promotion_envelope` in
  `src/skriptoteket/infrastructure/runner/contracts/promotions_v3.py`.

## Verification

- Services (running):
  - Dev-local (backend + SPA) on `:8000`/`:5173`: `pdm run dev-local` (SPA check via `curl -I http://127.0.0.1:5173/`).
  - Local backend (FIM) on `:8002`: `WATCHFILES_FORCE_POLLING=true LLM_COMPLETION_ENABLED=true LLM_COMPLETION_SYSTEM_PROMPT_MAX_TOKENS=2048 pdm run uvicorn --app-dir src skriptoteket.web.app:app --reload --host 127.0.0.1 --port 8002` (log: `.artifacts/inline-completion-verify-local.log`).
  - GPT backend on `:8003`: `WATCHFILES_FORCE_POLLING=true LLM_COMPLETION_ENABLED=true LLM_COMPLETION_BASE_URL=https://api.openai.com LLM_COMPLETION_MODEL=gpt-5-nano AI_REMOTE_PROVIDERS_ENABLED=true LLM_COMPLETION_SYSTEM_PROMPT_MAX_TOKENS=2048 pdm run uvicorn --app-dir src skriptoteket.web.app:app --reload --host 127.0.0.1 --port 8003` (log: `.artifacts/inline-completion-verify-gpt5.log`).
  - Vite (local) on `:5173` → proxy `:8002`: `VITE_DEV_PROXY_TARGET=http://127.0.0.1:8002 pnpm -C frontend --filter @skriptoteket/spa dev`.
  - Vite (GPT) on `:5174` → proxy `:8003`: `VITE_DEV_PROXY_TARGET=http://127.0.0.1:8003 pnpm -C frontend --filter @skriptoteket/spa exec vite --port 5174 --strictPort`.
- Playwright (real editor requests; escalated permissions required on macOS):
  - Local (long script, suffix hole): `pdm run python -m scripts.diagnose_ghost_text --base-url http://127.0.0.1:5173 --tool-slug html-to-pdf-preview --cursor-anchor "if not html_sources:" --cursor-anchor-mode line --cursor-text "        return {" --cursor-delete-next-lines 7`
    → ghost text present; `cursor_overlap_chars=0` in `.artifacts/diagnose-ghost-text/result.json` (completion off-target).
  - GPT-5 (long script, return block hole): `pdm run python -m scripts.diagnose_ghost_text --base-url http://127.0.0.1:5174 --tool-slug html-to-pdf-preview --cursor-anchor "if not html_sources:" --cursor-anchor-mode line --cursor-text "        return {" --cursor-delete-next-lines 7`
    → ghost text present; `cursor_overlap_chars=0`.
- Logs (source of truth):
  - Local: `.artifacts/inline-completion-verify-local.log` correlation `46a593de-db93-412e-952b-2bc065980e7f` shows `prompt_format="fim"` + `ai_inline_completion_request` (`system_prompt_tokens=1075`, `prefix_tokens=2016`, `suffix_tokens=512`).
  - GPT-5: `.artifacts/inline-completion-verify-gpt5.log` correlation `79bbf574-96d5-4020-af0d-f9ac36b3af5a` shows `prompt_format="delimited"` + `ai_inline_completion_request` (`system_prompt_tokens=875`, `prefix_tokens=1904`, `suffix_tokens=512`).
- Quality gates:
  - `pdm run pytest -q tests/unit/infrastructure/llm/test_openai_payloads.py tests/unit/infrastructure/llm/test_openai_chat_ops_provider_grammar.py`
  - `pdm run lint`
  - `pdm run typecheck`
  - `pdm run pytest -q tests/unit/infrastructure/runner/test_docker_runner_execute.py tests/unit/infrastructure/runner/test_docker_runner_adoption.py tests/unit/infrastructure/runner/test_runner_contract_seams.py`
  - `pdm run test`
  - `pdm run docs-validate`
  - `pdm run fe-test`
  - `pdm run fe-test-coverage`
  - `pdm run fe-build`
  - `pdm run docs-validate`

## How to Run

```bash
# Setup
docker compose up -d db && pdm run db-upgrade

# Development (backend + SPA)
ARTIFACTS_ROOT=/tmp/skriptoteket/artifacts pdm run dev-local

# Quality gates
pdm run lint
pdm run typecheck
pdm run test
pdm run fe-test
```

## Known Issues / Risks

- Local Devstral inline completions remain slow (~8–9s provider_ms in logs) and still return off-target blocks in long-script holes.
- Playwright on macOS may require escalated permissions (MachPortRendezvous).

## Next Steps

- Consider reducing system prompt weight or adding explicit local context metadata to improve completion relevance.
