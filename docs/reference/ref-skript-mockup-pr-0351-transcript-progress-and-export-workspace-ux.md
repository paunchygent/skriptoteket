---
type: reference
id: REF-SKRIPT-MOCKUP-pr-0351-transcript-progress-and-export-workspace-ux
title: PR-0351 transcript progress and export workspace UX
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: active
reference_kind: mockup
summary: PR-0351 transcript progress and export workspace UX
---

## Intent

### PR-0351 Transcript Progress And Export Workspace UX

### Purpose

Retain the approved direction for the Conversion Hub transcript flow after a
successful STT conversion.

The flow must not expose internal conversion jargon, hide the useful workspace
behind a manual `Spara` gate, or present export artifacts as repeated
calculator-like rows of small buttons.

### Assets

- [Static HTML mockup](index.html)
- [Generated direction image](transcript-progress-export-direction.png)

### Direction

- While work is running, the main panel shows conversion progress only. The
  transcript workspace, speaker renaming, and export controls are not shown
  until a transcript exists.
- The running state has one cancel action: `Avbryt`. It must not include a
  checkbox, toggle, delayed-cancel mode, or any `avbryt efter klar` behavior.
- Progress copy uses normal Swedish product language: `Hittar talare`,
  `Skriver ut samtalet`, and `Gör texten klar`.
- The running state may show measured browser upload progress while bytes are
  still uploading. After Sir Convert owns the job, `PR-0354` amends this
  contract: do not render raw percent, ETA, processed-audio, chunk, or heartbeat
  counters until the upstream contract can make them stable enough for
  teacher-facing progress.
- Completion autosaves the transcript. The completed workspace shows
  `Sparat automatiskt`, not a primary generic `Spara` gate.
- Restart actions use direct user language such as `Ny transkribering`, not
  awkward labels like `Skapa transkript igen`.
- Speaker names and export controls live in a right-side inspector titled
  `Talare och export`; do not add redundant subsection labels such as
  `Talarnamn` and `Export` when the controls are already self-describing.
- Speaker-name editing autosaves on input. The completed workspace shows a
  compact incomplete/saving/saved/failed status row and does not require a
  separate speaker-name save button.
- Export uses one compact control block: a single segmented format selector
  for `TXT`, `MD`, `VTT`, and `SRT`, followed by two named actions for the
  selected format: `Ladda ner` and `Mina filer`.
- The selected file format must not be interpolated into visible action labels;
  the format selector already carries that state and action labels must stay on
  one line on desktop.
- Do not show a second big `Exportera` button, dropdown chevron, selected-file
  row, repeated download affordance, or separate metadata cards for generated
  files.
- Do not hide status, warning, or recovery rows that later appear and push the
  layout around. Pending, running, failed, and warning states must either use a
  reserved fixed slot in the same footprint or a separately planned state layout
  for the inspector.
- User-facing progress copy must only promise behavior the product actually
  supports. Do not claim that the user can leave the workspace or keep working
  elsewhere unless that has been verified in the implementation, and do not
  surface unstable upstream counters as reliable ETA/progress.
- Runtime symbols must follow the approved semantic icon dictionary. Use
  `IconX` for removing/dismissing the selected file, `IconCheck` for success
  and saved autosave state, `IconRun` for start/play actions, `IconDownload`
  for download/export, `IconVaultFiles` for `Mina filer`, `IconFileAudio` for
  uploaded audio/video source files, and `IconFileText` for text/document
  export files.
- The completed workspace needs a real transcript width. The transcript column
  must not be squeezed between fixed setup and inspector rails; at narrower
  widths the inspector moves below the transcript, and on small widths the rail
  stacks above the work surface.

## Package Manifest

The source material below remains authoritative for this section.

## Design Interpretation

The source material below remains authoritative for this section.

## Runtime And Proof Boundary

The source boundaries and recovery limits remain preserved below.

## Governing Links And Follow-Up

The source material below remains authoritative for this section.
