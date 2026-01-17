# Session Handoff

Keep this file updated so the next session can pick up work quickly.

## Editing Rules (do not break structure)

- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files instead.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines; move history to `.agent/readme-first.md` + `docs/`.

## Snapshot

- Date: 2026-01-17
- Branch: `main` + local changes
- Current sprint: None (between sprints; last: `SPR-2026-01-05` (done))
- Production: Full Vue SPA
- Completed: recent — ST-14-11/12 done; ST-14-19 done; ST-14-20 done; ST-14-23 done; ST-08-24 done; ST-08-28 done; ST-08-29 done (history: `.agent/readme-first.md`)

## Current Session (2026-01-17)

- PR-0033 SRP refactors complete + perf polish (help topic loading/prefetch, diff parse cache + early-exit, redundant newline normalization removed); see `docs/backlog/prs/pr-0033-large-file-srp-refactors-help-panel-docker-runner-edit-ops.md`.
- Execution queue planning drafted: ADR-0062 (proposed), EPIC-18 (proposed), ST-18-01 (ready), PR-0039 (ready), review pending; `docs/index.md` updated.
- Verification:
  - `pdm run fe-gen-api-types`
  - `pdm run fe-type-check`
  - `pdm run fe-test`
  - `pdm run fe-build`
  - `pdm run format`
  - `pdm run lint`
  - `pdm run test`
  - `pdm run docs-validate`
  - `BASE_URL=http://127.0.0.1:5173 pdm run ui-smoke` (escalated)
  - `BASE_URL=http://127.0.0.1:5173 pdm run ui-editor-smoke` (escalated)
  - Manual (earlier in session): `pdm run dev-local` → verified `/` (Home), opened Help panel, opened `/admin/tools/:toolId` editor view.

## How to Run

```bash
# Setup
docker compose up -d db && pdm run db-upgrade

# Development
pdm run dev                 # Backend 127.0.0.1:8000

# Quality gates
pdm run format
pdm run lint
pdm run typecheck
pdm run test
```

## Known Issues / Risks

- Large local worktree from PR-0033 refactors; verify intent before staging changes outside that scope.
- ADR-0062 / EPIC-18 are proposed and require review approval before implementation.

## Next Steps

- Continue PR-0033 SRP refactors and update its PR checklist.
- Run `pdm run docs-validate` for the new ADR/epic/story/PR/review docs.
- Start review for EPIC-18; flip ADR-0062 to `accepted` after approval.
