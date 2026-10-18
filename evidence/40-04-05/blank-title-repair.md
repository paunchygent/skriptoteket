# 40-04-05 blank-title repair

Defect (staging walk of main 8090c48f): blanking the exam title made
`POST .../exam-workspace/documents/{id}/autosaves` return 422 `string_too_short` on
`body.document.title`. The blank title was never stored, `export_blockers` never computed, and the
export menu showed no red row.

## Cause

`NativeExamDocument.title` carried `Field(min_length=1)`. The save and autosave request schemas embed
that model, so the domain constructor rejected a state the contract treats as a savable draft blocked
only at export. The handler tests built blank-title documents with `model_copy`, which skips
validation, so they never reached the request schema.

## Change

- `native_exam_document.py`: `title: str` with no presence guard. `native_export_blockers`
  (`title_has_text`) stays the only owner of the title rule; no other save path checks the title.
- `useExamWorkspaceSave.ts`: removed the client "Skriv en titel innan du sparar provet." refusal from
  Spara and Spara som.
- `useExamWorkspaceSaveFlow.ts`: Spara is available whenever an exam is open and not busy.
- `ExamWorkspaceDetailsDrawer.vue`: guidance line reads "Skriv en titel innan du exporterar provet."
- `openapi.d.ts` regenerated with `pdm run fe-gen-api-types`; it did not change (the generated types
  carried no `minLength` for the title).

## Tests added or changed

- `tests/unit/web/test_exam_workspace_blank_title.py` (new): HTTP requests through the real request
  schemas. Autosave and PUT save with title `""` and `"   "` return 200, store the title, and return
  `{"item_id": null, "reason": "title_without_text"}` in `export_blockers`; reopening the document
  carries the blocker; a following titled autosave clears it. With the `min_length` restored these
  four cases return 422 (observed).
- `test_exam_workspace_export_file_names.py`: export refusal (download, save to Mina filer) now also
  runs for titles `""` and `"   "` and names the title reason.
- `ExamWorkspaceTitleBlocker.spec.ts`: after the autosave of `""` / `"   "` the red export-menu row
  shows, QTI, PDF and DOCX are disabled, and no failure toast is raised; Spara with `"   "` sends the
  request, shows the row and raises no failure toast. The server is a test double.
- `ExamWorkspaceMetadataSlice.spec.ts`: the test that pinned the client-side refusal now pins that
  Spara sends the blank title.

## Proof

- `pdm run pytest tests/unit/application/curated_apps tests/unit/domain/curated_apps tests/unit/web -k exam`:
  3719 passed, 75 skipped, 1 failed. The failure is
  `tests/unit/web/test_spa_fallback.py::...[/public/apps/documents.conversion_hub/exam-converter]`
  (HTTP 500 on the public exam-converter SPA shell route); this change touches no code on that path.
  It was not run against a clean base.
- `pnpm exec vitest run src/views/apps`: 239 files, 1585 tests passed.
- `pdm run lint`: passed. `pdm run typecheck`: passed.
- No browser walk was run. Behavior on staging is unverified until the next staging walk.

## Residual

The drawer shows its own blank-title cue (`!document.title.trim()`) next to the server verdict; it
gates nothing, but it is a second client-side reading of "blank".

Commit: c7226069b8d6ac326e9927f6b868b2ffa5645ae6
