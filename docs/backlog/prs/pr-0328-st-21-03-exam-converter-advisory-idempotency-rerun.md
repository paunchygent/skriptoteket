---
type: pr
id: PR-0328
title: "ST-21-03 Exam Converter advisory idempotency rerun"
status: done
owners: "agents"
created: 2026-05-17
updated: 2026-05-17
stories:
  - "ST-21-03"
tags:
  - frontend
  - authenticated
  - conversion-hub
  - sir-convert
  - huleedu
  - llm
  - idempotency
  - proof-blocker
acceptance_criteria:
  - "Given an authenticated advisory Exam Converter submit replays a prior Sir Convert job, when the returned `answer_key_completion_report` contains eligible machine-marked items but all such items failed with `provider_request_failed`, then Skriptoteket must not silently treat that replay as the current live answer-key proof."
  - "Given the teacher explicitly retries advisory enrichment after a provider/runtime failure, when Skriptoteket resubmits the same `.dxe` and same job spec, then the request carries a bounded `advisoryRetryAttempt` marker that changes the Sir Convert `Idempotency-Key` while preserving normal duplicate-submit protection for accidental double clicks."
  - "Given a retry job returns a fresh `answer_key_completion_report`, when valid candidates are present, then the AI-facit review UI renders those candidates and the previous failed replay no longer controls the teacher-visible state."
  - "Given the provider lane is still failing, when the explicit retry produces another provider-only failure report, then the UI remains in the normal missing-key state and surfaces the approved retry affordance without automatically looping or weakening the reviewed-completion contract."
  - "Given accepted-current-state export remains separate, when a prior advisory report has provider failures, then the source-evidence-only `Godkänn` path still requires its own explicit teacher action and must not be confused with reviewed AI-facit."
  - "Given the live proof is rerun after implementation, when the same byte-identical `.dxe` is used by `paunchygent@gmail.com`, then retained operator evidence proves a fresh Sir Convert job id, a non-replay create response, and valid candidate payloads when Qwen is healthy."
---

# PR-0328: ST-21-03 Exam Converter Advisory Idempotency Rerun

## Bug Report

Live tested authenticated Exam Converter conversions can appear to fail LLM
enrichment in the UI even when the current Qwen provider container is healthy.
The failure mode is stale Sir Convert idempotent replay:

```text
same .dxe + same job spec -> same Idempotency-Key -> old failed Sir job replayed
```

This is not a current Qwen inference failure. It is a consumer retry semantics
bug in the authenticated Skriptoteket flow.

## Current Evidence

Operator investigation on Hemma on 2026-05-17 found:

- Latest authenticated Skriptoteket flow POSTed and fetched Sir Convert job:
  `jobv2_c93420ae30f441cc8e4013cd2d`.
- Sir Convert logs showed the authenticated caller path fetching the advisory
  report for that job:
  `GET /v2/convert/jobs/jobv2_c93420ae30f441cc8e4013cd2d/artifacts/answer_key_completion_report`
  returned `200`.
- The report at
  `/var/lib/sir-convert-a-lot/prod/jobs_v2/jobv2_c93420ae30f441cc8e4013cd2d/artifacts/answer-key-completion-report.json`
  contains:
  - `schema_version=answer_key_completion_report_v1`;
  - `17` items;
  - `8` eligible machine-marked items;
  - all `8` eligible items have
    `backend_failure_code=provider_request_failed`;
  - `0` answer payloads.
- The idempotency record for that job is
  `/var/lib/sir-convert-a-lot/prod/idempotency/c67e318d394346c0da076e5be49a906b4f26999648025a937a3620c7ff1bb41c.json`
  and was created at `2026-05-17T02:58:31Z`.
- A current in-container probe from `sir_convert_a_lot_prod` to
  `sir_convert_qwen_answer_key:8082` returned `200` and valid JSON Schema
  output:
  - endpoint:
    `http://sir_convert_qwen_answer_key:8082/v1/chat/completions`;
  - model: `qwen3.6-27b-q6k-mtp`;
  - returned content:
    `{"correct_alternative_ids":[2]}`.
- Newer Sir Convert jobs after the repaired Qwen/runtime lane do produce valid
  advisory answer payloads:
  - `jobv2_4263624111764e0d83c45ab3df`: `6` valid answer payloads;
  - `jobv2_4d1d54c4382a40b7a13773f266`: `6` valid answer payloads.

## Evidence Commands

The operator evidence above came from these command classes:

```bash
pdm run run-hemma -- bash -lc 'sudo -n docker logs --since=90m sir_convert_a_lot_prod 2>&1 | grep -Ei "digiexam|answer|completion|provider|qwen|failed|error|exception|job" | tail -n 240'
```

```bash
pdm run run-hemma -- bash -lc 'sudo -n docker exec sir_convert_a_lot_prod python -c "... summarize answer-key-completion-report.json ..."'
```

```bash
pdm run run-hemma -- bash -lc 'sudo -n docker exec sir_convert_a_lot_prod python -c "... inspect idempotency record for jobv2_c93420ae30f441cc8e4013cd2d ..."'
```

```bash
pdm run run-hemma -- bash -lc 'sudo -n docker exec -i sir_convert_a_lot_prod python - <<PY
# POST JSON Schema probe to
# http://sir_convert_qwen_answer_key:8082/v1/chat/completions
PY'
```

The retained implementation proof should replace these abbreviated command
classes with exact command output snippets or sanitized artifacts.

## Linked Files

Skriptoteket authority and consumer surfaces:

- `docs/backlog/stories/story-21-03-exam-converter-public-and-authenticated-artifact-lanes.md`
- `docs/backlog/prs/pr-0324-st-21-03-exam-converter-authenticated-end-to-end-proof.md`
- `docs/backlog/prs/pr-0326-st-21-03-exam-converter-authenticated-llm-enrichment-consumer-sync.md`
- `frontend/apps/skriptoteket/src/api/sirConvertGateway/requestContext.ts`
- `frontend/apps/skriptoteket/src/api/sirConvertGateway/jobSpec.ts`
- `frontend/apps/skriptoteket/src/api/sirConvertGateway/client.ts`
- `frontend/apps/skriptoteket/src/views/apps/exam-converter-authenticated/useExamConverterAuthenticatedRuntime.ts`
- `frontend/apps/skriptoteket/src/views/apps/exam-converter-authenticated/useExamConverterReviewArtifacts.ts`
- `frontend/apps/skriptoteket/src/views/apps/exam-converter-authenticated/digiexamAnswerKeyCompletionReport.ts`

Sir Convert producer/runtime evidence surfaces:

- `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/scripts/sir_convert_a_lot/interfaces/http_routes_jobs_v2.py`
- `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/scripts/sir_convert_a_lot/infrastructure/idempotency_store.py`
- `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/scripts/sir_convert_a_lot/infrastructure/structured_llm_provider.py`
- `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/scripts/sir_convert_a_lot/infrastructure/structured_llm_payloads.py`
- `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/backlog/tasks/task-320-containerize-qwen3-6-answer-key-provider-for-hemma-production.md`

## Root Cause

`requestContext.ts` correctly makes the normal authenticated Sir Convert
idempotency key deterministic from the canonical job spec plus uploaded file
bytes and companion evidence. That protects ordinary duplicate submits.

For advisory answer-key completion, however, a deterministic replay can preserve
an obsolete provider-runtime failure after the operator has repaired Qwen. The
browser-visible flow then fetches a stale `answer_key_completion_report` from
the old job, and the teacher sees missing facit even though the current
provider can now produce valid candidates.

The specific stale job is inside Sir Convert's normal idempotency window, so
Sir Convert is behaving as designed. The missing behavior belongs in
Skriptoteket's explicit retry path for advisory enrichment.

## Required Product Behavior

Skriptoteket must preserve two facts at the same time:

- deterministic idempotency is still required for normal submit safety; and
- explicit retry after provider-runtime failure must produce a fresh Sir
  Convert job instead of silently reusing an obsolete failed advisory report.

The teacher should not need to understand provider internals or idempotency.
The UI can keep the normal missing-key state, but the retry action must create a
new upstream attempt when the prior advisory report proves that all eligible
machine-marked suggestions failed due `provider_request_failed`.

## Recommended Implementation

Implement a narrow advisory retry attempt in the authenticated Exam Converter
runtime state.

Recommended shape:

1. Detect provider-only advisory failure after artifact load:
   - completion mode is `local_llm_suggest_missing_machine_marked`;
   - `answer_key_completion_report` exists;
   - at least one supported machine-marked item is eligible for a
     facitförslag;
   - every eligible candidate attempt ended with
     `backend_failure_code=provider_request_failed`;
   - there are no valid answer payloads.
2. Show the approved teacher-facing retry affordance in the existing
   review/status area:
   - status text: `Det gick inte att ta fram ett facitförslag.`;
   - action: a button with a Lucide retry-style icon and label
     `Försök igen`;
   - visible copy must not describe AI, provider, idempotency, replay, Qwen,
     Sir Convert, or other internal machinery.
3. On explicit retry, use `advisoryRetryAttempt`, not a random nonce. The
   value is a positive integer starting at `1`.
4. Include that retry marker in the idempotency digest only for authenticated
   advisory completion submits. Do not send it as a new Sir Convert semantic
   field unless a producer contract explicitly adds one later.
5. Preserve the same Sir Convert job spec and `.dxe` bytes so the retry changes
   only transport idempotency, not conversion semantics.
6. Clear reviewed AI-facit decisions and loaded artifacts before the retry
   submit, because the prior report no longer owns current teacher review
   state.
7. Keep double-click protection for the same retry attempt. Repeated clicks of
   one retry affordance must reuse the same retry attempt key while that
   attempt is in flight. A later explicit retry may increment the attempt only
   after the previous retry attempt has completed and still produced the same
   provider-only advisory failure class.
8. Record whether the returned create response is an idempotent replay via the
   existing `idempotentReplay` field, and treat a retry response that still
   points to the old failed job as a proof failure.

## Rejected Options

- Restarting Qwen:
  rejected because the current in-container JSON Schema probe succeeds and
  newer jobs already have valid candidates.
- Asking teachers to modify the `.dxe` file:
  rejected as an operator workaround, not product behavior.
- Randomizing every submit:
  rejected because it destroys ordinary idempotency and duplicate-submit
  protection.
- Automatically looping retries:
  rejected because provider/runtime failures can be real outages and should not
  create hidden conversion churn.
- Treating provider-failed advisory reports as accepted-current-state:
  rejected because accepted-current-state export and reviewed AI-facit are
  separate teacher decisions.

## Open Questions and Recommendations

All open questions have a recommended default for approval before code
implementation:

1. Retry trigger:
   recommended: enable retry only for provider-only advisory failures where all
   eligible machine-marked candidate attempts failed with
   `provider_request_failed` and no valid candidate payloads exist.
2. Retry affordance:
   recommended: surface one compact action in the existing authenticated review
   status area. The approved UI shape is status text
   `Det gick inte att ta fram ett facitförslag.` plus a button with a Lucide
   retry-style icon and label `Försök igen`. Do not expose AI/provider,
   idempotency, replay, Sir Convert, Qwen, or other internal state as visible
   product copy.
3. Retry attempt storage:
   recommended: keep it browser-runtime local for this slice. Do not persist
   retry counters to Skriptoteket backend unless a later job-history feature
   needs it.
4. Idempotency-key shape:
   recommended: add `advisory_retry_attempt:<n>` to the client-side digest parts
   for advisory retries only. Use `advisoryRetryAttempt`, not a random nonce.
   The value is a positive integer starting at `1`, is included only for
   authenticated advisory completion submits, and may increment only after the
   previous retry attempt has completed and still produced the same
   provider-only advisory failure class. Do not mutate
   `digiexam_migration_options` for Sir Convert.
5. Automatic retry:
   recommended: do not automatically retry on page load or artifact load. The
   teacher or operator must explicitly trigger retry after a provider-only
   failure.
6. PR-0324 proof rerun:
   recommended: after implementation, rerun the live proof with the same
   byte-identical `.dxe` from `paunchygent@gmail.com` and retain evidence that
   the retry produced a fresh Sir job with valid AI-facit candidates.

## Implementation Plan

1. Extend the authenticated runtime state with advisory retry attempt tracking.
2. Extend `requestContext.ts` so `buildSirConvertRequestContext` can include a
   bounded advisory retry marker in the idempotency digest.
3. Keep `jobSpec.ts` unchanged unless tests prove the current canonical job spec
   cannot preserve the contract.
4. Add a report classifier near `digiexamAnswerKeyCompletionReport.ts` or the
   review-artifact projection that identifies provider-only advisory failure.
5. Wire the retry affordance through
   `useExamConverterAuthenticatedRuntime.ts` and the authenticated review/status
   component without weakening normal submit-state guards.
6. Ensure retry clears stale artifacts and reviewed decisions before submit.
7. Add focused tests for:
   - no retry marker on normal first submit;
   - same retry attempt remains idempotent while in flight;
   - the first retry uses `advisoryRetryAttempt=1`, not a random nonce;
   - incremented retry attempt changes the key only after a completed retry
     still produced the same provider-only advisory failure class;
   - retry is offered only for provider-only advisory failure;
   - valid candidates do not show retry;
   - the retry affordance uses the approved status text, Lucide retry-style
     icon, and `Försök igen` label without internal AI/provider/idempotency
     wording;
   - accepted-current-state remains separate.
8. Rerun the live authenticated proof and retain sanitized evidence under the
   `PR-0324` rerun.

## Test Plan

Implemented in this slice:

- `requestContext.ts` and `types.ts` accept a bounded
  `advisoryRetryAttempt` only for authenticated advisory completion submits and
  include `advisory_retry_attempt:<n>` only in the client idempotency digest.
- The Sir Convert job spec/options remain unchanged; retry changes transport
  idempotency, not conversion semantics.
- `digiexamAnswerKeyCompletionReport.ts` owns the provider-only advisory
  failure classifier.
- `ExamConverterAuthenticatedView.vue` and
  `useExamConverterAuthenticatedRuntime.ts` keep retry state browser-runtime
  local, start at attempt `1`, and allow a new increment only after the prior
  retry completed with the same provider-only failure class.
- `ExamConverterAdvisoryRetryPanel.vue` and
  `ExamConverterWorkspaceShell.vue` render the approved product copy:
  `Det gick inte att ta fram ett facitförslag.` plus a Lucide retry icon and
  `Försök igen`.
- The dev/test-only `provider-only-advisory-failure` fixture supports
  authenticated internal-browser inspection of the real app surface.

Executed verification:

- `pdm run fe-test -- --run src/api/sirConvertGateway/requestContext.spec.ts src/views/apps/ExamConverterAuthenticatedAdvisoryRetry.spec.ts src/views/apps/ExamConverterAuthenticatedRuntimeBridgeSlice.spec.ts src/views/apps/ExamConverterAuthenticatedReviewSlice.spec.ts src/views/apps/ExamConverterAuthenticatedUiInspectionFixtures.spec.ts src/router/routes.spec.ts`
  passed, 6 files / 37 tests.
- `pdm run fe-type-check` passed.
- `pdm run fe-lint` passed.
- `pdm run fe-build` passed with the existing Vite large-chunk warning.
- Production bundle grep found no fixture-route or fixture-id strings:
  `provider-only-advisory-failure`, `complete-qti-blocked`,
  `complete-qti-ready`, `missing-facit`, `ai-facit-review`,
  `exam-converter-ui-inspection`, or `ui-fixtures`.
- Internal browser proof through the HuleEdu login ceremony opened
  `/apps/documents.conversion_hub/exam-converter/ui-fixtures/provider-only-advisory-failure`
  and verified the retry panel is visible, the retry action is visible, the
  approved status text is visible, the `Försök igen` label is visible, one
  Lucide SVG icon is present, and the retry panel does not contain `AI-facit`
  or provider wording.
- `pdm run docs-validate`, `pdm run handoff-validate`, and `git diff --check`
  passed after closeout updates.

Live proof after implementation:

- Start with the same byte-identical `.dxe` that previously replayed
  `jobv2_c93420ae30f441cc8e4013cd2d`.
- Submit through authenticated Skriptoteket as `paunchygent@gmail.com`.
- Verify the first response is identified as stale provider-only failure if it
  replays the old job.
- Trigger the explicit retry.
- Verify the new Sir Convert job id differs from
  `jobv2_c93420ae30f441cc8e4013cd2d`.
- Verify `X-Idempotent-Replay` is not controlling the retry create response.
- Verify the new `answer_key_completion_report` has valid non-null candidates
  when Qwen is healthy.
- Verify the right-panel reviewed facitförslag affordances render from the
  fresh report.

The live `PR-0324` proof rerun remains the next governed proof slice because it
requires the exact byte-identical `.dxe`, authenticated Gateway traffic as the
operator account, and retained Sir Convert job evidence.

## Stop Conditions

- Stop if the retry requires direct browser calls to `convert.hule.education`,
  Sir Convert service credentials, or raw HuleEdu identity material.
- Stop if the implementation randomizes all submissions instead of only
  explicit advisory retries.
- Stop if the implementation uses a random retry nonce instead of the bounded
  integer `advisoryRetryAttempt` contract.
- Stop if the retry failure affordance exposes AI/provider/idempotency/replay
  internals as teacher-facing copy.
- Stop if a provider-only failed report can still silently remain the active
  AI-facit proof after an explicit retry.
- Stop if retry mutates the Sir Convert semantic job spec without a governed
  producer contract change.
- Stop if the UI treats provider failure as source truth, reviewed truth, or
  accepted-current-state export.

## Rollback Plan

Remove the advisory retry marker, provider-only failure classifier, and retry
affordance. Normal deterministic authenticated submits and the separate
accepted-current-state path must continue to work because this slice only
changes explicit advisory retry behavior.
