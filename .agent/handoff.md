# Session Handoff

Keep this file updated so the next session can pick up work quickly.

## Editing Rules (do not break structure)

- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files instead.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines; move history to `.agent/readme-first.md` + `docs/`.

## Snapshot

- Date: 2026-01-18
- Branch: `main` + local changes
- Current sprint: None (between sprints; last: `SPR-2026-01-05` (done))
- Production: Full Vue SPA
- Completed: recent — ST-14-11/12 done; ST-14-19 done; ST-14-20 done; ST-14-23 done; ST-08-24 done; ST-08-28 done; ST-08-29 done (history: `.agent/readme-first.md`)

## Current Session (2026-01-18)

- Execution queue implementation in progress: ST-18-01 / PR-0039 (Postgres `tool_run_jobs` + worker loop + adopt-first stale-lease recovery); see `docs/backlog/prs/pr-0039-execution-queue-worker-loop.md`.
  - Key files: `src/skriptoteket/workers/execution_queue_worker.py`, `src/skriptoteket/infrastructure/repositories/tool_run_job_repository.py`, `migrations/versions/0027_tool_run_jobs_execution_queue.py`.
- SPA updated for queued runs (polling + status rendering + timestamps); see `frontend/apps/skriptoteket/src/views/MyRunsListView.vue` and `frontend/apps/skriptoteket/src/views/ToolRunView.vue`.
- Docs status: ADR-0062 accepted, EPIC-18 active, review approved; ST-18-01 / PR-0039 set to `in_progress`.
- Verification:
  - `pdm run test`
  - `pdm run pytest -m docker --override-ini addopts=''`
  - `pdm run fe-test`
  - `pdm run typecheck`
  - `pdm run format`
  - `pdm run lint`
  - `pdm run docs-validate`
  - Manual: `docker compose up -d db && pdm run db-upgrade`
  - Manual: `ARTIFACTS_ROOT=/tmp/skriptoteket/artifacts pdm run dev-local` (backend `http://127.0.0.1:8000`, SPA `http://127.0.0.1:5173`)
  - Manual: `curl -s -o /dev/null -w '%{http_code} %{content_type}\\n' http://127.0.0.1:5173/`
  - Manual: `curl -s -o /dev/null -w '%{http_code} %{content_type}\\n' http://127.0.0.1:5173/my/runs`
  - Manual: `curl -s -o /dev/null -w '%{http_code} %{content_type}\\n' http://127.0.0.1:8000/openapi.json`

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

- Large local worktree from PR-0033 refactors; verify intent before staging changes outside that scope.
- Queue-enabled runs require a worker process; if `RUNNER_QUEUE_ENABLED` is enabled without `run-execution-worker` running, runs will remain `queued`.

## Next Steps

- Finish PR-0039 checklists + rollout notes, then move ST-18-01 / PR-0039 to `done`.
- Execute PR-0040 (execution queue test coverage): `docs/backlog/prs/pr-0040-execution-queue-test-coverage.md`.
