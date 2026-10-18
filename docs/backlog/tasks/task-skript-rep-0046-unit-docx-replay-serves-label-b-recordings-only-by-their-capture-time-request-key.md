---
type: task
id: TASK-SKRIPT-REP-0046
title: Unit DOCX replay serves label_b recordings only by their capture-time request
  key
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-18'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
  - The unit DOCX replay serves a label_b recording only to a request whose text ends with that recording's capture-time request key
  - A label_b recording without its request.txt sidecar is refused when the replay provider is built
  - The unit replay and the integration RecordedTransport share one key-load and match implementation
backlog_document_profile: contract-derived
---

## Implementation Contract

`ReplayProvider.complete_structured` in `tests/unit/application/curated_apps/handlers/docx_pipeline_replay.py` serves second-pass labeler (`label_b`) replies by request id alone. It derives `label_b_<qid>.json` from `request.item_id` and never reads the request text or the `label_b_<qid>.request.txt` sidecar. A stale recording is therefore served to a changed labeler request. REP-0045 fixed the same defect in the integration `RecordedTransport`, but did not touch the unit replay. The Mac parent ruled on 2026-10-18 that this residual from REP-0045 becomes its own task.

The task moves the REP-0045 key load and match into one shared test-support module. The integration transport and the unit replay both use that module, and the unit replay drops its id-derived path for `label_b`.

Non-goals: changing production code, the labeler, the recordings or the converter-batch anchor match.

## Contract Inputs

- TASK-SKRIPT-REP-0045 (root cause, sidecar format), merged into main at `c0fb9e7c0`.
- `tests/integration/exam_workspace_docx_background_support.py` (`RecordedTransport._label_b_request_keys` and the `item_type_label` branch of `_resolve`).
- Mac parent ruling 2026-10-18 via the Hemma orchestrator.

## Core Vertical And Performance

The vertical is the unit replay of the production DOCX pipeline. Each `item_type_label` request gets its own recording, matched by its capture-time key. No performance concern.

## Validation

- A new adversarial test file: a changed labeler request stays unmatched; a recording without its sidecar is refused; an unchanged request is served its recording.
- `tests/unit/application/curated_apps/handlers/test_exam_workspace_docx_build.py`, which replays all nine recorded exams.
- `pdm run test tests/integration/test_exam_workspace_docx_background.py -m "integration or not integration"` when Docker is available.
- Ruff and mypy on the touched files.

## Stop Conditions

Stop and report to the parent if a unit replay fails because a labeler recording is stale. Never re-record anything and make no live model calls.

## User-Exam Recording Keys (parent ruling 2026-10-18)

The new rule refused the 15 `label_b` recordings in `tests/fixtures/exam_conversion/docx_user_exams/recordings/` (`omprov_grammatik_sve2` q1-q8, `exempelprov_grammatik_sve2_v2_1` q1-q5, q7, q8), because they had no sidecars. They were added at `b7ca932c` (2026-10-18), after the `c67dcb70` points-line change. The parent ruled that their keys are captured as that revision built the requests, not from today's request text.

Method: a detached throwaway worktree at `b7ca932c` replayed both exams through that revision's production DOCX pipeline, with that revision's `src` first on the import path. Each `item_type_label` request's text after `### Question q1` became the sidecar. Every request held one question and no images. The disposable script is `evidence/probes/capture_user_exam_label_b_keys.py` in retained root `01a14f5e`, and the worktree was removed afterwards. Today's pipeline matches all 15 keys, so the request text has not changed since `b7ca932c`. This proves the recordings are current only on the assumption that they were captured against `b7ca932c`'s own code; the commit message supports that, but it is an assumption. This replaces the REP-0045 derivation (raw manifest, no points-line placement). That derivation fit the pre-`c67dcb70` recordings, but it would give the wrong text at `b7ca932c`. No live calls were made and nothing was re-recorded.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| R1  | Root cause: `ReplayProvider.complete_structured` names the reply `request.item_id.replace(":", "_")` and serves it once the file exists. The request text never takes part in the match. |
| R2  | The `label_b` key load (sidecar parity assertion included) and the key match move from `RecordedTransport` into one shared test-support module under `tests/fixtures/`. `RecordedTransport` and `ReplayProvider` both import it; no copy of the logic remains. |
| R3  | `ReplayProvider` loads the keys for `root / exam` when it is constructed. A `label_b_*.json` without its `.request.txt`, or a sidecar without its recording, is refused there. |
| R4  | An `item_type_label` request is matched only on `request.user_payload` ending with `### Question q1\n<key>` against an unused recording. An unmatched request raises `MissingRecording`. The provider has no id-derived fallback. |
| R5  | No re-recording and no live model calls; the converter-batch anchor match is out of scope. |

## Resume Here (2026-10-18)

- State: in independent review; reviewer pending. Branch `codex/task-skript-rep-0046-remote` in worktree `/home/paunchygent/apps/skriptoteket-task-skript-rep-0046-remote`; implementation head `bcc4047c`.
- Done: the shared key module, the unit replay key match, the 15 user-exam capture-time sidecars and the adversarial test file. Proof: new test file 12/12, user-exam replay 10/10, other replay importers 1150 passed, Docker integration 11/11, ruff, format and mypy clean.
- Next: the parent routes the review verdict; repair any admitted findings.
- Open findings: none. A note for the reviewer: the key does not cover the fixed classification instruction (same as in REP-0045).
- Retained root: `/home/paunchygent/apps/skriptoteket/.orchestration/context/sessions/01a14f5e-1cc7-74d6-abf4-0d911114f415`.
- Blockers and user gates: none. No children are running.
