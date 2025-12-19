# Session Handoff

Keep this file updated so the next session can pick up work quickly.

## Editing Rules (do not break structure)

- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files instead.
- Never include secrets/tokens/passwords or personal data.
- If you need to write a **chat message** to a new developer/agent, use `.agent/next-session-instruction-prompt-template.md` instead (this file is not that message).
- Keep this file under 200 lines; move history to `.agent/readme-first.md` + `docs/`.

## Snapshot

- Date: 2025-12-19
- Branch / commit: `main` @ `5dd5b5a` (plus local uncommitted changes)
- Current sprint: `docs/backlog/sprints/sprint-2025-12-22-ui-contract-and-curated-apps.md`
- Backend now: ST-10-03 Session B (implement deterministic `UiPayloadNormalizerProtocol`)
- Frontend now: N/A (completed work moved to `.agent/readme-first.md`)
- Goal of next session: implement the normalizer + determinism tests (ST-10-03)

## 2025-12-19 ST-05-12 Mobile Editor Scroll Follow-up (IN PROGRESS)

- Parked/not sprint-critical; keep details in `docs/backlog/stories/story-05-12-mobile-editor-ux.md` and `.agent/readme-first.md`.

## 2025-12-19 ST-05-12 Mobile Editor UX Issues (DONE)

- Completed; details live in `docs/backlog/stories/story-05-12-mobile-editor-ux.md`.

## 2025-12-19 ST-05-11 Hamburger Menu Fix (DONE)

- Completed; details live in `docs/backlog/stories/story-05-11-hamburger-htmx-bug.md`.

## What changed

- This handoff is intentionally compressed to current sprint-critical work only (see `.agent/readme-first.md` for history).
- Backend: contract v2 seams/policies/models/tests added (see `## 2025-12-19 SPR-2025-12-22 Session A (DONE)` below).

### Current session (EPIC-05 Responsive Frontend: ST-05-07, ST-05-08, ST-05-10)

- Archived; completed story details live in `.agent/readme-first.md` + story docs under `docs/backlog/stories/`.

### Previous session (ST-06-08 Editor UI fixes: sizing, borders, CodeMirror init, file input)

- Archived; see `.agent/readme-first.md` (links only) and the story docs.

### Current session (ST-04-04 continuation - Maintainer Admin + My Tools + Rollback)

- Archived; see story docs under `docs/backlog/stories/`.

### Previous session (ST-04-05 User execution of active tools)

- Archived; see story docs under `docs/backlog/stories/`.

### Previous session (ST-04-04 Contributor iteration after publication)

- Archived; see story docs under `docs/backlog/stories/`.

### Current session (ST-06-06 Test warnings hygiene)

- Archived; see `.agent/readme-first.md`.

### Current session (ST-06-05 Web pages router test coverage)

- Archived; see `.agent/readme-first.md`.

### Previous session (ST-04-04 QC)

- Archived; see `.agent/readme-first.md`.

### EPIC-05: HuleEdu Design System Harmonization (IN PROGRESS)

- Not in current sprint scope; see `docs/backlog/epics/epic-05-huleedu-design-harmonization.md`.

### Previous session (ST-04-04 QC)

- Archived; see `.agent/readme-first.md`.

## Decisions (and links)

- Contract v2 allowlists (ADR-0022): outputs `notice|markdown|table|json|html_sandboxed` (+ `vega_lite` curated-only); action fields `string|text|integer|number|boolean|enum|multi_enum`.
- Normalizer returns combined result `{ui_payload, state}` via `UiNormalizationResult` (ADR-0024).
- Policy budgets/caps approved (default vs curated) in `src/skriptoteket/domain/scripting/ui/policy.py`.
- `vega_lite` enabled in curated policy now; restrictions MUST be implemented before the platform accepts/renders it (ADR-0024 risk).

## How to run / verify

- Canonical local recipe: see `.agent/readme-first.md` (includes `ARTIFACTS_ROOT` note).
- Quality gates: `pdm run lint` (runs Ruff + agent-doc budgets + docs-validate), then `pdm run test`.
- Session A checks: `pdm run pytest tests/unit/domain/scripting/ui`.

## Known issues / risks

- `vega_lite` restrictions are not implemented yet; do not accept/render vega-lite outputs until restrictions exist (ADR-0024).

## Next steps (recommended order)

- Backend: implement deterministic `UiPayloadNormalizerProtocol` implementation + unit tests (ST-10-03 Session B).
- Backend: Session C will add persistence + migrations (out of scope until explicitly started).

### ST-04-04 COMPLETED

- Archived; see story docs under `docs/backlog/stories/`.

### EPIC-05: Button/UI Consistency Audit (IN PROGRESS)

- Archived/not sprint-critical; see `.agent/readme-first.md`.

### Other

- Keep `.agent/handoff.md` under 200 lines; keep `.agent/readme-first.md` under 300 lines (enforced by pre-commit).

## Notes

- Old/completed story detail belongs in `.agent/readme-first.md` (links only) + `docs/backlog/stories/`.

## 2025-12-19 Security Hardening (EPIC-09)

- Not sprint-critical; see `docs/backlog/epics/epic-09-security-hardening.md` + `docs/runbooks/`.

## 2025-12-17 Production Deployment (COMPLETE)

- Not sprint-critical; keep deployment procedures in `docs/runbooks/` (do not store personal data here).

## 2025-12-17 ST-05-07 Frontend Stabilisering (ny story)

- Completed/archived; see `docs/backlog/stories/story-05-07-frontend-stabilization.md`.

### Nästa sessions uppdrag

- Archived; see story doc.

### Relevanta filer

- Archived; see story doc.

## 2025-12-17 Editor/UI fixes (live check)

- Not sprint-critical; keep canonical live-check recipe in `.agent/readme-first.md` and story docs.

## 2025-12-19 SPR-2025-12-22 Session A (DONE)

- Scope: contract/policy seams only (no DB/API/runner/UI changes).
- Protocol seams: `src/skriptoteket/protocols/tool_ui.py`
- Contract v2 models: `src/skriptoteket/domain/scripting/ui/contract_v2.py`
- Policy profiles + caps: `src/skriptoteket/domain/scripting/ui/policy.py`
- Normalization result type: `src/skriptoteket/domain/scripting/ui/normalization.py`
- Tests: `tests/unit/domain/scripting/ui/test_policy_profiles.py`, `tests/unit/domain/scripting/ui/test_contract_v2_models.py`
- Docs: `docs/adr/adr-0022-tool-ui-contract-v2.md`, `docs/adr/adr-0024-tool-sessions-and-ui-payload-persistence.md`, `docs/backlog/stories/story-10-03-ui-payload-normalizer.md`
