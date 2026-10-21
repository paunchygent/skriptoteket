---
type: story
id: ST-SKRIPT-40-01
title: Converge tokens, components and action buttons onto the shared package
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-09-27'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: user
  decided_at: '2026-10-22'
  approval_protocol: agent-planning:user-closure-gate
  approval_evidence: 'The user closed the story on 2026-10-22: TASK-SKRIPT-40-01-01 to TASK-SKRIPT-40-01-04 are done, and the story-level proof on main d9fab7e2 (clean-state repeat sync with no change, frontend and backend suites, migration tests) is recorded in its progress section.'
epic: EPIC-SKRIPT-40
acceptance_criteria:
- The root map adopts tokens, tailwind-theme, horizontal logo, dense-tool-primitives, dense action/icon/status components, dense spinner, segmented toggle, SystemMessage, ToastHost, Vue barrel, ui-glyphs, ui-glyph, ui-symbol and action-buttons; only brand and auth-lifecycle remain null, and clean-state repeat sync changes no file
- The released glyph peer and complete relative-import closure allow Story 1 to typecheck and build without the Story 2 release
- Modal surfaces, secondary tone, busy behavior, equal-width toggle, nullable-string messages with preserved dismissal and announcements, ordered store-backed toasts and inline buttons work from the package without local forks
- Frontend typecheck, unit tests, build and shared design-system validation pass, and the touched workflows pass a Hemma staging walk through the governed HuleEdu browser-session ceremony
links:
  decisions: []
backlog_document_profile: contract-derived
---

## Slice Contract

Adopt shared tokens, theme, logo, dense primitives/components/spinner, segmented
toggle, SystemMessage, ToastHost, Vue barrel and action buttons through sync.
Adopt ui-glyphs, UiGlyph, UiSymbol and the released catalog peer when those
components first require them. Broad semantic icon migration remains Story 2;
Story 1 may temporarily retain `lucide-vue-next` for unmigrated callers.

One prior skill-repository release, TASK-SKILL-REP-0186, supplies every promotion
and syncs HuleEdu without changing existing call-site defaults. Shared Vue
files occupy `src/components/ui/shared/` with components under `components/`;
the existing local UI barrel re-exports the package and local-only components.
Tokens, theme, logo and metadata mirror keep their established paths.

SystemMessage preserves nullable-string text, hiding, dismissal and error
announcements through the agreed optional package API and explicit consumer
attributes. The local toast adapter supplies newest-first props and bottom
placement without changing store state, timers or call sites. No synced file
is locally patched.

## Contract Inputs

- Retained plan `.orchestration/context/sessions/01a0e42e-f433-727d-a17f-f9eced6d04bc/evidence/planning/TASK-SKRIPT-REP-0033/plan.md`, D1-D13/D15-D16 and admitted D19-D25.
- EPIC-SKRIPT-40 and its R1-R6 review repair.
- TASK-SKILL-REP-0186 merged release plus HuleEdu sync/check evidence.
- Canceled TASK-SKRIPT-REP-0033 continues as TASK-SKRIPT-40-01-01 with its token-path, validation, documentation and unused-schema acceptance preserved.

## Tasks

| Order | Task | Outcome |
| --- | --- | --- |
| 0 | TASK-SKILL-REP-0186 | All promotions, explicit spinner export, released SystemMessage contract, HuleEdu sync and checks. |
| 1 | TASK-SKRIPT-40-01-01 | Done 2026-10-12: three-resource adoption, root map, real validator wrapper, clean checkpoints and automatic hook; Hemma staging walk passed at fc42b918. |
| 2 | TASK-SKRIPT-40-01-02 | Complete shared Vue subtree, glyph peer/runtime, import migration, message adaptation and toast adapter. |
| 3 | TASK-SKRIPT-40-01-03 | Shared action-button stylesheet and removal of local button rules. |
| 4 | TASK-SKRIPT-40-01-04 | Adopt huleedu-integrated 0.1.34 through design-system sync. Done 2026-10-22: main `e9983e4f`, F1/F2 fixed `3b91b792`, user closure. |

## Progress

- 2026-10-21 (Hemma orchestrator), story-level proof for closure readiness:
  - Clean-state repeat sync: `repository-governance-frontend-catalog design-system sync` from skill-repository `5cbfeb7f` (the TASK-SKRIPT-40-01-04 D1 source) onto a clean copy of main `d9fab7e2` exited 0 and changed no file (retained root `01a15f48-0f71-77ba-b7df-f48c8e838efb`, `evidence/admission/st-40-01-repeat-sync-d9fab7e2/`).
  - Story-wide frontend and backend proof on main `d9fab7e2`, run directly on Hemma with the pre-push hook's steps: `fe-build`, `typecheck`, frontend tests (639 files, 4391 tests) and backend tests (7983 passed, 59 skipped; the one governance pin failure was an out-of-date local environment and passed after `pdm install --frozen-lockfile`), plus migration tests (121 passed) (`evidence/admission/full-suite-d9fab7e24/`).
  - Open: TASK-SKRIPT-40-01-04 (review changes_requested, two medium findings, held for the user's triage).
- 2026-10-22: done (user closure). TASK-SKRIPT-40-01-01 to -04 are done (40-01-04: merged `e9983e4f`, F1/F2 fixed `3b91b792`); the open item above is closed. Story-level proof on main `d9fab7e2` stands.

## Verification

- Each task proves real sync, digest validation and a no-diff repeat sync from its parent-owned clean committed checkpoint. The design-system hook is active at delivery.
- Story 1 alone passes `pdm run fe-type-check`, `pdm run fe-test`, `pdm run fe-build` and `pdm run design-system-validate`; no transitive import points to an unadopted file or missing peer.
- Focused proof covers busy and secondary actions, surface helpers, equal-width toggles, slotless/slot messages, null clearing, explicit dismissal, failure announcements, three-toast age order, fourth-toast eviction, manual dismissal and expiry.
- Hemma walk covers planner/share panel, modal/drawer, toggles, a real error and its dismissal, a multi-toast stack and each action-button class. Use HuleEdu browser-session helpers/preflight.

## Decided Contract Terms

| ID | Decided contract term |
| --- | --- |
| D1 | All Story 1 promotions ship in 0186's single release, including the manifest/barrel spinner export. Source: retained D15/D25; R1. |
| D2 | Package ToastHost is fed by a local newest-first bottom-placement adapter around the unchanged store. Source: retained D10/D22; R4. |
| D3 | Package tone/slots and optional string model preserve messages through explicit consumer dismissal and ARIA. Source: retained D12/D21; R3. |
| D4 | Package Vue exports use the shared subtree; root map, mirror, CSS and logo paths stay established. Source: retained D19, replacing the literal retained D6 path term for Vue files; R2. |
| D5 | Every task runs frontend, shared-validator and touched-screen staging proof. Source: retained D16. |
| D6 | Story 1 adopts the glyph runtime/peer; Story 2 owns broad meaning migration and old-peer removal. Source: retained D20; R1. |
| D7 | Sync proof uses admitted clean-map/result/repeat checkpoints with automatic hook enforcement restored before delivery. Source: retained D24; R6. |
