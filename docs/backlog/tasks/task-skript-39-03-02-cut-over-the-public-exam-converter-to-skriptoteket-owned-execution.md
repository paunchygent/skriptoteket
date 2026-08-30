---
type: task
id: TASK-SKRIPT-39-03-02
title: Cut over the public Exam Converter to Skriptoteket-owned execution
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-08-30'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - An anonymous user completes the existing public Exam Converter workflow through the unchanged Skriptoteket public API and locally produced jobs and artifacts without a request reaching Sir Convert and without new public remote-provider behavior
story: ST-SKRIPT-39-03
backlog_document_profile: contract-derived
---

## Implementation Contract

Keep the existing public UI and Skriptoteket public API contract while replacing
`PublicExamConverterSirConvertProtocol` execution with Skriptoteket-owned jobs,
conversion, results, artifact manifests, and downloads.

- Preserve anonymous upload limits, concurrency controls, transient job
  handles, polling, target selection, optional graded-result evidence,
  warnings, manual follow-up reporting, and named artifact downloads.
- Remove the production path's dependency on Sir submission grants, upstream
  job identifiers, and Sir artifact-read leases.
- Add no public Luna, GLM, answer-key-completion, or other remote-provider
  behavior.
- Leave deletion of now-unconsumed Sir surfaces to
  `TASK-SKRIPT-39-03-03`.

## Contract Inputs

- `ST-SKRIPT-39-03` terms S1-S5.
- The current public frontend already calling Skriptoteket endpoints.
- The public handler, transient job store, rate/size/concurrency controls,
  status/result/manifest/download models, and in-process producer/artifact
  seams.
- The current public product behavior is the contract to preserve.

## Core Vertical And Performance

An anonymous user submits through the existing public UI, receives the existing
transient public job handle, follows it through the existing Skriptoteket
endpoints, and downloads the requested locally produced artifacts without a
request reaching Sir Convert.

The current public request budget and asynchronous job behavior remain intact;
conversion does not become an unbounded synchronous public request.

## Validation

- Focused backend and frontend checks cover the unchanged public API/UI against
  the local producer, including success, limits, expiry, failure, warnings,
  manual follow-up, manifest, and download behavior.
- A live public conversion through the deployed Hemma surface exercises
  submission, polling, result reporting, artifact discovery, and download with
  real input.
- Affected quality gates, docs validation, and `git diff --check` pass.

## Stop Conditions

- Stop rather than change the public product contract to fit the local
  implementation.
- Do not introduce remote answer-key completion into the public lane.
- Do not complete the task while public execution still depends on Sir.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                  |
| --- | ---------------------------------------------------------------------------------------------------------------------- |
| T1  | The public UI and API remain stable while their producer implementation becomes Skriptoteket-owned.                    |
| T2  | Limits, transient lifecycle, optional evidence, targets, warnings, follow-ups, manifests, and downloads are preserved. |
| T3  | The public lane gains no Luna, GLM, answer-key-completion, or other remote-provider behavior.                          |
| T4  | The production public execution path no longer needs Sir grants, upstream jobs, or artifact leases.                    |
