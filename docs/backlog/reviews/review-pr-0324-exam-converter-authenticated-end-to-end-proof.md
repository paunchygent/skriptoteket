---
type: review
id: REV-PR-0324
title: "Review: PR-0324 Exam Converter authenticated end-to-end proof"
status: changes_requested
owners: "agents"
created: 2026-05-13
updated: 2026-05-13
reviewer: "codex"
prs:
  - PR-0324
links:
  - EPIC-21
  - ST-21-03
  - PR-0318
  - PR-0322
  - PR-0325
---

# Review: PR-0324 Exam Converter Authenticated End-to-End Proof

## TL;DR

Verdict: `changes_requested`.

`PR-0324` cannot proceed to live authenticated proof yet. The proof slice hit
its own stop condition during preflight: there is no authenticated bespoke Exam
Converter host surface, the authenticated backend Conversion Hub surface still
models generic document routes rather than the DigiExam artifact-bundle flow,
and downloaded Sir Convert named artifacts cannot currently be saved into
owner-scoped user files.

## Problem Statement

`PR-0324` was intended to prove authenticated submit, poll, result, artifact
manifest, named download, save-to-user-files, missing-auth rejection, and
Gateway-only browser authority. That proof requires a runnable authenticated
Exam Converter product surface and a persistence path for named Sir Convert
artifacts. The current runtime is not yet shaped that way.

## Proposed Solution

Create and implement `PR-0325` as a narrow remediation slice before rerunning
`PR-0324`. The remediation should register an authenticated Exam Converter host
view, wire the authenticated flow to the existing HuleEdu Gateway client, add
or adapt a server-side owner-scoped save path for Sir Convert named artifacts,
and retain focused tests for the new authenticated UI/runtime/save behavior.

`PR-0324` should remain blocked until `PR-0325` is done and reviewable.

## Artifacts to Review

| Artifact | Focus | Time |
|----------|-------|------|
| `frontend/apps/skriptoteket/src/views/curatedAppHostRegistry.ts` | Authenticated host registration for `documents.conversion_hub` | 5 min |
| `frontend/apps/skriptoteket/src/api/sirConvertGateway/client.ts` | Existing HuleEdu Gateway browser client for DigiExam migration | 5 min |
| `frontend/apps/skriptoteket/src/api/sirConvertGateway/saveMetadata.ts` | Save metadata mapper that is not yet consumed by UI/user-file flows | 5 min |
| `src/skriptoteket/web/api/v1/apps_conversion_hub.py` | Authenticated Conversion Hub API shape | 10 min |
| `src/skriptoteket/application/curated_apps/handlers/conversion_hub_jobs.py` | Current generic owned job download handler | 10 min |
| `src/skriptoteket/web/api/v1/vault.py` and `src/skriptoteket/application/scripting/vault.py` | Existing vault save command shape | 5 min |
| `src/skriptoteket/application/curated_apps/classroom_planner/handlers/seating_export_job_completion.py` | Klassrumskartan app-export finalizer pattern | 5 min |
| `src/skriptoteket/web/api/v1/apps_classroom_planner_export_job_contracts.py` | `download_url` + `vault_artifact` DTO pattern | 5 min |

**Total estimated time:** ~50 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Keep `PR-0324` proof-only | The PR explicitly says to stop and create a narrow remediation PR when runtime gaps are found | [x] |
| Implement remediation in `PR-0325` | Avoid mixing proof evidence with product/runtime implementation | [x] |
| Keep public lane untouched | Public grant/read-lease proof is approved and this blocker is authenticated-only | [x] |
| Require owner-scoped save semantics | Authenticated lane acceptance includes save-to-user-files and unrelated-account denial | [x] |

## Review Checklist

- [x] Scope is bounded and appropriate
- [x] Acceptance criteria or proof obligations are reviewable
- [x] Risks and structural fault lines are called out explicitly
- [x] Docs-as-code state remains aligned with implementation readiness
- [ ] Runtime proof can execute against the current product surface
- [ ] Save-to-user-files has retained positive and negative evidence

## Review Feedback

### Blocker: No authenticated Exam Converter host surface exists

`documents.conversion_hub` is registered only for the public host mode:
`frontend/apps/skriptoteket/src/views/curatedAppHostRegistry.ts:47`. Because
there is no authenticated bespoke view, an authenticated teacher cannot run the
Exam Converter submit/status/result/manifest/download/save workflow that
`PR-0324` is supposed to prove.

This blocks live proof because the authenticated lane must be exercised through
the authenticated product surface, not by manually calling lower-level clients.

### Blocker: Authenticated backend runtime is still generic Conversion Hub

`src/skriptoteket/web/api/v1/apps_conversion_hub.py:52` lists generic PDF,
DOCX, Markdown, and HTML routes. `src/skriptoteket/web/api/v1/apps_conversion_hub.py:103`
rejects unsupported route pairs, and `src/skriptoteket/web/api/v1/apps_conversion_hub.py:111`
builds a generic v2 job spec. The submit endpoint at
`src/skriptoteket/web/api/v1/apps_conversion_hub.py:159` accepts the generic
`ConversionHubJobSpecV2` flow, not `.dxe`, `graded_result_pdf`, `parity_pdf`,
`conversion.targets`, result metadata, artifact manifest, and named artifact
bundle semantics.

The owned download handler also proxies one generic artifact through
`src/skriptoteket/application/curated_apps/handlers/conversion_hub_jobs.py:263`,
which is insufficient for the DigiExam migration bundle.

### High: Save-to-user-files is not wired for downloaded Sir Convert artifacts

The frontend metadata mapper exists at
`frontend/apps/skriptoteket/src/api/sirConvertGateway/saveMetadata.ts:1`, but
the module itself says later UI/user-file flows will consume it after named
downloads. The current vault endpoint at `src/skriptoteket/web/api/v1/vault.py:54`
uses `SaveVaultFileCommand`, whose shape in
`src/skriptoteket/application/scripting/vault.py:40` is run/artifact based:
`source_kind`, `run_id`, `artifact_id`, and optional `name`.

That is not a complete owner-scoped persistence path for a downloaded Sir
Convert named artifact with bundle provenance.

Klassrumskartan shows the local pattern to reuse rather than bypass:
`src/skriptoteket/application/curated_apps/classroom_planner/handlers/seating_export_job_completion.py:70`
finalizes an app-owned export by writing a `VaultFile` with
`VaultFileSourceKind.APP_EXPORT`, checking per-file and total Vault limits,
storing bytes through `VaultStorageProtocol`, rolling back stored bytes on
failure, and then linking the export job to `vault_file_id`. Its download path
at `src/skriptoteket/application/curated_apps/classroom_planner/handlers/seating_export_job_completion.py:209`
requires both job ownership and Vault-file ownership before reading bytes.
The response model at
`src/skriptoteket/web/api/v1/apps_classroom_planner_export_job_contracts.py:94`
returns a product job DTO with `download_url` and `vault_artifact`, which is a
better precedent for the authenticated Exam Converter lane than the generic
run-artifact Vault command.

## Changes Made

| # | Files | Change |
|---|-------|--------|
| 1 | `docs/backlog/prs/pr-0324-st-21-03-exam-converter-authenticated-end-to-end-proof.md` | Marked the proof slice `blocked` and recorded the stop-condition reason. |
| 2 | `docs/backlog/prs/pr-0325-st-21-03-exam-converter-authenticated-runtime-ui-and-save-remediation.md` | Created the narrow remediation PR that must land before rerunning `PR-0324`, including the Klassrumskartan app-export/Vault finalizer precedent. |
| 3 | `docs/backlog/stories/story-21-03-exam-converter-public-and-authenticated-artifact-lanes.md` | Synced the authenticated lane plan to `PR-0324` blocked and `PR-0325` ready. |
| 4 | `docs/backlog/epics/epic-21-curated-app-conversion-hub.md` | Synced implementation summary with the authenticated proof blocker and remediation slice. |
| 5 | `docs/index.md` and `.codex/handoff.md` | Added the retained review/remediation pointers and next-step state. |
