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
- Branch / commit: `main` (HEAD; clean working tree)
- Goal of the session: Align EPIC-04 dynamic scripting architecture/docs end-to-end (runner/storage/versioning/RBAC/user run) and resolve cross-epic story mismatches; apply minimal code changes required by the updated contracts.

## What changed

- Added/updated EPIC-04 docs: ADR-0012/0013/0014, EPIC-04, ST-04-01..05, and reference specs/contracts:
  - `docs/adr/adr-0012-script-source-storage.md`
  - `docs/adr/adr-0013-execution-ephemeral-docker.md`
  - `docs/adr/adr-0014-versioning-and-single-active.md`
  - `docs/backlog/epics/epic-04-dynamic-tool-scripts.md`
  - `docs/backlog/stories/story-04-01-versioned-script-model.md`
  - `docs/backlog/stories/story-04-02-docker-runner-execution.md`
  - `docs/backlog/stories/story-04-03-admin-script-editor-ui.md`
  - `docs/backlog/stories/story-04-04-governance-audit-rollback.md`
  - `docs/backlog/stories/story-04-05-user-execution.md`
  - `docs/reference/ref-dynamic-tool-scripts.md` (includes lifecycle map linking ST-03-03 + ST-04-04)
  - `docs/reference/ref-scripting-api-contracts.md` (includes user endpoints)
- Resolved EPIC-02/03/04 story alignment:
  - Expanded ST-02-02 acceptance criteria: `docs/backlog/stories/story-02-02-admin-nomination-and-superuser-approval.md`
  - Renamed and clarified ST-03-03 as tool visibility (not script versions): `docs/backlog/stories/story-03-03-publish-and-depublish-tools.md`
  - Updated EPIC-03 wording to reflect tool governance vs script versioning: `docs/backlog/epics/epic-03-script-governance-workflow.md`
- Applied minimal code changes required by updated contracts:
  - `src/skriptoteket/domain/catalog/models.py` (Tool now includes `is_published` + `active_version_id`)
  - `src/skriptoteket/protocols/catalog.py` (`ToolRepositoryProtocol.get_by_id/get_by_slug`)
  - `src/skriptoteket/infrastructure/repositories/tool_repository.py` (implements the new methods)
- Repo guidance: added “no unapproved reverts” rule: `AGENTS.md`

## Decisions (and links)

- Execution: sibling runner containers controlled via Docker SDK over `docker.sock` (no host-path bind mounts); hardened runner (non-root, cap-drop, no-new-privileges, pids-limit, read-only root + writable tmpfs/volumes). See `docs/adr/adr-0013-execution-ephemeral-docker.md` and `docs/backlog/stories/story-04-02-docker-runner-execution.md`.
- Storage: hybrid (DB stores source + stdout/stderr/html_output; binaries on disk with retention cleanup; production inputs not retained by default). See `docs/adr/adr-0012-script-source-storage.md`.
- Versioning: append-only; publish is copy-on-activate and archives the reviewed `in_review` version (publish “consumes” it). See `docs/adr/adr-0014-versioning-and-single-active.md` and `docs/backlog/stories/story-04-04-governance-audit-rollback.md`.
- Governance: Admins can publish tool visibility and script versions; Superuser rollback only. “Published implies runnable” (requires `tools.active_version_id`). See `docs/backlog/stories/story-03-03-publish-and-depublish-tools.md` and `docs/reference/ref-dynamic-tool-scripts.md`.

## How to run / verify

- Quality gates (run this session): `pdm run docs-validate && pdm run lint && pdm run typecheck && pdm run test`

## Known issues / risks

- Docker `docker.sock` mount expands blast radius; plan for a dedicated runner service/host in the future (ADR-0013).
- ST-03-03 “publish tool” depends on ST-04-01 `active_version_id` being present (published implies runnable).
- Production runs default to `--network none` and inject no secrets in v0.2; per-tool network/secrets are deferred.

## Next steps (recommended order)

1. Implement ST-04-01 end-to-end: `tool_versions` + `tool_runs` + `tools.active_version_id` migration, domain models/state transitions, protocols, repositories, and required migration idempotency test.
2. Implement ST-03-03 publish/depublish tool visibility with the guard “published implies runnable” (`active_version_id != null`) + minimal admin UI.
3. Implement ST-04-02 runner: Docker SDK sibling runner (archive copy I/O), runner image, artifact persistence + retention cleanup.
4. Implement ST-04-03 admin script editor UI (create/save/submit-review/run-sandbox).
5. Implement ST-04-04 governance handlers (publish/rollback) and policies.
6. Implement ST-04-05 user run pages (`/tools/{slug}/run`, `/my-runs/{run_id}`) and 404 rules for unpublished tools.

## Notes

- Do not include secrets/tokens in this file.
- Relevant commits for this work: `901f50b`, `b0b2b09`, `96dedbd`.
