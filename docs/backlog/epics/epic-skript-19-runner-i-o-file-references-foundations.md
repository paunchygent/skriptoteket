---
type: epic
id: EPIC-SKRIPT-19
title: Runner I/O + file references foundations
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: active
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
outcome: Runner-based tools use a single request envelope and first-class file references
  (run/session/vault) with explicit state semantics and structured errors, enabling
  robust multi-step workflows and future vault reuse without path leakage.
retired_ids:
- EPIC-19
---

## Scope

- Replace env-var JSON payload transport (`SKRIPTOTEKET_INPUTS`, `SKRIPTOTEKET_INPUT_MANIFEST`, `SKRIPTOTEKET_ACTION`)
  with a single `/work/request.json` request envelope for runner-based tools.
- Introduce a first-class `FileRef` concept + resolver used end-to-end (validation, staging into `/work/input/`,
  deterministic manifest mapping).
- Add platform-supported promotion primitives so outputs (run artifacts) can become reusable inputs in:
  - the current session context (“promote to session”) — tools may request these promotions, and
  - the per-user file vault (“save to vault”) — explicit user action only (no tool auto-persistence).
- Upgrade runner output contract to v3 with:
  - explicit `state_update` (no ambiguity between missing/null/empty),
  - structured `error` payload alongside `error_summary`,
  - explicit promotion requests/results (at minimum: tool-requested session promotions + platform-applied outcomes).
- Apply **no-migration-path** policy:
  - runner/app/tool scripts are upgraded together,
  - older payload transport is removed (no shims),
  - script bank + starter templates are updated as part of the same work.

## Epic Contract

### Scope

- Replace env-var JSON payload transport (`SKRIPTOTEKET_INPUTS`, `SKRIPTOTEKET_INPUT_MANIFEST`, `SKRIPTOTEKET_ACTION`)
  with a single `/work/request.json` request envelope for runner-based tools.
- Introduce a first-class `FileRef` concept + resolver used end-to-end (validation, staging into `/work/input/`,
  deterministic manifest mapping).
- Add platform-supported promotion primitives so outputs (run artifacts) can become reusable inputs in:
  - the current session context (“promote to session”) — tools may request these promotions, and
  - the per-user file vault (“save to vault”) — explicit user action only (no tool auto-persistence).
- Upgrade runner output contract to v3 with:
  - explicit `state_update` (no ambiguity between missing/null/empty),
  - structured `error` payload alongside `error_summary`,
  - explicit promotion requests/results (at minimum: tool-requested session promotions + platform-applied outcomes).
- Apply **no-migration-path** policy:
  - runner/app/tool scripts are upgraded together,
  - older payload transport is removed (no shims),
  - script bank + starter templates are updated as part of the same work.

### DX / UX gold standard (invariants)

Tool scripts should be able to follow a single, stable mental model:

- Tools read runtime inputs via `skriptoteket_toolkit` only (not `os.environ`), and rely on the request envelope +
  file manifest for discovery.
- Every input file is staged under `/work/input/` and appears in the manifest; tools never need to know if a file came
  from upload/session/vault.
- Tools never handle platform file paths outside `/work/input/` for inputs. File identity across turns uses `FileRef`
  values (not paths), and the platform resolves/stages refs for the tool.
- FileRef values are stable enough to be stored as defaults in tool settings or action prefill (including vault refs);
  the resolver must treat these defaults the same as user-selected refs.

### Out of scope

- SPA UI rendering work (pickers, “files available” panels, run view polish). This remains in EPIC-14 stories such as
  ST-14-24 and ST-14-36.
- Data model/UX details for datasets/vault beyond the plumbing boundary (handled in EPIC-14 + ADR-0058/0059).

### Stories

- [ST-19-01: Runner request envelope: /work/request.json (replace env payloads)](../stories/story-19-01-runner-request-envelope.md)
- [ST-19-02: FileRef model + resolver + promotion plumbing (session + vault)](../stories/story-19-02-file-refs-resolver-and-promotion.md)
- [ST-19-03: Runner contract v3: structured errors + state_update + promotions](../stories/story-19-03-runner-contract-v3-structured-errors-state-update-and-promotions.md)
- [ST-19-04: Runner request factory seam (V2)](../stories/story-19-04-runner-request-factory-seam.md)
- [ST-19-05: Runner result parser seam (V2)](../stories/story-19-05-runner-result-parser-seam.md)
- [ST-19-06: Runner contract selection seam (V2 default)](../stories/story-19-06-runner-contract-selection-seam.md)

### Implementation Summary (as of 2026-01-22)

- Implemented `/work/request.json` envelope end-to-end and removed env-var JSON payloads (ST-19-01).
- Added FileRef model + resolver + session promotion plumbing (ST-19-02).
- Adopted runner contract v3 parsing/emission with `state_update`, structured errors, and promotions (ST-19-03).
- Added a V2 request factory seam that builds a structured request object + workdir archive (ST-19-04).
- Added a V2 result parser seam that wraps the existing result parsing behavior (ST-19-05).
- Added a DI-managed contract selection seam with V2 default factory/parser wiring (ST-19-06).

### Enables / blocks

- Enables (and should precede):
  - [ST-14-24: UI contract: first-class file references](../stories/story-14-24-ui-contract-file-references.md)
  - [ST-14-36: User file vault: reusable uploads + picker](../stories/story-14-36-user-file-vault-and-picker.md)

### Risks

- Breaking changes across runner/app/tool scripts (mitigate by updating the script bank + templates in the same PR and
  refusing old contract versions).
- Security bugs if file references can resolve across users/tools/contexts (mitigate by strict access checks at
  resolution time + exhaustive tests).
- Increased payload surface area (mitigate by size caps, deterministic normalization, and strict schema validation at
  the runner boundary).

### Dependencies

- ADR-0015 (runner contract boundary)
- ADR-0022 (typed UI contract)
- ADR-0024 (tool sessions, state, actions)
- ADR-0039 (session file persistence)
- ADR-0063 (runner request envelope v1)
- ADR-0064 (file references + resolver + staging manifest)
- ADR-0065 (runner contract v3 + promotion semantics)
- EPIC-14 (UI rendering stories depend on this foundation)

> Note: This epic implies ADR updates (and review) for the contract evolution before implementation.

## ADR Coverage

No separate material is recorded in the source snapshot.

## Contract Inputs

- ADR-0015 (runner contract boundary)
- ADR-0022 (typed UI contract)
- ADR-0024 (tool sessions, state, actions)
- ADR-0039 (session file persistence)
- ADR-0063 (runner request envelope v1)
- ADR-0064 (file references + resolver + staging manifest)
- ADR-0065 (runner contract v3 + promotion semantics)
- EPIC-14 (UI rendering stories depend on this foundation)

> Note: This epic implies ADR updates (and review) for the contract evolution before implementation.

## Stories

- [ST-19-01: Runner request envelope: /work/request.json (replace env payloads)](../stories/story-19-01-runner-request-envelope.md)
- [ST-19-02: FileRef model + resolver + promotion plumbing (session + vault)](../stories/story-19-02-file-refs-resolver-and-promotion.md)
- [ST-19-03: Runner contract v3: structured errors + state_update + promotions](../stories/story-19-03-runner-contract-v3-structured-errors-state-update-and-promotions.md)
- [ST-19-04: Runner request factory seam (V2)](../stories/story-19-04-runner-request-factory-seam.md)
- [ST-19-05: Runner result parser seam (V2)](../stories/story-19-05-runner-result-parser-seam.md)
- [ST-19-06: Runner contract selection seam (V2 default)](../stories/story-19-06-runner-contract-selection-seam.md)

## Epic Verification Plan

No separate material is recorded in the source snapshot.

## Exceptions And Follow-Ups

- SPA UI rendering work (pickers, “files available” panels, run view polish). This remains in EPIC-14 stories such as
  ST-14-24 and ST-14-36.
- Data model/UX details for datasets/vault beyond the plumbing boundary (handled in EPIC-14 + ADR-0058/0059).

## Risks

- Breaking changes across runner/app/tool scripts (mitigate by updating the script bank + templates in the same PR and
  refusing old contract versions).
- Security bugs if file references can resolve across users/tools/contexts (mitigate by strict access checks at
  resolution time + exhaustive tests).
- Increased payload surface area (mitigate by size caps, deterministic normalization, and strict schema validation at
  the runner boundary).

## Notes

### Scope

- Replace env-var JSON payload transport (`SKRIPTOTEKET_INPUTS`, `SKRIPTOTEKET_INPUT_MANIFEST`, `SKRIPTOTEKET_ACTION`)
  with a single `/work/request.json` request envelope for runner-based tools.
- Introduce a first-class `FileRef` concept + resolver used end-to-end (validation, staging into `/work/input/`,
  deterministic manifest mapping).
- Add platform-supported promotion primitives so outputs (run artifacts) can become reusable inputs in:
  - the current session context (“promote to session”) — tools may request these promotions, and
  - the per-user file vault (“save to vault”) — explicit user action only (no tool auto-persistence).
- Upgrade runner output contract to v3 with:
  - explicit `state_update` (no ambiguity between missing/null/empty),
  - structured `error` payload alongside `error_summary`,
  - explicit promotion requests/results (at minimum: tool-requested session promotions + platform-applied outcomes).
- Apply **no-migration-path** policy:
  - runner/app/tool scripts are upgraded together,
  - older payload transport is removed (no shims),
  - script bank + starter templates are updated as part of the same work.

### DX / UX gold standard (invariants)

Tool scripts should be able to follow a single, stable mental model:

- Tools read runtime inputs via `skriptoteket_toolkit` only (not `os.environ`), and rely on the request envelope +
  file manifest for discovery.
- Every input file is staged under `/work/input/` and appears in the manifest; tools never need to know if a file came
  from upload/session/vault.
- Tools never handle platform file paths outside `/work/input/` for inputs. File identity across turns uses `FileRef`
  values (not paths), and the platform resolves/stages refs for the tool.
- FileRef values are stable enough to be stored as defaults in tool settings or action prefill (including vault refs);
  the resolver must treat these defaults the same as user-selected refs.

### Out of scope

- SPA UI rendering work (pickers, “files available” panels, run view polish). This remains in EPIC-14 stories such as
  ST-14-24 and ST-14-36.
- Data model/UX details for datasets/vault beyond the plumbing boundary (handled in EPIC-14 + ADR-0058/0059).

### Stories

- [ST-19-01: Runner request envelope: /work/request.json (replace env payloads)](../stories/story-19-01-runner-request-envelope.md)
- [ST-19-02: FileRef model + resolver + promotion plumbing (session + vault)](../stories/story-19-02-file-refs-resolver-and-promotion.md)
- [ST-19-03: Runner contract v3: structured errors + state_update + promotions](../stories/story-19-03-runner-contract-v3-structured-errors-state-update-and-promotions.md)
- [ST-19-04: Runner request factory seam (V2)](../stories/story-19-04-runner-request-factory-seam.md)
- [ST-19-05: Runner result parser seam (V2)](../stories/story-19-05-runner-result-parser-seam.md)
- [ST-19-06: Runner contract selection seam (V2 default)](../stories/story-19-06-runner-contract-selection-seam.md)

### Implementation Summary (as of 2026-01-22)

- Implemented `/work/request.json` envelope end-to-end and removed env-var JSON payloads (ST-19-01).
- Added FileRef model + resolver + session promotion plumbing (ST-19-02).
- Adopted runner contract v3 parsing/emission with `state_update`, structured errors, and promotions (ST-19-03).
- Added a V2 request factory seam that builds a structured request object + workdir archive (ST-19-04).
- Added a V2 result parser seam that wraps the existing result parsing behavior (ST-19-05).
- Added a DI-managed contract selection seam with V2 default factory/parser wiring (ST-19-06).

### Enables / blocks

- Enables (and should precede):
  - [ST-14-24: UI contract: first-class file references](../stories/story-14-24-ui-contract-file-references.md)
  - [ST-14-36: User file vault: reusable uploads + picker](../stories/story-14-36-user-file-vault-and-picker.md)

### Risks

- Breaking changes across runner/app/tool scripts (mitigate by updating the script bank + templates in the same PR and
  refusing old contract versions).
- Security bugs if file references can resolve across users/tools/contexts (mitigate by strict access checks at
  resolution time + exhaustive tests).
- Increased payload surface area (mitigate by size caps, deterministic normalization, and strict schema validation at
  the runner boundary).

### Dependencies

- ADR-0015 (runner contract boundary)
- ADR-0022 (typed UI contract)
- ADR-0024 (tool sessions, state, actions)
- ADR-0039 (session file persistence)
- ADR-0063 (runner request envelope v1)
- ADR-0064 (file references + resolver + staging manifest)
- ADR-0065 (runner contract v3 + promotion semantics)
- EPIC-14 (UI rendering stories depend on this foundation)

> Note: This epic implies ADR updates (and review) for the contract evolution before implementation.

## Decision And Assumption Ledger

The source snapshot is the governing record for the decisions and assumptions stated above.

## Plan Document Review

No separate material is recorded in the source snapshot.

## Epic Closeout Review

No separate material is recorded in the source snapshot.
