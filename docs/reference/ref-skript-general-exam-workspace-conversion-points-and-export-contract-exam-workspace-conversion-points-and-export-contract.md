---
type: reference
id: REF-SKRIPT-GENERAL-exam-workspace-conversion-points-and-export-contract
title: Exam workspace conversion, points and export contract
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-23'
status: active
reference_kind: general
summary: 'Durable user rules for the exam workspace: conversion quality, printed points,
  import cleanup, question labels, metadata, exports and notices'
---

## Overview

This reference holds the user's durable product rules for the exam workspace
and the exam converter: how conversion quality is judged, how printed points
are owned, how cleanup and question names work after conversion, what belongs
in the exam's metadata, which exports exist, and how notices behave. The
approved prototype
[REF-SKRIPT-MOCKUP-app-shell-and-exam-workspace-redesign-prototype](ref-skript-mockup-app-shell-and-exam-workspace-redesign-prototype-app-shell-and-exam-workspace-redesign-prototype.md)
owns layout and control placement. Work state lives in the backlog.

## Facts And Semantics

### Conversion Quality

- Judge AI conversion (DOCX to native exam to QTI) and dropped-text detection
  by pattern. A changed word, one or two non-critical dropped words, or a
  spelling, grammar or terminology fix that keeps the meaning is no finding.
- A finding is a systematic drop: a recurring pattern where one kind of
  paragraph or sentence is dropped or made worse, so items end up worse than
  their source. An edit that almost always improves the question is
  acceptable; the model is not deterministic.
- The gate is interpretive. Read each dropped or changed instance side by side
  with its source and judge whether the item still works as well for reading,
  understanding, answering and marking. No similarity score, word count or
  wording rule decides.
- Measure a rule change by pattern analysis over all recorded fixtures,
  grouping drops by kind and fixture. Fix a found pattern at its root, in the
  prompt or the conversion rule, never with a wording-based flag.

### Printed Points

- Document structure alone decides the owner of every printed points line,
  never the AI's placement, the Word style or which other lines exist:
  - a question's own line gives that question's points and beats the AI reply;
  - a line that opens or closes a part gives that part's total;
  - any other line is an exam-total candidate, and conflicting candidates give
    no total.
- Question values are corrected before any section allocation. Reject
  conditional patches such as "only when no other total line exists". Prove
  the rule with invariance tests across the AI placements of every recording.
- A printed total that differs from its questions' sum is a warning that
  never blocks Spara or an export, and nothing shows when the totals match.
  The workspace shows one plain sentence-case Swedish line per differing
  level, with no all-caps text, no jargon such as "Tryckt" and no number
  repeated next to itself.

### After Conversion

- Every label, pointer and check refers to Skriptoteket's own converted
  structure: the list labels ("Fråga 5", "4a", "Del 3"), its parts and its
  stored points. Alerts, toasts, export rows and blockers name a question by
  the label the question list shows, never by the source exam's numbering or
  titles or by `item.sequence`. A source value appears only quoted
  ("provtexten anger 22 p"). Never infer the teacher's intent from the
  source's old structure.
- Import cleanup removes text the app regenerates or does not need, such as
  "(3 poäng)" at the end of a question, only under a sure rule: end of text,
  and the number matches the item's points. A case in the same shape that
  fails only a certainty check becomes one batch offer in the review note,
  for example "3 frågor har kvar poängtext, t.ex. ‘(3 poäng)’. Ta bort?".
  Accept removes all of it in one undo step, dismiss keeps it and the offer
  does not return, and continue jumps to the first case. Never offer points
  wording inside a sentence, which can be the question itself, and never make
  per-item offers.
- A one-off decision is question text answered by the shared
  accept and dismiss glyphs, for example "Använd beräknade poäng?", with the
  action names only in the tooltip and accessible name. A one-off decision is
  never a text button such as "Ignorera skillnaden".

### Exam Metadata

- Course and central content belong in the native exam document, which is a
  durable, shareable format. Class and other teacher-situational data never
  do; a class label may come later only as optional data outside the exam
  document, linked to the classroom planner's classes. Check each new field
  against "would any colleague want this exam data?".
- A teacher finds the right course and central content in the fewest clicks.
  Prefill or suggest only when the value is very likely correct. Grundskolan
  year bands (åk 1–3, 4–6, 7–9) are never grouped together.

### Exports

- QTI is the main route into Exam.net and DigiExam. PDF is a deterministic
  print rendering of the teacher's final exam in the house template, as a
  student PDF and a PDF med facit; print features such as writing areas belong
  there. DOCX is for download and editing. The Exam.net import-plan PDF stays
  only as a fallback for import when QTI fails: it is never an exam, never
  printed and never promoted. Export menus list QTI, PDF, PDF med facit, DOCX,
  then the import-plan PDF.
- Exam.net imports a QTI question declared as 0 points as 1 point (observed
  2026-10-17), and Skriptoteket keeps exporting 0. When any question has 0
  points, the export area shows the inline note "Exam.net ger frågor med 0
  poäng 1 poäng. Ändra poängen i Exam.net efter importen." The note never
  blocks the export and is never a toast. A 0 is a set value; a question with
  no points value is still an export blocker.
- Every word an export adds is Swedish; there is no per-exam language switch.

### Notices

- A toast appears only when an action fails, such as a failed save, export or
  undo request. A success has no toast: the result in place confirms it.
- A toast never carries Ångra or any other action. Feedback on an in-place
  edit, such as the dropped-content notice after a question-type change, is
  inline in that element. Undo runs on the autosave-backed history through
  the header Ångra and Gör om and Ctrl/Cmd+Z, so an edit needs no Ångra button
  of its own.

## Decisions And Interpretation

These rules record user rulings from the ST-SKRIPT-39 and ST-SKRIPT-40 work
between 2026-10-16 and 2026-10-19; the exam workspace follows them in
`examWorkspaceConversionShared.ts`, `useExamWorkspaceStructure.ts`,
`examWorkspaceTotals.ts` and `examWorkspaceExportFormats.ts`. They supersede
the prototype's success toasts, its toast with Ångra and its footer-only total
line, which the prototype reference now marks.
