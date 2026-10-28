---
type: epic
id: EPIC-SKRIPT-40
title: Shared design-system convergence
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-09-27'
status: active
closeout_review:
  record: inline
  status: not_started
outcome: Skriptoteket consumes the shared huleedu-integrated design system through design-system sync for tokens, components, action buttons and glyphs, and its local extensions live in the shared package.
links:
  decisions: []
backlog_document_profile: contract-derived
---

## Capability Contract

Skriptoteket consumes the shared `huleedu-integrated` design system through
`repository-governance-frontend-catalog design-system sync`, replacing hand
copies and local forks. Reusable local extensions are promoted into the
package before adoption. Existing Skriptoteket features are preserved;
existing HuleEdu call sites retain their rendering and defaults.

Skill-repository owns package releases and HuleEdu syncs. Skriptoteket owns
its root adoption map, local composition barrel, application adapters and
call sites. Package Vue files occupy a package-shaped subtree under
`frontend/apps/skriptoteket/src/components/ui/shared`; adopted CSS, logo and
metadata mirror retain their existing paths. Brand and auth-lifecycle stay
unadopted. HuleEdu UI redesign is excluded. New product features are excluded,
except that ST-SKRIPT-40-04 builds the exam workspace controls for features
whose backends come from EPIC-SKRIPT-39 (user 2026-10-17, G1, G2).

Story 1 includes the released glyph runtime and peer needed by its shared
components. Story 2 owns icon-meaning inventory, missing-meaning promotion,
call-site migration and removal of `lucide-vue-next`.

## Contract Inputs

- Accepted retained plan `.orchestration/context/sessions/01a0e42e-f433-727d-a17f-f9eced6d04bc/evidence/planning/TASK-SKRIPT-REP-0033/plan.md`, D1-D18 and admitted repair decisions D19-D25.
- Review `docs/backlog/reviews/review-epic-40-shared-design-system-convergence.md`, R1-R6; the review decision remains unchanged pending rereview.
- Original adoption discovery `.orchestration/context/sessions/01a0e42e-f433-727d-a17f-f9eced6d04bc/discovery/design-system-adoption.md`.
- Repair evidence `.orchestration/context/sessions/01a0e4a4-436a-70d9-a907-702d84f2a091/evidence/planning/EPIC-SKRIPT-40-repair/draft.md`.
- Existing boundary precedent TASK-HULE-REP-0085; first Skriptoteket sync is the initial integrated delivery, not a separate skeleton task.

## Stories

| Story           | Slice                                                                                                                                                                                                                                 |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ST-SKRIPT-40-01 | Done 2026-10-22 (user closure): TASK-SKRIPT-40-01-01 to -04 done (tokens, theme, logo, shared Vue subtree, toast adapter, action buttons, huleedu-integrated 0.1.34); story-level proof on main `d9fab7e2`.                           |
| ST-SKRIPT-40-02 | Done 2026-10-28 (closure under TASK-SKRIPT-REP-0055 D7): TASK-SKRIPT-40-02-01 migrated the remaining icons to the shared glyph vocabulary and removed `lucide-vue-next`; Mac staging walk at `05b3fc12a` passed.                      |
| ST-SKRIPT-40-03 | Done 2026-10-20 (user closure): every screen outside the app shell and the exam workspace is on the shared visual direction through TASK-SKRIPT-40-03-01 to TASK-SKRIPT-40-03-10; the .codex/rules facts live in their owning skills. |
| ST-SKRIPT-40-04 | Done 2026-10-28 (closure under TASK-SKRIPT-REP-0055 D7): the prototype is approved and the app shell and exam workspace are rebuilt; every follow-up task is done or canceled.                                                        |

## Verification

- The map covers every released export; only brand and auth-lifecycle are null at epic completion. All adopted bytes match the mirror digests.
- From a clean committed consumer checkpoint, sync against the identified clean skill-repository main release exits 0 and changes no file. The automatic validator hook is active; bootstrap checkpoints are not completion evidence.
- No local fork of an adopted export or `lucide-vue-next` dependency remains. Explicitly classified local icons may remain when no shared meaning fits.
- Each story passes frontend typecheck, unit tests, build and shared design-system validation, plus the relevant Hemma staging walks using the HuleEdu browser-session helpers/preflight.
- HuleEdu is synced to each required release with design-system validation and frontend checks passing. Shared SystemMessage defaults and rich-slot rendering remain unchanged.

## Epic Verification Plan

| Gate                                                                   | Verification Result | Evidence                                                                                                                                                      | Owner           | Follow-up / Exception |
| ---------------------------------------------------------------------- | ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------- | --------------------- |
| Every Skriptoteket screen on the shared visual direction               | verified            | ST-SKRIPT-40-03 closeout (user closure 2026-10-20); TASK-SKRIPT-40-03-01 to -10 closeout evidence                                                             | ST-SKRIPT-40-03 | None                  |
| Tokens, components and action buttons converge onto the shared package | verified            | ST-SKRIPT-40-01 closeout (user closure 2026-10-22); TASK-SKRIPT-40-01-01 to -04 closeout evidence; clean-state repeat sync and full suites on main `d9fab7e2` | ST-SKRIPT-40-01 | None                  |
| Icons converge onto the shared glyph vocabulary                        | verified            | ST-SKRIPT-40-02 closeout (closure 2026-10-28, TASK-SKRIPT-REP-0055 D7); Mac staging walk at `05b3fc12a`                                                       | ST-SKRIPT-40-02 | None                  |
| App shell and exam workspace rebuilt from the approved prototype       | verified            | ST-SKRIPT-40-04 closeout (closure 2026-10-28, TASK-SKRIPT-REP-0055 D7); child task closeouts                                                                  | ST-SKRIPT-40-04 | None                  |

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | Reusable local extensions are promoted instead of forked. Source: retained D1/D9/D11-D15.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| D2  | Brand and auth-lifecycle remain unadopted. Source: retained D13.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| D3  | Package palette is authoritative. Source: retained D3.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| D4  | Adoption and drift proof use shared sync/validate and admitted clean checkpoints. Source: retained D4/D16/D24; R6.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| D5  | Two stories separate component delivery from semantic icon migration; prerequisite glyph runtime belongs to Story 1. Source: retained D17/D20; R1.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| D6  | Vue adoption uses the shared subtree and local composition barrel; other established resource paths remain. Source: retained D19; R2.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| D7  | Greenfield UI design and its implementation are Opus-owned and cover only the app shell (top bar, sidebar, page frame) and the exam workspace (ST-SKRIPT-40-04): one Opus lead makes the prototype and owns the design rules, and two Opus builders implement it after user approval. Every other screen keeps its layout and gets the simple refresh onto shared tokens, buttons and components by Sol 6.1 agents (ST-SKRIPT-40-03); Sol agents do only non-visual work otherwise. Source: user 2026-10-17, G7, G9, G10.                                                                                                                                                                                                                                                                                                                                                  |
| D8  | The epic stays `active` on 2026-10-28 (orchestrator decision, TASK-SKRIPT-REP-0056 D5): its acceptance is not fully established on main. What holds: all four stories are done with their verification rows `verified`; `pdm run design-system-validate` exits 0; `repository-governance-frontend-catalog design-system sync` against skill-repository (release 0.1.37, the map's version) exits 0 and changes no file; `frontend/apps/skriptoteket/package.json` has no `lucide-vue-next`; `pdm run fe-type-check` exits 0. What is open: the last Verification bullet requires HuleEdu synced to each required release, HuleEdu's `design-system-map.json` is at 0.1.34 while the package and Skriptoteket are at 0.1.37, and no record names which releases HuleEdu requires. The Contract Inputs also say the epic review decision remains unchanged pending rereview. |
