---
type: pr
id: PR-0137
title: "Klassrumskartan: class-list import remediation for example corpus, overview reconciliation, and runnable tests"
status: ready
owners: "agents"
created: 2026-03-25
updated: 2026-03-25
stories:
  - "ST-26-02"
tags: ["backend", "frontend", "klassrumskartan", "import", "remediation", "tests"]
dependencies:
  - "PR-0133"
  - "PR-0134"
  - "PR-0135"
acceptance_criteria:
  - "Given the example inputs under `data/class_list_example_inputs`, when the class-list import flow parses the text, legacy Excel, and PDF-backed variants, then each supported example yields the suggested class name `SA24D` plus the expected student roster preview instead of an empty result."
  - "Given a teacher confirms an imported class list, when roster creation succeeds, then the resulting roster is reconciled into the overview state immediately and the class workspace opens on the imported roster instead of reopening a blank create modal."
  - "Given roster creation from the import preview fails, when the teacher stays in the confirmation modal, then the failure reason is visible in the same workflow surface."
  - "Given import tests are added for this remediation slice, when the focused backend/frontend suites run, then the new tests execute under the repo's real fixture setup rather than failing at collection time."
  - "Given the repo's default local development environment, when a teacher uploads the shipped PDF example without any ad hoc Sir Convert base-url override, then the preview succeeds through a safe/default PDF execution policy that does not require an undeclared GPU-only lane."
  - "Given any import-preview request, when the extractor submits or polls PDF parsing work upstream, then the request correlation ID is propagated through the API, handler, extractor, and Sir Convert client so failures remain traceable."
  - "Given the full set of shipped teacher fixtures under `data/class_list_example_inputs/`, when the Playwright proof uploads each supported input format end to end, then the teacher can reach the parsed preview, confirm the import, and see the saved roster without the modal overlay swallowing clicks or closing the workflow unexpectedly."
  - "Given a teacher clicks `Ny klasslista`, when the create flow opens, then importing from file is the obvious first-path action inside that workflow, the accepted Skola24-oriented file types are clearly visible, and manual name entry remains available as the fallback path only when parsing needs correction."
  - "Given a teacher clicks `Redigera klass`, when the edit flow opens, then importing from file is still available from inside that class-list workflow as an afterthought instead of requiring a separate overview-level import button."
---

## Problem

The first class-list import slice established the preview contract and shipped the initial UI, but the
review surfaced four concrete gaps:

- the overview flow does not reconcile a successfully imported roster into local state
- save failures inside the preview modal are invisible to the teacher
- CSV/TSV-style row parsing silently drops common name-only rows without an index column
- the new integration test file does not run in the repo's actual fixture harness

In addition, the real example corpus under `data/class_list_example_inputs/` must become a standing
regression target so the implementation proves both student extraction and class-name inference on
teacher-like files rather than only on synthetic strings.

The follow-up review and live local testing also exposed three additional gaps that this remediation
slice must now own:

- the current PDF lane only proved itself when the web container was pointed at a remote GPU-backed
  Sir Convert deployment, which is not safe as the default repo expectation
- request correlation IDs are dropped before the new PDF extraction flow reaches Sir Convert, making
  production failures harder to trace
- the modal overlay / click handling is logically broken after parsing, and the current overview-row
  button layout makes file import feel like a side path instead of the primary teacher workflow

## Goal

Repair the import flow end to end so the teacher-facing experience is coherent, the parser handles the
provided example corpus (including the legacy `.xls` sample), the default repo environment can prove
the PDF lane safely, and the focused test suite plus live Playwright coverage provide real evidence
for those guarantees.

## Non-goals

- No broad redesign of unrelated Klassrumskartan overview panels beyond the import-focused class-list
  create/edit workflow changes needed to make file import the obvious first-path action.
- No expansion into roster merge/update flows for existing classes.
- No replacement of Sir Convert-a-Lot with a fully separate local PDF parsing pipeline inside
  Skriptoteket for teacher-uploaded class lists, even if future HTML->PDF export lanes may prefer
  lighter-weight local rendering for controlled inputs.

## Implementation plan

1. Keep Story `ST-26-02` and this PR doc as the governing slice, expanding the task to include the
   reviewer follow-ups, the overlay bug, and the class-list workflow UX correction.
2. Make the PDF extraction execution policy safe for the default repo environment by configuration or
   a repo-approved fallback policy, then prove the default local lane without requiring an ad hoc
   remote Sir Convert base-url override.
3. Thread the request correlation ID through `import_preview` -> handler -> extractor protocol ->
   extractor implementation -> Sir Convert client so submit/poll/download logs stay traceable.
4. Extend the extractor/parsing path to support the provided legacy `.xls` sample and to avoid empty
   previews for common delimited name rows without an explicit numeric index while still inferring
   the class name.
5. Repair the frontend modal/overlay state machine so parsing completion leaves the preview fully
   interactive, teachers can confirm-save without being clicked out of the workflow, and save errors
   remain visible in-place.
6. Rework the roster create/edit UX so `Ny klasslista` opens a class-list workflow with a prominent
   in-context `Importera från fil` action, accepted Skola24 file types are clearly communicated, and
   `Redigera klass` exposes the same import affordance inside edit mode rather than depending on a
   separate overview-row button.
7. Reconcile the created roster into the overview shell via the normal roster upsert path instead of
   reopening blank create mode, and keep import available as an afterthought inside edit mode.
8. Add focused regression tests that read the real example files from
   `data/class_list_example_inputs/`, assert suggested class name plus parsed student count, and
   cover correlation propagation plus the safe/default PDF job configuration.
9. Replace or repair the broken import integration tests so they run under the repo's actual fixtures.
10. Add a Playwright proof that exercises every supported file under `data/class_list_example_inputs/`
    end to end, covering upload -> parse -> preview -> save -> imported roster visible/selected.

## Test plan

- Backend unit tests for extractor/parser coverage using the real example `.txt`, `.csv`, `.tsv`,
  `.xls`, and PDF-backed fixtures.
- Backend handler and protocol tests proving the PDF lane uses the configured/default-safe Sir
  Convert execution policy and forwards the request correlation ID.
- Frontend tests for successful import reconciliation, visible confirm-save failure messaging, and
  the corrected modal/overlay interaction.
- Focused live local UI proof covering every supported file under `data/class_list_example_inputs/`
  from upload -> preview -> save -> imported roster visible/selected.
- Live local UX proof showing `Ny klasslista` and `Redigera klass` both expose in-context file
  import with clear Skola24-oriented file-type guidance.

## Rollback plan

- Remove the remediation wiring and fall back to the original import-preview and manual roster flows.
