---
type: story
id: ST-SKRIPT-08-36
title: Klassrumskartan tutorial clips in Hjälp with a first-use dialog
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-15'
status: ready
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SKRIPT-08
acceptance_criteria:
- The first visit to each planner section at desktop width opens a centered dialog
  with the section's first clip poster and a play button, and dismissing it records
  the section as seen for that guest browser or signed-in user.
- Every planner Hjälp section lists its clips as thumbnails that open the same dialog,
  on every width.
- Clips are served from a mounted media volume under the existing static path with
  range support, and a missing clip degrades to the written help without an error.
links:
  decisions: []
backlog_document_profile: contract-derived
---

## Slice Contract

Klassrumskartan teachers and guest demo users meet one narrated Swedish tutorial clip per Hjälp planner section, once, on first use at desktop width, and can replay every clip from Hjälp.

- Actors: a guest in the public workspace and a signed-in teacher in the authenticated workspace.
- First use: the first visit to a planner section (`planner_overview`, `planner_seating`, `planner_grouping`, `planner_rules`) at `(min-width: 1024px)` opens a centered 16:9 dialog with the section's first clip poster, a play control, and the section's other clips listed beneath. Sound never autoplays. Closing the dialog records the section as seen.
- Gate: the dialog waits for the manifest, the seen-state source, and on the authenticated host the guest-upgrade gate reaching `allowed`; it never opens while another planner dialog or the Hjälp panel is open. Under 1024 px nothing opens and the seen-state is untouched.
- Replay: every planner Hjälp section lists its clips as thumbnails that open the same dialog, on every width.
- Seen-state: a guest browser key under the existing `skriptoteket:classroom-planner:` prefix; a signed-in user's list on the profile through the existing classroom-planner settings endpoint.
- Clips: Clip manifest at `/static/media/klassrumskartan/clips.json`: `schema_version` 1, `app` `classroom.group-seating-studio`, and `clips[]` with `id`, `section` (exactly `planner_overview`, `planner_seating`, `planner_grouping` or `planner_rules`), `order`, `title`, `duration_seconds`, `video` and `poster` as paths relative to the manifest. A missing manifest means no pop-up and no thumbnails; a missing video shows the poster with a Swedish load-error line while the written help stays.
- Hosting: Media directory on Hemma at `/home/paunchygent/apps/skriptoteket-media/<dev|prod>/`, bind-mounted read-only at `/var/lib/skriptoteket/media` in the web container by `compose.hemma-dev.yaml` and `compose.prod.yaml`, served by the existing static mount at `/static/media`. The production compose change is inert until `hemma-deploy`, which needs its own authority.
- Copy: Swedish only, du-form, no first person, dry yet warm and concrete, labels taken from the live app.
- Non-goals: an in-app guided coach, bilingual copy, phone pop-ups, clip production (HuleFilm ST-VIDEO-12-01), and the production media deploy.

## Contract Inputs

- [EPIC-SKRIPT-08](../epics/epic-skript-08-contextual-help-hj-lp-and-onboarding.md) help and onboarding scope.
- [Klassrumskartan kom igång guide](../../guides/guide-klassrumskartan-kom-igang.md), the source of the generated planner help sections and of the draft narration; its TALMANUS block for a clip leaves the guide once that clip's talmanus is approved.
- Help seam: `components/help/helpTopicCatalog.ts`, `helpTopics.ts`, `topics/HelpTopicPlanner.vue`, `useHelp.ts`; context set by `PlannerWorkspaceShell.vue`, `PlannerClassWorkspace.vue` and `ClassroomPlannerGuestWorkspaceShell.vue`.
- Profile settings: `PATCH /api/v1/profile/classroom-planner-settings` and `UpdateClassroomPlannerSettingsHandler`.
- Guest upgrade gate: `useClassroomPlannerGuestUpgrade.ts` (`isBlocking`, `shouldShowPrompt`).
- Clip producer: HuleFilm EPIC-VIDEO-12 / ST-VIDEO-12-01, which publishes to the media directory and owns the manifest writer.
- Retained plan: `.orchestration/context/sessions/01a13d03-cc0c-731e-a9e5-b3d536821e55/evidence/planning/ST-SKRIPT-08-36/plan.md`.

## Tasks

- [TASK-SKRIPT-08-36-01](../tasks/task-skript-08-36-01-walking-skeleton-serve-one-placeholder-clip-from-the-media-mount-into-the-first-use-dialog-with-seen-state.md): walking skeleton across media mount, manifest, dialog, thumbnails and seen-state on Hemma dev.
- Later tasks are derived after the skeleton proof: copy and thumbnail polish once real clips exist, and the production media deploy under its own authority.

## Verification

- Focused backend tests for the media mount, the profile seen-sections field and the settings endpoint.
- Focused frontend tests for the manifest schema, the seen-state composable, the first-use gate conditions and the dialog.
- A real browser click-through on Hemma dev as a guest and as a signed-in proof user, with evidence in the retained session.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| D01 | Narrated clips embedded in Hjälp, one set per planner section, opening automatically on first use. |
| D02 | Swedish only, du-form, no first person, dry yet warm and concrete. |
| D03 | Scope: klass, klassrum, sittschema, grupper, regler, dela, fast plats. |
| D04 | First use opens once per section at desktop width as a centered dialog with poster and play; no autoplaying sound; dismissing marks the section seen. |
| D05 | Hjälp planner sections list their clips as thumbnails that open the same dialog, on every width. |
| D06 | Guests and signed-in users both; guest seen-state in the browser, signed-in seen-state per user. |
| D07 | No pop-up under 1024 px; thumbnails still play; seen-state unaffected. |
| D08 | Clips hosted on a Hemma media directory served under the existing static path; HuleFilm publishes there. |
| D09 | The production mount and publish step need separate authority; the skeleton runs on Hemma dev. |
| D10 | The first task is the walking skeleton. |
| D11 | Seven clips mapped to the four sections; the pop-up plays the section's first clip and lists the rest. |
| D12 | This story owns the Skriptoteket surface; HuleFilm EPIC-VIDEO-12 owns the clips; they meet at the manifest contract. |
| D13 | An approved clip talmanus replaces the guide's TALMANUS block for that clip. |
| D14 | Infrastructure is built on draft scripts; talmanus approval comes last; a missing clip degrades to the written help. |
| D15 | Clip manifest at `/static/media/klassrumskartan/clips.json`: `schema_version` 1, `app` `classroom.group-seating-studio`, and `clips[]` with `id`, `section` (exactly `planner_overview`, `planner_seating`, `planner_grouping` or `planner_rules`), `order`, `title`, `duration_seconds`, `video` and `poster` as paths relative to the manifest. A missing manifest means no pop-up and no thumbnails; a missing video shows the poster with a Swedish load-error line while the written help stays. |
| D16 | Media directory on Hemma at `/home/paunchygent/apps/skriptoteket-media/<dev|prod>/`, bind-mounted read-only at `/var/lib/skriptoteket/media` in the web container by `compose.hemma-dev.yaml` and `compose.prod.yaml`, served by the existing static mount at `/static/media`. The production compose change is inert until `hemma-deploy`, which needs its own authority. |
