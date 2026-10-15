---
type: reference
id: REF-SKRIPT-MOCKUP-exam-workspace-approved-mockups-for-the-shared-design-direction
title: Exam workspace approved mockups for the shared design direction
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-12'
status: active
reference_kind: mockup
summary: User-approved images and exclusions for the exam workspace restyle
---

## Intent

The user approved these images on 2026-10-12 as the visual target for the exam
workspace restyle. They follow the HuleEdu comparative judgment rater and setup
screens: slightly rounded corners, no hard offset shadows, 44 px regular
controls, teal primary action and sentence-case labels.

## Package Manifest

Images live in `docs/mockups/exam-workspace-shared-direction/approved/`:

| File | Shows |
| --- | --- |
| `r2-2-desktop-edit-rail.jpg` | Desktop Redigera with the details rail of stacked cards beside the editor. |
| `r2-4-desktop-files.jpg` | Desktop Filer view. |
| `r2-5-tablet-edit-open.jpg` | Tablet Redigera with the floating details panel over the editor. |
| `r2-6-phone-edit-closed.jpg` | Phone Redigera with Detaljer at the end of the question strip. |
| `r2-7-phone-details-open.jpg` | Phone details as a full screen with Tillbaka. |

## Design Interpretation

Binding: control sizes (44 px regular, 28 px compact only for dense controls
such as "Ny fråga"), corner radii, the absence of hard shadows, colour and type,
the mode toggle at the same height as Spara, and the placement of the details
rail (desktop), floating panel (tablet) and full screen (phone). Detaljer sits
in the workspace toolbar on desktop and tablet and at the end of the question
strip on phone.

The image generator added content the workspace does not have. These images
decide appearance and placement only and add no feature. Not built from them:

- the version dropdown; the workspace shows the version as text;
- drag handles on answer options and the "Lägg till alternativ" button;
- a filled teal Detaljer button: Spara is the only filled action in a view;
- teal "Föreslå facit" and "Välj provfil" buttons and icon tiles for the
  export formats in the Filer view;
- example question text, notes and sources, which are placeholder content.

## Runtime And Proof Boundary

Static images prove no runtime behaviour. Runtime acceptance is the Hemma
staging walk owned by TASK-SKRIPT-39-04-05.

## Governing Links And Follow-Up

- TASK-SKRIPT-39-04-05 implements these images; its retained plan holds
  decisions D5-D8 (Skriptoteket retained session
  `01a13061-ff38-7099-aa3d-e23f6e5bba43`).
- ST-SKRIPT-40-03 brings every other screen onto the same direction.
