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

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| R1  | Root cause: `ReplayProvider.complete_structured` names the reply `request.item_id.replace(":", "_")` and serves it once the file exists. The request text never takes part in the match. |
| R2  | The `label_b` key load (sidecar parity assertion included) and the key match move from `RecordedTransport` into one shared test-support module under `tests/fixtures/`. `RecordedTransport` and `ReplayProvider` both import it; no copy of the logic remains. |
| R3  | `ReplayProvider` loads the keys for `root / exam` when it is constructed. A `label_b_*.json` without its `.request.txt`, or a sidecar without its recording, is refused there. |
| R4  | An `item_type_label` request is matched only on `request.user_payload` ending with `### Question q1\n<key>` against an unused recording. An unmatched request raises `MissingRecording`. The provider has no id-derived fallback. |
| R5  | No re-recording and no live model calls; the converter-batch anchor match is out of scope. |
