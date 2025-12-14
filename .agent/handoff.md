# Session Handoff

Keep this file updated so the next session can pick up work quickly.

## Editing Rules (do not break structure)

- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files instead.
- Never include secrets/tokens/passwords or personal data.
- If you need to write a **chat message** to a new developer/agent, use `.agent/next-session-instruction-prompt-template.md` instead (this file is not that message).

## Snapshot

- Date: 2025-12-14
- Branch / commit: `main` (HEAD)
- Goal of the session: Implement ST-04-01 “Versioned script model” end-to-end (migration + domain + protocols + repos + DI + tests incl. required migration idempotency test).

## What changed

- Updated docs to clarify submission audit and artifact paths:
  - `docs/backlog/stories/story-04-01-versioned-script-model.md` (status: done)
  - `docs/reference/ref-dynamic-tool-scripts.md`
  - `docs/reference/ref-scripting-api-contracts.md`
- Added migration + REQUIRED Testcontainers idempotency test:
  - `migrations/versions/0005_tool_versions.py` (`tool_versions`, `tool_runs`, `tools.active_version_id`)
  - `tests/integration/test_migration_0005_tool_versions_idempotent.py`
- Added scripting domain models + transitions:
  - `src/skriptoteket/domain/scripting/models.py`
- Added protocols + infrastructure repositories + DI wiring:
  - `src/skriptoteket/protocols/scripting.py`
  - `src/skriptoteket/infrastructure/db/models/tool_version.py`
  - `src/skriptoteket/infrastructure/db/models/tool_run.py`
  - `src/skriptoteket/infrastructure/db/models/tool.py` (adds `active_version_id`)
  - `src/skriptoteket/infrastructure/repositories/tool_version_repository.py`
  - `src/skriptoteket/infrastructure/repositories/tool_run_repository.py`
  - `src/skriptoteket/di.py` (register new repos)
  - `src/skriptoteket/infrastructure/repositories/tool_repository.py` (set `active_version_id` on draft creation)
- Added domain unit tests:
  - `tests/unit/domain/scripting/test_models.py`

## Decisions (and links)

- Submission audit uses dedicated fields (`submitted_for_review_by_user_id`, `submitted_for_review_at`) and does not overload reviewer fields. See `docs/reference/ref-dynamic-tool-scripts.md`.
- Audit user FKs (`created_*`, `submitted_for_review_*`, `reviewed_*`, `published_*`, `requested_*`) use `ON DELETE RESTRICT` to preserve history. See `docs/reference/ref-dynamic-tool-scripts.md`.
- Version uniqueness:
  - `UNIQUE (tool_id, version_number)`
  - Partial unique: one active per tool (`WHERE state='active'`)
  See `docs/backlog/stories/story-04-01-versioned-script-model.md` and `migrations/versions/0005_tool_versions.py`.
- `tool_runs.version_id` uses default `NO ACTION` (restrictive, cascade-safe); `artifacts_manifest` is `JSONB NOT NULL DEFAULT '{}'::jsonb`. See `migrations/versions/0005_tool_versions.py`.
- `tool_runs.workdir_path` is stored as a relative key under the artifacts root (not an absolute host path). See `docs/reference/ref-dynamic-tool-scripts.md`.

## How to run / verify

- Quality gates (ran): `pdm run format && pdm run lint && pdm run typecheck && pdm run test && pdm run docs-validate`
- REQUIRED migration idempotency tests (ran; requires Docker): `pdm run pytest -m docker --override-ini addopts=''`
- UI functional checks: not applicable (no UI/routes changed)

## Known issues / risks

- Docker-marked tests require access to the local Docker daemon (may need elevated permissions in sandboxed environments).
- ST-03-03 and later UI flows still need to enforce “published implies runnable” (active version must exist).

## Next steps (recommended order)

1. Confirm with the user before starting any ST-03-03 or runner/UI work (session scope rule).
2. Implement ST-03-03 publish/depublish tool visibility with the guard “published implies runnable” (`active_version_id != null`).
3. Implement ST-04-02 runner (Docker SDK sibling runner + artifact persistence/retention).
4. Implement ST-04-03 admin script editor UI (create/save/submit-review/run-sandbox).
5. Implement ST-04-04 governance handlers (publish/rollback/request changes) and policies.
6. Implement ST-04-05 user run pages (`/tools/{slug}/run`, `/my-runs/{run_id}`).

## Notes

- Do not include secrets/tokens in this file.
