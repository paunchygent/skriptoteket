# Session Handoff

Keep this file updated so the next session can pick up work quickly.

## Editing Rules (do not break structure)

- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files instead.
- Never include secrets/tokens/passwords or personal data.
- If you need to write a **chat message** to a new developer/agent, use `.agent/next-session-instruction-prompt-template.md` instead (this file is not that message).

## Snapshot

- Date: 2025-12-15
- Branch / commit: `main` (HEAD `cc78d48`, dirty working tree)
- Goal of the session: Button/UI consistency audit across all templates - ensure uniform button behavior and sizing.

## What changed

### Current session (EPIC-05 Review & Refinement)

**Completed ST-05-06 (Toast + HTMX Loading)**:
- Created `src/skriptoteket/web/templates/partials/toast.html` with OOB swap pattern
- Added auto-dismiss JS to `base.html` (5 second delay, fade-out animation)
- Spinner CSS already existed in `app.css` (`.huleedu-spinner`, `.htmx-indicator`)

**Design Fixes & Refinements**:
- Fixed button display bug: `.huleedu-list-item a` was overriding `.huleedu-btn` with `display: flex`
  - Added specificity override in `app.css` lines 387-397 for both `.huleedu-btn` and `.huleedu-link`
- Added header separator: vertical line between logo and nav (`.huleedu-header-separator`)
  - Updated `base.html` lines 19-33 with separator span and `huleedu-flex-center` wrapper
  - Added CSS in `app.css` lines 151-156
- Restructured `admin_tools.html` from list to table layout (`.huleedu-table`)
  - Columns: Verktyg, Status, Aktiv version, Actions
  - Status dots for published/unpublished state
- Fixed sticky hover on large CTA buttons:
  - Large buttons (not `.huleedu-btn-sm`) no longer change color on hover
  - Uses `opacity: 0.9` instead to avoid sticky hover state on touch devices
  - Added CSS in `app.css` lines 179-191
- Ensured consistent button sizing across templates:
  - Added `huleedu-min-w-32` to action buttons in `admin/script_editor.html` and `suggestions_review_detail.html`.
  - Added `huleedu-w-full` to the login button in `login.html`.
  - Added `huleedu-min-w-32` to the submit button in `suggestions_new.html`.

**Files Modified**:
- `src/skriptoteket/web/static/css/app.css` (button fixes, header separator, CTA hover)
- `src/skriptoteket/web/templates/base.html` (header separator, toast auto-dismiss JS)
- `src/skriptoteket/web/templates/admin_tools.html` (table layout)
- `src/skriptoteket/web/templates/partials/toast.html` (NEW)
- `src/skriptoteket/web/templates/admin/script_editor.html` (button sizing)
- `src/skriptoteket/web/templates/suggestions_review_detail.html` (button sizing)
- `src/skriptoteket/web/templates/login.html` (button sizing)
- `src/skriptoteket/web/templates/suggestions_new.html` (button sizing)
- `docs/backlog/stories/story-05-06-htmx-enhancements.md` (status: done)

### Previous session (ST-04-04 QC)

- Katalog-metadata (titel/sammanfattning) separerat från skript-källkod + enkel admin-UI för uppdatering:
  - `src/skriptoteket/application/catalog/commands.py` (`UpdateToolMetadataCommand/Result`)
  - `src/skriptoteket/application/catalog/handlers/update_tool_metadata.py`
  - `src/skriptoteket/protocols/catalog.py` (`UpdateToolMetadataHandlerProtocol`, `ToolRepositoryProtocol.update_metadata`)
  - `src/skriptoteket/infrastructure/repositories/tool_repository.py` (`update_metadata`)
  - `src/skriptoteket/web/pages/admin_scripting.py` (`POST /admin/tools/{tool_id}/metadata`)
  - `src/skriptoteket/web/templates/admin/script_editor.html` (kort: “Verktygsmetadata”)
- Svensk UI-copy i admin-skripteditor + state/status-labels:
  - `src/skriptoteket/web/ui_text.py` (labels + `ui_error_message`)
  - `src/skriptoteket/web/templating.py` (Jinja-filter: `version_state_label`, `run_status_label`)
  - `src/skriptoteket/web/templates/admin/script_editor.html`
  - `src/skriptoteket/web/templates/admin/partials/version_list.html`
  - `src/skriptoteket/web/templates/admin/partials/run_result.html`
  - `src/skriptoteket/web/pages/admin_scripting.py`, `src/skriptoteket/web/pages/admin_scripting_runs.py` (UI-feltexter)
  - `src/skriptoteket/web/middleware/error_handler.py` (svensk feltext för HTML-svar)
- Docs:
  - `docs/backlog/stories/story-04-04-governance-audit-rollback.md` (noterar metadata-separation + regressiontest)
- Tests:
  - `tests/integration/web/test_admin_tool_metadata_routes.py` (regression: Katalog visar tool-metadata, inte kod)

### EPIC-05: HuleEdu Design System Harmonization (IN PROGRESS)

- **Completed ST-05-01 (CSS/base template)**:
  - `src/skriptoteket/web/templates/base.html` updated with:
    - `hx-boost="true"` for global SPA-like navigation
    - Linked `/static/css/app.css` (HuleEdu tokens + app extensions)
    - Google Fonts preconnects (IBM Plex family)
    - HuleEdu layout structure (`.huleedu-frame`, `.huleedu-header`, `.huleedu-main`)
    - Toast container (`#toast-container`)
  - `src/skriptoteket/web/static/css/huleedu-design-tokens.css` - full design tokens
  - `src/skriptoteket/web/static/css/app.css` - application CSS

- **Completed ST-05-02 (Simple template migration)**:
  - `src/skriptoteket/web/templates/login.html` converted to HuleEdu card, input, and button classes.
  - `src/skriptoteket/web/templates/home.html` converted to HuleEdu card and link classes.
  - `src/skriptoteket/web/templates/error.html` converted to HuleEdu styling with burgundy accent.

- **Completed ST-05-03 (Browse template migration)**:
  - `src/skriptoteket/web/templates/browse_professions.html` converted to `huleedu-card`, `huleedu-list`, `huleedu-list-item`.
  - `src/skriptoteket/web/templates/browse_categories.html` converted with `huleedu-link` for back navigation.
  - `src/skriptoteket/web/templates/browse_tools.html` converted with `huleedu-muted` for summaries and empty state.

- **Completed ST-05-04 (Suggestion template migration)**:
  - `src/skriptoteket/web/templates/suggestions_new.html` converted with `huleedu-checkbox-group`, `huleedu-form-group`, proper label/input classes.
  - `src/skriptoteket/web/templates/suggestions_review_queue.html` converted with status dots (`huleedu-dot-active`/`huleedu-dot-success`), `huleedu-list-item`.
  - `src/skriptoteket/web/templates/suggestions_review_detail.html` converted with `huleedu-radio-group`, `huleedu-checkbox-group`, form styling.

- **Completed ST-05-05 (Admin template migration)**:
  - `src/skriptoteket/web/templates/admin_tools.html` converted with `huleedu-list-item`, button hierarchy (Publicera=burgundy CTA, Avpublicera=secondary), "Öppna skripteditor" changed from link to navy button.
  - `src/skriptoteket/web/templates/admin/script_editor.html` removed inline `<style>` block, uses `huleedu-editor-layout`, `huleedu-pill`, `huleedu-card-flat` for nested sections.
  - `src/skriptoteket/web/templates/admin/partials/version_list.html` converted with `huleedu-list`, `huleedu-badge` for state labels.
  - `src/skriptoteket/web/templates/admin/partials/run_result.html` converted with `huleedu-card` (brutal shadow), `huleedu-pill` for status.
  - `src/skriptoteket/web/static/css/app.css` added `huleedu-min-w-32` utility for consistent button widths.

### Previous session (ST-04-04 QC)

- ST-04-04 docs status updates:
  - `docs/adr/adr-0014-versioning-and-single-active.md` (implementation status)
  - `docs/backlog/stories/story-04-04-governance-audit-rollback.md` (status/progress notes)
- Deferred governance options for future epics:
  - `docs/reference/ref-scripting-governance-deferred-options.md` (hard reject, review queue, decision log, email notifications)
- Story + contracts:
  - `docs/backlog/stories/story-04-03-admin-script-editor-ui.md` (status: done; records UI/asset decisions)
  - `docs/reference/ref-scripting-api-contracts.md` (clarifies v0.1 `/admin/...` is HTML/HTMX UI; JSON DTOs are conceptual)
- Application handlers + commands (draft lifecycle + sandbox):
  - `src/skriptoteket/application/scripting/commands.py`
  - `src/skriptoteket/application/scripting/handlers/publish_version.py`
  - `src/skriptoteket/application/scripting/handlers/request_changes.py`
  - `src/skriptoteket/application/scripting/handlers/create_draft_version.py`
  - `src/skriptoteket/application/scripting/handlers/save_draft_version.py` (expected-parent draft head check)
  - `src/skriptoteket/application/scripting/handlers/submit_for_review.py`
  - `src/skriptoteket/application/scripting/handlers/run_sandbox.py` (reuses `ExecuteToolVersionHandler` with SANDBOX context)
  - `src/skriptoteket/application/scripting/handlers/execute_tool_version.py` (preflight `compile(...)`; `SyntaxError` -> FAILED run without Docker)
- Protocols + DI:
  - `src/skriptoteket/protocols/scripting.py`
  - `src/skriptoteket/protocols/catalog.py` (`ToolRepositoryProtocol.set_active_version_id`)
  - `src/skriptoteket/di.py`
  - `src/skriptoteket/infrastructure/repositories/tool_repository.py` (`PostgreSQLToolRepository.set_active_version_id`)
- Web UI (server-rendered + HTMX):
  - `src/skriptoteket/web/pages/admin_scripting.py` (editor + draft routes; includes publish + request-changes; includes run router)
  - `src/skriptoteket/web/pages/admin_scripting_runs.py` (sandbox run + run refresh + artifact download)
  - `src/skriptoteket/web/pages/admin_scripting_support.py` (shared helpers)
  - `src/skriptoteket/web/router.py` (includes admin scripting pages)
  - `src/skriptoteket/web/app.py` (mounts `/static`)
  - `src/skriptoteket/web/templates/admin/script_editor.html` (adds Review version card for IN_REVIEW + admin/superuser)
  - `src/skriptoteket/web/templates/admin/partials/version_list.html`
  - `src/skriptoteket/web/templates/admin/partials/run_result.html`
  - `src/skriptoteket/web/templates/admin_tools.html` (adds “Öppna skripteditor” link)
  - `src/skriptoteket/web/templates/base.html` (adds HTMX include + extension blocks; fixes checkbox/radio input styling)
  - `src/skriptoteket/web/static/vendor/` (vendored CodeMirror + HTMX; pinned versions in `README.md`)
- Quality fixes uncovered by QC:
  - `src/skriptoteket/infrastructure/runner/docker_runner.py` (mypy-friendly typing for docker client interactions)
  - `tests/unit/infrastructure/runner/test_retention.py`, `tests/unit/infrastructure/runner/test_docker_runner_utils.py`
- Tests:
  - `tests/unit/application/test_scripting_execute_tool_version_handler.py` (runner not called on `SyntaxError`)
  - `tests/unit/application/test_scripting_draft_handlers.py` (draft save concurrency guard)
  - `tests/unit/application/test_scripting_review_handlers.py` (publish + request-changes)
  - `tests/integration/web/test_admin_scripting_review_routes.py` (POST routes)

## Decisions (and links)

- **HuleEdu Design System** (ADR-0017): Adopt full HuleEdu design tokens for future integration compatibility. Uses Google Fonts CDN for IBM Plex family. Grid background pattern at 4% opacity included.
- Editor UX: integrate CodeMirror now (no plain textarea-only MVP); keep `<textarea>` as fallback and for form submission.
- Assets: vendor pinned JS/CSS under `src/skriptoteket/web/static/vendor/` (no CDN at runtime).
- Execution UX: HTMX used for sandbox run result updates (partial HTML under `templates/admin/partials/`).
- Safety: preflight `compile(...)` prevents Docker runs for syntax errors and returns a FAILED run with actionable `error_summary`.
- ST-04-04 publish/reject workflow decisions are pending (reject semantics + review queue + notifications); see `docs/backlog/stories/story-04-04-governance-audit-rollback.md`.

## How to run / verify

- Start dev stack (ran): `pdm run dev-start`
- Run migrations (ran): `docker compose -f compose.yaml -f compose.dev.yaml exec -T web pdm run db-upgrade`
- Build runner image (optional, needed for sandbox/prod execution): `docker build -f Dockerfile.runner -t skriptoteket-runner:latest .`
- Live functional check (ran, no secrets/tokens recorded):
  - Seeded a temporary admin session + 2 draft tools + 2 `IN_REVIEW` versions via one-off script inside the web container.
  - Verified via `curl` (with the temporary session cookie) that:
    - `GET /admin/tool-versions/{in_review_id}` returns 200 and includes “Review version” card for admin.
    - `POST /admin/tool-versions/{in_review_id}/publish` returns 303, redirect page shows `active`, and `/admin/tools/{tool_id}` shows `active_version_id` set (not `—`).
    - `POST /admin/tool-versions/{in_review_id}/request-changes` returns 303, redirect page shows `draft`, and the “Review version” card is not shown.
- Live functional check (ran, current session):
  - Verified in browser (manual): uppdaterade “Verktygsmetadata” (titel + sammanfattning) i skripteditor och såg att Katalog visar den nya sammanfattningen (inte gammal skript-body).
  - Verified via `curl` (med temporär admin-session-cookie) att `/admin/tool-versions/{version_id}` innehåller svensk UI-copy:
    - status-label “För granskning”, rubrikerna “Skicka för granskning” och “Granska version”, samt “Startfunktion” och “Ändringssammanfattning”.
- QC gates (ran): `pdm run lint-fix && pdm run lint && pdm run typecheck && pdm run test && pdm run docs-validate`
- QC gates (ran, current session): `pdm run lint && pdm run typecheck && pdm run test && pdm run docs-validate`
- Sanity (ran): `python -m py_compile src/skriptoteket/application/scripting/commands.py src/skriptoteket/protocols/scripting.py src/skriptoteket/protocols/catalog.py src/skriptoteket/infrastructure/repositories/tool_repository.py src/skriptoteket/di.py`

## Known issues / risks

- Rollback workflow is still missing (Superuser-only; out of this session scope).
- `/work` per-run volume does not have a portable per-run size cap (unlike tmpfs); a buggy/malicious script can fill disk.
- docker.sock mount expands blast radius if the app container is compromised (keep production opt-in and hardened).
- Contributor discoverability: contributors can access the editor only if they have the direct `/admin/tools/{tool_id}` URL
  (no “My tools” list yet).

## Next steps (recommended order)

### EPIC-05: Button/UI Consistency Audit (IN PROGRESS)

**Status**: Stories ST-05-01 through ST-05-06 complete. Refinement pass needed for button consistency.

**Remaining work**:
1. Audit ALL 15 templates for button class consistency (COMPLETED)
2. Ensure uniform `min-width` on action buttons in rows (COMPLETED)
3. Verify header "Logga ut" stays fixed on resize (VERIFIED - flex-shrink: 0 is correct)
4. Verify `suggestions_review_queue.html` matches `admin_tools.html` pattern (VERIFIED - uses huleedu-tool-list)

**Templates to audit** (in priority order):
- [X] `base.html` - header logout button
- [X] `admin_tools.html` - action buttons (partially fixed)
- [X] `suggestions_review_queue.html` - "Öppna" buttons
- [X] `suggestions_review_detail.html` - action buttons
- [X] `admin/script_editor.html` - multiple action buttons
- [X] `admin/partials/version_list.html` - version actions (No buttons found, implicitly consistent)
- [X] `login.html` - "Logga in" CTA
- [X] `suggestions_new.html` - "Skicka förslag" CTA
- [X] Browse templates (3 files) - navigation links (No buttons found, implicitly consistent)

**Button CSS reference** (`app.css` lines 171-229):
- `.huleedu-btn` = burgundy CTA
- `.huleedu-btn-navy` = navy functional
- `.huleedu-btn-secondary` = outline
- `.huleedu-btn-sm` = small variant
- `.huleedu-tool-actions .huleedu-btn { min-width: 130px; }` = row consistency

### Other

1. Implement rollback (Superuser-only) if scope expands (handler + route + UI).
2. Consider artifact size caps (max bytes per file/total) and/or operational disk quotas.

## Notes

- Do not include secrets/tokens in this file.
