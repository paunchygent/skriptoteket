---
type: task
id: TASK-SKRIPT-39-10-03
title: A PDF without readable text stops with a message, and skipped pages are named
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-21'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: orchestrator
  decided_at: '2026-10-28'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: 'Ruthless review raised F1 (medium): the skipped-pages note reached the exam only at final publication; repaired in 057c344e6 and admitted on focused proof without rereview. Merged 32d503c98; script callers repaired 8edbedd9b (0944a6e23). Mac staging walk at 0944a6e23 by the Mac thread 2026-10-28 (Mac ~/Repos/Skriptoteket/.artifacts/staging-walk-39-10-03-0944a6e23/walk-record.md): checks 1-3 pass; the walk found the stop message cut with an ellipsis. Walk repair 7bba2bb8b (merged fac5f7e1c): a failed import''s message wraps in full; fail-first spec 1 failed before, 25 tests passed after, fe-type-check and fe-lint exit 0 (retained evidence stop-message-wrap/). Closed on that unit proof without a re-walk, by orchestrator decision.'
task_kind: story
acceptance_criteria:
  - A PDF without text, or whose text layer is mostly unreadable, imports nothing and shows a stop message telling the teacher to save the exam as Word or as a PDF from the original
  - When only some pages lack readable text, the readable pages import and a note names the skipped pages
story: ST-SKRIPT-39-10
backlog_document_profile: contract-derived
---

## Implementation Contract

A teacher imports a PDF exam into the exam workspace (ST-SKRIPT-39-10). Today a PDF with no text at all stops with "PDF-filen saknar läsbart innehåll." (`exam_workspace_pdf_chunker.py` `read_pdf_blocks`). That message gives no way forward. A PDF whose text layer is garbled, or which has a few pages without text, is not handled page by page.

This task implements story terms P2 and P7:

- **Whole PDF without readable text.** It imports nothing and stops with a message telling the teacher to save the exam as a Word file, or as a PDF from the original document. Pictures alone are no readable content, as today.
- **Some pages without readable text.** The readable pages import as today. One note in the import result names the skipped pages by page number. It is shown through the existing import notice surface in the workspace; no new component.
- **Mostly unreadable pages.** They follow the same rules. A page counts as unreadable when its text layer is mostly unmapped glyphs (for example pdfminer's `(cid:NN)` output, replacement or private-use characters) by a deterministic measure the lead defines and proves on fixtures.
- **Non-goals.** Scanned-PDF support (OCR) stays deferred. No new AI call site. No change to the Word import.

## Contract Inputs

- ST-SKRIPT-39-10 terms P2, P5 and P7 (user grilling 2026-10-21).
- Current behaviour: `read_pdf_blocks` in `src/skriptoteket/infrastructure/curated_apps/apps/conversion_hub/exam_workspace_pdf_chunker.py` and the page reader in `exam_workspace_pdf_page_adapter.py`.
- TASK-SKRIPT-39-10-01 and 39-10-02 (done) for the PDF import path and its proof set.

## Core Vertical And Performance

One import: a PDF reaches `read_pdf_blocks`, each page is judged readable or not, and the result is a stop, a full import, or an import with a skipped-pages note that the teacher sees in the workspace. The page judgement runs once per page on text the reader already extracts; no extra parsing pass.

## Validation

- Focused backend tests with generated PDFs: no text at all; pictures only; one textless page between text pages; a garbled text layer on one page and on all pages. Each fails before the change where the behaviour is new.
- A focused frontend spec for the skipped-pages note.
- One Mac staging walk of the exam workspace with a textless PDF and a PDF with one textless page.

## Stop Conditions

- The skipped-pages note cannot reach the workspace through the existing import result and notice surface without a new API shape that other imports must change for.
- No deterministic readability measure separates the garbled fixtures from real exams in the 39-10 proof set.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                             |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | A PDF without readable text imports nothing and stops with a message telling the teacher to save the exam as a Word file or as a PDF from the original (story P2).                                                                                |
| D2  | When some pages lack readable text, the readable pages import and one note names the skipped pages by number, through the existing import notice surface (story P2).                                                                              |
| D3  | Mostly unreadable pages follow D1 and D2; readability is a deterministic per-page measure of unmapped glyphs, defined and proved on fixtures by the lead (story P7).                                                                              |
| D4  | Scanned-PDF support stays deferred; no new AI call site; the Word import is unchanged (story P2, P5).                                                                                                                                             |
| D5  | New copy gets one ui-copy review; proof is focused backend and frontend tests and one Mac staging walk; one independent review at most, repairs admitted on focused proof. Orchestrator decision 2026-10-28 under the user's priority order (#5). |

## Progress

### Orchestrator decision 2026-10-28: picture-only pages

- A picture-only page between text pages keeps importing its picture and is not named in the skipped-pages note, as it imports today. Only a page with neither text nor pictures, or with a mostly garbled text layer, is skipped and named. A PDF whose pages are all picture-only or empty still stops with the D1 message. "Pictures alone are no readable content" applies to the whole-PDF case.
