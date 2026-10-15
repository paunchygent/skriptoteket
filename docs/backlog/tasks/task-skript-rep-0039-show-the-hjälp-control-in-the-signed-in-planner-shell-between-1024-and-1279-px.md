---
type: task
id: TASK-SKRIPT-REP-0039
title: Show the Hjälp control in the signed-in planner shell between 1024 and 1279
  px
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-15'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
- At every viewport from 1024 px up, the signed-in Klassrumskartan shell exposes a
  visible Hjälp control (top bar or drawer) that opens the help panel, with the existing
  no-duplication rule for app lanes preserved
backlog_document_profile: contract-derived
---

## Implementation Contract

Found by the ST-SKRIPT-08-36 staging walk on 2026-10-15 (retained session
`01a13d03-cc0c-731e-a9e5-b3d536821e55`, `evidence/staging-walk-prep-b8e43394/walk-2026-10-15/WALK.md`,
finding F2, screenshot 18). At exactly 1024 px the signed-in Klassrumskartan
shell shows only **Meny**; the top bar's Hjälp button has zero size and the
drawer lists Hem, Mina filer, Föreslå verktyg, Katalog, Profil and Mina verktyg
without Hjälp. At 1280 px the top bar shows Aktivera fokusläge, Hjälp and Logga
ut. The guest shell shows Hjälp at 1024 px and 900 px. Cause:
`AuthTopBar.vue` hides `.top-user-bar--xl-sidebar-breakpoint` from 768 px and
shows it again from 1280 px, while `AuthSidebar.spec.ts` pins that the drawer
never lists Hjälp. The tutorial first-use dialog still opens at these widths;
replaying a clip from Hjälp does not.

Deliver one visible Hjälp control in the signed-in planner shell at every width
from 1024 px up, with the same help panel behind it, without duplicating app
lanes in the drawer.

Owner: the user's Mac Claude session (2026-10-15), which repairs this together
with HuleEdu TASK-HULE-REP-0142 and then reruns the ST-SKRIPT-08-36 walk.

## Contract Inputs

- `frontend/apps/skriptoteket/src/components/layout/AuthTopBar.vue` breakpoints
  (last changed in `7eace644` and `48eb6dff`).
- `frontend/apps/skriptoteket/src/components/help/HelpButton.vue` and the
  planner help topic from ST-SKRIPT-08-36.
- `AuthSidebar.spec.ts` lines asserting Hjälp is not a drawer nav item.

## Core Vertical And Performance

Core vertical: signed-in planner at 1024 px → visible Hjälp control → help panel
opens → Klass thumbnail replays the clip. No layout shift in the shell at the
768, 1024 and 1280 px breakpoints.

## Validation

- Frontend focused vitest for the shell at 1024 px and 1279 px (control present
  and reachable) and at 1280 px (unchanged), plus the existing sidebar spec.
- Proof: a real browser walk on Hemma staging at 1024 px and 1279 px as the proof
  user, retained under the task's session.

## Stop Conditions

- A change to the shared design-system shell tokens or breakpoints stops for a
  lead decision.
- Listing Hjälp as a drawer app lane contradicts the no-duplication rule and
  stops for a lead decision.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| T01 | Widths under 1024 px keep their current shell; the tutorial first-use dialog is desktop-only and this task does not change that. |
