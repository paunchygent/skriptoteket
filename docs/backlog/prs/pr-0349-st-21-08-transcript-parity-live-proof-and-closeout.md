---
type: pr
id: PR-0349
title: "ST-21-08 Transcript parity live proof and closeout"
status: blocked
owners: "agents"
created: 2026-06-13
updated: 2026-06-13
stories:
  - "ST-21-08"
tags:
  - proof
  - browser
  - gateway
  - transcript
  - formatter
  - user-files
dependencies:
  - "PR-0344"
  - "PR-0345"
  - "PR-0346"
  - "PR-0347"
  - "PR-0348"
  - "HuleEdu TASK-0676"
  - "Sir Convert task-361"
acceptance_criteria:
  - "Given a signed-in teacher uses the transcript lane through the HuleEdu browser-session ceremony, when a long-running job is submitted, then retained evidence shows truthful progress fields rendering through Gateway."
  - "Given cancel is requested for a running transcript job, when the product receives the abort outcome, then retained evidence shows clear cancel feedback and no invalid follow-up action."
  - "Given a saved transcript has speaker names, when TXT, Markdown, VTT, and SRT are exported, then retained evidence proves exported artifacts use overlay display names and do not fall back to `speaker_00` labels."
  - "Given overlay-aware artifacts are available, when download and save to Mina filer are used, then retained evidence proves both actions work through authorized artifact references."
  - "Given the parity proof closes, when docs and handoff are updated, then ST-21-08 records what is done and any future search/sharing/indexing work remains separate."
---

# PR-0349: ST-21-08 Transcript Parity Live Proof And Closeout

## Problem

The transcript lane spans three repos and cannot be considered parity-complete
without authenticated product evidence.

## Goal

Retain end-to-end proof for progress, cancel feedback, speaker overlays,
overlay-aware exports, downloads, and Mina filer saves.

## Non-goals

- No new production behavior beyond proof hardening and documentation closeout.
- No direct product-backend credential shortcuts.
- No direct Sir Convert browser proof.

## Implementation Plan

- Use the HuleEdu browser-session ceremony and repo proof helpers.
- Run a fresh transcript job and capture progress rendering.
- Exercise cancel feedback on a controlled job where cancellation is valid.
- Save canonical transcript JSON, name speakers, replay formatter exports, and
  verify TXT/Markdown/VTT/SRT artifact content uses display names.
- Download each artifact and save at least one representative artifact to Mina
  filer.
- Update ST-21-08, EPIC-21, reviews if created, `.codex/handoff.md`, and the
  development changelog as required by the repo.

## Test Plan

- Authenticated browser proof with retained sanitized artifacts.
- Focused regression tests touched by proof harness adjustments.
- Full docs/handoff validation and `git diff --check`.

## Evidence Log

### 2026-06-13 Cross-Repo Smoke And Blocked Live Proof Rerun

HuleEdu `TASK-0676` and Sir Convert `task-361` are approved upstream
dependencies for this closeout. The cross-repo trust-profile smoke is green,
but the live product proof still blocks at the runtime Sir Convert
internal-identity verifier:

- HuleEdu retained review approved `TASK-0676`:
  `/Users/olofs_mba/Documents/Repos/huleedu/docs/backlog/reviews/review-task-0676-01-ruthless-review-task-0676-internalidentitycontextv1-trust-profile.md`.
- Sir Convert retained review approved `task-361`:
  `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/backlog/reviews/review-46-ruthless-review-task-361-huleedu-internalidentitycontextv1-trust-profile-consumption.md`.
- HuleEdu profile publisher passed for `local-auth-integration` and
  `hemma-production`:
  `pdm run run-local-pdm hemma-sir-convert-internal-identity-trust-profile --environment local-auth-integration`
  and
  `pdm run run-local-pdm hemma-sir-convert-internal-identity-trust-profile --environment hemma-production`.
  Both emitted sanitized profile metadata with canonical DER SPKI fingerprint
  `46aefc0edc2f71267e2df783ca27f4df2b0da269cc7e84b43cbe2de6ac7c1992`.
- Sir Convert approved Task 361 smoke passed:
  `pdm run pytest-root tests/sir_convert_a_lot/test_huleedu_internal_identity_trust_profile_v1.py tests/sir_convert_a_lot/test_structured_llm_settings_route_v2.py tests/sir_convert_a_lot/test_digiexam_migration_access_control_api_v2.py tests/sir_convert_a_lot/test_compose_contract.py tests/sir_convert_a_lot/test_local_compose_contract.py -q`
  with `39 passed`.

- HuleEdu shared PostgreSQL migrations verified at Alembic head for
  `batch_orchestrator_db`, `essay_lifecycle_db`, `cj_assessment_db`,
  `class_management_db`, `file_service_db`, `file_service_content_db`,
  `spellchecker_db`, `result_aggregator_db`, `nlp_db`,
  `batch_conductor_db`, `identity_db`, `email_db`, and `entitlements_db`:
  `HULEEDU_ENV_OVERLAY_FILE=output/tmp/pr0349-shared-postgres-migrations.env pdm run run-local-pdm db-lifecycle verify --all`.
- Skriptoteket dev DB migration state upgraded cleanly:
  `pdm run dev-stack db-upgrade`.
- Canonical local stacks were healthy:
  `HULEEDU_ENV_OVERLAY_FILE=output/tmp/pr0349-sir-convert-tunnel.env pdm run run-local-pdm auth-integration check`
  and `pdm run dev-stack ps`.
- Gateway was corrected from the closed default `host.docker.internal:8085` to
  the canonical tunnel backend `http://host.docker.internal:28085` through the
  HuleEdu env-overlay + `dev-recreate api_gateway_service` path. Container-side
  `/readyz` to that backend returned ready.
- A focused red/green harness remediation added blocked-run summary tests.
  Red evidence:
  `pdm run test tests/unit/scripts/test_playwright_pr_0349_summary_truthfulness.py`
  failed before implementation because the finalizer functions did not exist.
  Green focused command:
  `pdm run test tests/unit/scripts/test_playwright_pr_0349_summary_truthfulness.py tests/unit/scripts/test_playwright_script_surface.py tests/unit/scripts/test_conversion_hub_transcript_docs_guard.py`
  passed with `8 passed`.
- Retained browser proof artifact after the remediation:
  `.artifacts/playwright-pr-0349-transcript-parity-live/20260613T153843Z/proof-summary.json`.
  The summary keeps `status=failed` and now records the typed
  `sir_convert_internal_identity_rejected` object as the primary `failure`;
  the generic Playwright timeout is retained only as `raw_failure`.
- The artifact manifest now lists only captured files:
  `network.bounded.json`, `browser-console.bounded.json`, and `failure.png`.
- Retained network evidence:
  `.artifacts/playwright-pr-0349-transcript-parity-live/20260613T153843Z/network.bounded.json`
  records `POST /sir-convert/v2/convert/jobs?wait_seconds=0` as HTTP `401`
  with `error_code=auth_invalid_internal_identity` and
  `reason=invalid_internal_identity_signature`.
- Read-only Hemma/Sir Convert verification showed the local HuleEdu public-key
  fingerprint `b1e569219f6045be01bd89a1907e515c9a9d5c2e800bc2dacf593027a3d7b4b2`
  does not match the Sir Convert prod trusted public-key fingerprint
  `db96ea08a821bb9eb8a7fbd24ca9f5730834f5018af945b1a1200118c9e11f63`.

### Acceptance State

- Signed-in teacher reaches the transcript lane through the HuleEdu
  browser-session ceremony: proven locally before submit.
- Truthful progress rendering through Gateway: not proven; submit is rejected
  before a job exists.
- Cancel feedback on a valid controlled job: not proven; no cancellable job is
  created after the rejected submit.
- Save canonical transcript JSON: not proven in this PR-0349 run.
- Rename speakers via saved transcript overlay UI/API: not proven in this
  PR-0349 run.
- Replay export TXT, Markdown, VTT, and SRT: not proven in this PR-0349 run.
- Exported artifact content overlay-label check: not proven in this PR-0349
  run.
- Download overlay-aware artifacts and save representative artifact to Mina
  filer: not proven in this PR-0349 run.

The blocker is outside Skriptoteket product behavior: the HuleEdu/Sir Convert
code-level trust-profile contract now smokes green, but the live Sir Convert
runtime reached by the sanctioned local browser-session path still rejects the
Gateway-signed identity context. Do not mark `PR-0349` or `ST-21-08` complete
until the deployed/runtime trust lane is reconciled or a sanctioned Hemma/prod
proof lane proves the same local changes.

## Rollback Plan

Leave PR-0344 through PR-0348 behavior intact and keep ST-21-08 open with the
failed proof recorded as the blocker.
