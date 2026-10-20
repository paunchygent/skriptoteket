---
type: task
id: TASK-SKRIPT-41-02-05
title: A guest draft that Mina filer rejects for good stops retrying and is offered for download or removal
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-19'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - A guest draft the server rejects for good (any 4xx except 401, 408 and 429, a declared picture without bytes, or a draft without its position snapshot) is posted at most once per draft cursor; later page loads make no POST and show one notice
  - The notice says the exam could not be moved to Mina filer and offers two glyph actions, download as a file and remove from the browser, with names only in tooltip and aria-label
  - A full Mina filer gets its own notice with a retry glyph beside download and remove, and is never retried automatically
  - Transient failures (network, 5xx, 408, 429) render the workspace, show one honest toast and retry up to three times with doubling delay; a late success shows a toast and keeps the open exam
  - A 401 or superseded sign-in records nothing and shows nothing; the next signed-in load tries again
  - A draft whose position snapshot is missing no longer stops the signed-in workspace from rendering
story: ST-SKRIPT-41-02
backlog_document_profile: contract-derived
---

## Resume here

- 2026-10-19, lead 489a15c8 (retained root `01a1567f-d4fd-7c19-bd60-8c62b95f38ae`), branch
  `codex/task-skript-41-02-guest-handover-rejection-remote` from `2338b1af`.
- Done: U0 server `vault_full` marker and U1 pure classifier (`99bf9df4`); U2a handoff outcome
  and rejection record (`5ea99521`); U2b host controller (`4cd29ddc`). 56 focused tests green.
- Fail-first: a disposable probe on the pre-fix commit `2338b1af` failed 11 of 11 cases
  (`evidence/fail-first/` in the retained root).
- U3 notice and host wiring (`fdc5758a`); U4 component-rendered screenshots and string inventory
  (`evidence/copy/`). Merged origin/main `98cbab6c` as `d16e1653`; domain suite there green
  (backend 7900 passed, frontend 4015 passed; `evidence/suite/pdm-test-d16e1653.log`).
- Copy review 917b4838: C6, C7 and C9 replaced as proposed; C1-C5, C8 and C10 approved (D20).
- CSRF 403 `AUTHORIZATION_ERROR` deferred (`a0e8fe5a`, D8).
- Pi review ba74ef97 at `d16e1653`: changes requested (R1 high, R2-R4 medium). Repaired per
  D16-D19: core lock, owner and cursor-owned records (`4cba6dac`); controller removal, stale
  retry and success cleanup after retirement (`d0e03abb`). 96 focused tests green;
  fe-type-check, fe-lint and fe-build green (`evidence/u7a/`, `evidence/u7b/`).
- Next: ba74ef97 rereview of R1-R4, then the staging walk of the rejected-draft notice.
- Work orders: `work/orders/` in the retained root. Explorer maps: `discovery/explorer/`.

## Implementation Contract

The signed-in workspace host (`ExamWorkspaceTeacherHost.vue:32-41`) runs `runGuestHandoff` on
every mount. `useExamWorkspaceGuestHandoff.ts:90-93` catches every throw from the POST to
`/exam-workspace/guest-drafts`, discards the status and code, shows one toast that promises a
reload fixes it, and keeps the draft. A draft the server will never accept is therefore posted
again on every page load, and the toast returns each time (observed on staging `e9983e4f`,
2026-10-19). Beside it, `:81` calls `guestDocumentResponse` outside any try: when the draft has
no position snapshot, `runGuestHandoff` rejects and the workspace never renders.

Hypothesis, not yet observed: the staged draft is `native_exam_document_v8` from before the v9
bump `79ce96e5`, and the server answers 422 `DOCUMENT_SCHEMA_OUTDATED`.

This task changes five things:

1. **Server marker.** Both "Mina filer är fullt" raises in `exam_workspace_document_store.py`
   carry `details: {"reason": "vault_full"}` on the existing 422 `VALIDATION_ERROR`.
2. **One pure classifier** (`examWorkspaceGuestHandoffFailure.ts`): `vault_full`, `permanent`,
   `transient` or `deferred`, from the thrown error's status and the vault marker only.
3. **One attempt, typed outcome.** `runGuestHandoff` posts at most once and returns an outcome.
   Client-side permanent cases are decided before any POST. A permanent or vault-full rejection
   is recorded per draft cursor in one guarded localStorage key; while it matches the draft, no
   POST happens.
4. **Host controller.** The first attempt gates the view as before. Transient failures retry in
   the background with doubling delay, at most three times, cancelled on unmount. The
   controller owns every toast, the download, the removal and the manual retry.
5. **Notice.** `ExamWorkspaceGuestHandoffNotice.vue`, rendered by the teacher host above the
   view like the guest host's notices, states the outcome and offers glyph actions.

## Contract Inputs

- Assignment 489a15c8 from the Hemma orchestrator 944b5a5a, 2026-10-19, with the user decision
  "Offer download or remove". Orchestrator answers the same day: design approved; Q1 toast only
  and keep the open exam; Q2 403 is permanent; Q3 JSON without pictures accepted for now; Q4 one
  click, no confirm, filename `<provets titel>.json`; a full Mina filer is not permanent and gets
  its own state with a retry glyph; the server marker is added in this task; copy C1-C8 is
  provisional pending ui-copy review with component-rendered screenshots.
- Explorer maps in the retained root `discovery/explorer/`: E1 server statuses for the route,
  E2 `utils/browserDownload.ts:12`, E3 notices (toasts carry no actions), E4 backoff
  (`useExamWorkspaceEnrichment.ts:131-135`), E5 401 clears auth, 403 CSRF retried once, network
  errors are raw `TypeError`s.
- Original owner: TASK-SKRIPT-41-02-02 (guest sign-in handoff, done; F4+R2 `c8e61d9e`).

## Core Vertical And Performance

One server change (an error detail) and frontend modules around the existing handoff. The
rejection record is one small localStorage read per mount. Background retries are at most three
timers per mount. No performance concern.

## Validation

- Backend: `test_exam_workspace_single_file_contract.py` (create and overwrite paths carry the
  marker; an oversized file does not).
- Frontend focused Vitest: `examWorkspaceGuestHandoffFailure.spec.ts`,
  `examWorkspaceGuestHandoffRejection.spec.ts`, `useExamWorkspaceGuestHandoff.spec.ts`,
  `useExamWorkspaceGuestHandoff.rejection.spec.ts`, the controller spec, the notice spec and
  `ExamWorkspaceTeacherHost.spec.ts`; then `fe-type-check`, `fe-lint`, `fe-build`, `lint`,
  `typecheck`.
- Copy: component-rendered screenshots, labelled as such, of every notice and toast state, with
  a string inventory, to ui-copy review.
- One domain suite for the touched domains on the orchestrator's go; independent review routed
  by the orchestrator.

## Stop Conditions

Stop and report in any of these cases:

- the fix needs a change to the edit lease, sync gate, `useExamWorkspaceHistory` or
  `useExamWorkspaceDocument` (the 40-04 gap lane owns them);
- the fix needs a change to the lease part of `examWorkspaceGuestDraftStorage.ts`;
- the server route returns a status the classifier does not cover;
- the staging walk shows a reason for rejection other than those listed.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                                                                                                                                                              |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | Root cause: `useExamWorkspaceGuestHandoff.ts:90-93` discards the failure and retries on every mount; `:81` can reject before the view renders. The v8 cause is a hypothesis until the walk.                                                                                                                                                                                                                                        |
| D2  | One pure function classifies: 401 and a superseded sign-in are `deferred`; 408, 429, 5xx, other statuses and non-API throws are `transient`; a 422 whose `details.reason` is `vault_full` is `vault_full`; every other 4xx (400, 403, 404, 409, 413, 422) is `permanent`. No message or code text is matched.                                                                                                                      |
| D3  | A declared picture without bytes and a draft without its position snapshot are `permanent` and decided before any POST.                                                                                                                                                                                                                                                                                                            |
| D4  | A `permanent` or `vault_full` rejection is recorded as `{cursor, reason}` in the zod-checked localStorage key `skriptoteket.exam-workspace.guest-handoff-rejection`, every access guarded; a record for another cursor is cleared; no versioned reader. `examWorkspaceGuestDraftStorage.ts` is unchanged.                                                                                                                          |
| D5  | `runGuestHandoff` shows no toast; the host controller owns every user message.                                                                                                                                                                                                                                                                                                                                                     |
| D6  | The first attempt gates the view. A transient failure renders the view, shows one toast and retries at most three times with doubling delay, cancelled on unmount. After the last retry fails one more toast says the next opening tries again.                                                                                                                                                                                    |
| D7  | A late success (background or manual retry) shows a toast and keeps the open exam (Q1).                                                                                                                                                                                                                                                                                                                                            |
| D8  | A 403 with code `FORBIDDEN` (role refusal) and every other 403 is permanent (Q2); a 403 with code `AUTHORIZATION_ERROR` (failed CSRF token refresh) is `deferred` and records nothing (orchestrator, 2026-10-20).                                                                                                                                                                                                                  |
| D9  | Download is client-side: the stored draft record as JSON through `triggerBrowserDownload`, named `<saved title>.json` (Q4). The server exports would reject an outdated draft too.                                                                                                                                                                                                                                                 |
| D10 | Known limit (Q3): the download holds the draft JSON without picture bytes. Follow-up: decide whether pictures travel with the file before release.                                                                                                                                                                                                                                                                                 |
| D11 | Remove is one click with no confirm (Q4): `clearIf(cursor)`, then the record is cleared and the notice closes.                                                                                                                                                                                                                                                                                                                     |
| D12 | A full Mina filer is never retried automatically; its notice adds a retry glyph that posts once, ignoring the record.                                                                                                                                                                                                                                                                                                              |
| D13 | The server marks a full Mina filer with `details: {"reason": "vault_full"}` on the existing 422 `VALIDATION_ERROR`, following the `asset_mismatch` precedent; no new error code.                                                                                                                                                                                                                                                   |
| D14 | The notice is rendered by `ExamWorkspaceTeacherHost.vue` above the view, like the guest host's notices; `ExamWorkspaceView.vue` is unchanged. Actions are glyphs from `uiGlyphs` (`download`, `delete`, `retry`) with names in tooltip and aria-label only.                                                                                                                                                                        |
| D15 | Copy C1-C8 is provisional until ui-copy review approves it.                                                                                                                                                                                                                                                                                                                                                                        |
| D16 | Review ba74ef97 R1: every handoff attempt carries one owner (the auth session captured when the controller is created, plus its disposal flag). `runGuestHandoff` re-checks the owner after every await and returns `deferred` with no POST and no record write once it is retired; the POST is bound to that session through the client's existing `session` option, so a replaced sign-in fails as `SupersededAuthSessionError`. |
| D17 | Review ba74ef97 R4: the server cannot make a failed same-cursor create idempotent (a refused create rolls its claim back), so every handoff attempt and every removal runs inside one cross-tab Web Lock (`navigator.locks`, name `skriptoteket.exam-workspace.guest-handoff`), separate from the edit lease; the draft and the record are re-read after the lock is granted. Specs use an in-memory lock.                         |
| D18 | Review ba74ef97 R2: record mutations are cursor-owned. The record port gains `clearIf(cursor)` and loses its unconditional clear; a failed attempt writes its record only when the stored draft still has the posted cursor; success and removal clear only their own cursor's record.                                                                                                                                             |
| D19 | Review ba74ef97 R3: the manual retry names the held cursor; the recorded rejection is bypassed only when the record is `vault_full` for that same cursor and the stored draft still has it. Any other record is honoured.                                                                                                                                                                                                          |
| D20 | Copy review 917b4838 approved C1-C10 on 2026-10-20 after the C6, C7 and C9 replacements.                                                                                                                                                                                                                                                                                                                                           |
