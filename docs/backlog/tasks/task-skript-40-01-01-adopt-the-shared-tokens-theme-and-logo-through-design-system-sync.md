---
type: task
id: TASK-SKRIPT-40-01-01
title: Adopt the shared tokens, theme and logo through design-system sync
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-09-27'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- Running repository-governance-frontend-catalog design-system sync against Skriptoteket writes the package tokens, Tailwind theme and horizontal logo to their current Skriptoteket paths as named in the root design-system-map.json, with every other export null, and Skriptoteket's validate command passes
- Skriptoteket docs name the sync command instead of hand copying, and the unused mirror manifest.schema.json is gone
- Frontend type check, unit tests, build and the shared `repository-governance-frontend-catalog design-system validate`, plus a Hemma staging walk of the screens the task touches, pass
dependencies:
- TASK-SKILL-REP-0186
story: ST-SKRIPT-40-01
backlog_document_profile: contract-derived
---

## Implementation Contract

Adopt the 0186 release's tokens, Tailwind theme and horizontal logo through a
real `design-system sync` from clean skill-repository main.

- Root map: `design-system-map.json`; package identity `huleedu-integrated-frontend-design-system`; mirror `frontend/apps/skriptoteket/src/design-system/huleedu-integrated`.
- Map tokens to `src/skriptoteket/web/static/css/huleedu-design-tokens.css`, tailwind-theme to `frontend/apps/skriptoteket/src/styles/tailwind-theme.css`, and skriptoteket-logo-horizontal to `frontend/apps/skriptoteket/public/logo-horizontal.svg`. Every other released export, including ui-dense-spinner, is explicitly null.
- Declare `[tool.repository-governance.design-system]` with map and validate-command `pdm run design-system-validate`. Add that PDM script around the real shared `design-system validate`, without no-op or bootstrap-success branches.
- Parent commits this map/facts/wrapper preparation before installing the new automatic hook. The old mirror and local bytes are not asserted valid at this intermediate checkpoint. Run sync only when map, targets and both mirror files are clean. This preparation checkpoint is covered by the admitted D24 exception and cannot be integrated or deployed as completed delivery.
- Sync writes the release bytes and invokes the real validator. Then add the pre-commit hook covering the root map, mirror, every adopted target, pyproject.toml and hook configuration; delete the unused mirror manifest.schema.json; update bootstrap assertions; replace hand-copy instructions in the frontend design-system codemap reference with sync.
- After task validation, parent commits the coherent result with the hook active. Record clean protected-path status, repeat sync against the same clean source SHA, and require exit 0 with no diff or untracked output. If source main advances, reassess its release and repeat at integration.
- Later adoption tasks follow the same clean checkpoints. A map expansion with an existing hook uses only the admitted bounded manual-stage exception before sync, then restores pre-commit enforcement before the validated result commit. A version-only refresh leaves the hook active and lets sync update the version.

## Contract Inputs

- Retained plan `.orchestration/context/sessions/01a0e42e-f433-727d-a17f-f9eced6d04bc/evidence/planning/TASK-SKRIPT-REP-0033/plan.md`, D1-D6/D16 and admitted D24-D25.
- ST-SKRIPT-40-01; TASK-SKILL-REP-0186 merged with HuleEdu sync/check evidence.
- Continues canceled TASK-SKRIPT-REP-0033, including docs, token paths and schema deletion.
- EPIC-SKRIPT-40 review R6 and sync source `packages/repository_governance/src/repository_governance/frontend_catalog/design_system.py` in skill-repository.

## Core Vertical And Performance

A clean committed adoption map feeds real sync; sync writes all three resources
and metadata; the validator passes; parent commits the validated result with
the automatic hook active; a second clean-state sync produces no changes.
Static CSS/SVG introduces no identified material runtime-performance concern.

## Validation

- Retain source release SHA/version, successful first-sync output, shared validation, protected-path clean status and successful no-diff second-sync output. Do not run the second sync against dirty first-sync output.
- `tests/unit/governance/test_repository_governance_bootstrap.py` asserts the final design-system facts, wrapper and active hook configuration and passes.
- `pdm run fe-type-check`, `pdm run fe-test`, `pdm run fe-build` and `pdm run design-system-validate` pass.
- Hemma staging walk: home, tool list, Klassrumskartan planner and modal; use governed HuleEdu browser-session helpers/preflight.

## Stop Conditions

- Stop for dirty source or protected consumer paths, digest mismatch, incomplete export map, missing 0186 release/HuleEdu evidence, or an unapproved checkpoint exception.
- Stop if a needed token is removed. Preserve command failure evidence if validation fails after sync writes; no automatic rerun, stash, discard, hand copying, validator weakening or dirty-target bypass.
- Do not integrate a map-preparation checkpoint or leave the automatic hook deferred at delivery.

## Decided Contract Terms

| ID | Decided contract term |
| --- | --- |
| D1 | Adopt only tokens, theme and logo; all other release exports are null in this task. Source: retained D2. |
| D2 | Those resources keep their existing paths; the map stays at repository root. Source: retained D6. |
| D3 | A PDM wrapper runs the real shared validator through an automatic pre-commit hook at delivery. Source: retained D4. |
| D4 | Remove unused mirror manifest.schema.json. Source: retained D4. |
| D5 | Codemap documents sync instead of hand copying. Source: retained D4. |
| D6 | Parent owns clean-map, validated-result and repeatability checkpoints under the explicit bootstrap exception. Source: retained D24; R6. |
