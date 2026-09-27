---
type: epic
id: EPIC-SKRIPT-40
title: Shared design-system convergence
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-09-27'
status: ready
closeout_review:
  record: inline
  status: not_started
outcome: Skriptoteket consumes the shared huleedu-integrated design system through
  design-system sync for tokens, components, action buttons and glyphs, and its local
  extensions live in the shared package.
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
unadopted. New product features and HuleEdu UI redesign are excluded.

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

| Story | Slice |
| --- | --- |
| ST-SKRIPT-40-01 | Tokens, theme, logo, dense components and spinner, messages, toast adapter, action buttons, and required glyph runtime/peer. |
| ST-SKRIPT-40-02 | Expanded shared meaning vocabulary, complete icon migration, and old Lucide dependency removal. |

## Verification

- The map covers every released export; only brand and auth-lifecycle are null at epic completion. All adopted bytes match the mirror digests.
- From a clean committed consumer checkpoint, sync against the identified clean skill-repository main release exits 0 and changes no file. The automatic validator hook is active; bootstrap checkpoints are not completion evidence.
- No local fork of an adopted export or `lucide-vue-next` dependency remains. Explicitly classified local icons may remain when no shared meaning fits.
- Each story passes frontend typecheck, unit tests, build and shared design-system validation, plus the relevant Hemma staging walks using the HuleEdu browser-session helpers/preflight.
- HuleEdu is synced to each required release with design-system validation and frontend checks passing. Shared SystemMessage defaults and rich-slot rendering remain unchanged.

## Decided Contract Terms

| ID | Decided contract term |
| --- | --- |
| D1 | Reusable local extensions are promoted instead of forked. Source: retained D1/D9/D11-D15. |
| D2 | Brand and auth-lifecycle remain unadopted. Source: retained D13. |
| D3 | Package palette is authoritative. Source: retained D3. |
| D4 | Adoption and drift proof use shared sync/validate and admitted clean checkpoints. Source: retained D4/D16/D24; R6. |
| D5 | Two stories separate component delivery from semantic icon migration; prerequisite glyph runtime belongs to Story 1. Source: retained D17/D20; R1. |
| D6 | Vue adoption uses the shared subtree and local composition barrel; other established resource paths remain. Source: retained D19; R2. |
