---
type: adr
id: ADR-0087
title: "Exam Converter durable correction sessions with stateless apply"
status: accepted
owners: "agents"
deciders: ["user-lead"]
created: 2026-05-18
updated: 2026-05-19
links:
  - "ADR-0066"
  - "ADR-0086"
  - "EPIC-21"
  - "ST-21-03"
  - "ST-21-04"
  - "PR-0332"
  - "PR-0333"
  - "PR-0334"
  - "PR-0335"
  - "PR-0336"
  - "PR-0337"
  - "Sir Convert Task 333"
  - "Sir Convert Task 332"
  - "HuleEdu TASK-0567"
---

## Context

This ADR was reviewed and approved by `REV-ST-21-04` on 2026-05-18, then
accepted by the user-lead on 2026-05-19.

`ADR-0086` defines teacher-owned Exam Converter corrections as source-bound
overlays applied by Sir Convert into effective renderer input. Sir Convert Task
333 and HuleEdu TASK-0567 now expose a unified non-matching correction apply
edge for point, choice, gap/open-cloze, and item-text corrections. That edge is
stateless: it validates a submitted correction request and returns derived
effective state and artifact readiness for that transaction, but it does not
persist a teacher correction session.

Authenticated teachers need a stable workflow where corrections survive item
navigation, reloads, and later export/projection work. That cannot be claimed
from browser-local state and cannot be claimed from a stateless Sir Convert
apply response. It also must not be smuggled into `PR-0332`, whose proper scope
is consuming the unified non-matching route and keeping matching blocked until
Sir Convert Task 332.

The missing product decision is therefore where durable teacher-correction truth
lives when Sir Convert remains a stateless correction applicator.

## Proposed Decision

Skriptoteket will own authenticated Exam Converter correction sessions as a
durable product aggregate. Sir Convert remains a stateless deterministic
applicator. The HuleEdu Gateway remains the protected transport edge for
Skriptoteket-to-Sir Convert calls.

The durable truth boundary is:

- Skriptoteket persists teacher correction intents for an authenticated teacher,
  local Conversion Hub job, source binding, and source-state fingerprint.
- Sir Convert persists no correction-session truth for this workflow. Its
  returned effective state, hashes, target readiness, and artifacts are derived
  evidence from the submitted full correction set.
- The browser owns drafts and focus only. It does not own persisted correction
  truth and must not display local draft state as applied truth.
- Source IR remains immutable parser output. Persisted correction intents are
  overlays against source-bound item identities.
- `manual_matching_answer_key` remains blocked until Sir Convert Task 332
  provides matching-capable producer state and a later approved implementation
  slice enables it.

The correction-session aggregate must persist only source-bound intents whose
current producer contract can be replayed through the unified apply route:

| Correction entry kind | Durable ownership | Notes |
|---|---|---|
| `point_correction` | Persisted in this aggregate | One active point correction per source-bound item. |
| `manual_choice_answer_key` | Persisted in this aggregate | One active answer-key correction per source-bound choice interaction. |
| `manual_gap_open_cloze_answer_key` | Persisted in this aggregate | One active answer-key correction per source-bound gap/open-cloze interaction. |
| `item_text_patch` | Persisted in this aggregate | One active visible-text value per source-bound text field target. |
| `review_decision` | Persisted in this aggregate | Accepted-current-state export decisions are durable submitted semantics and must not be recreated from local UI state. |
| `candidate_suppression` | Persisted in this aggregate | Teacher rejection of an advisory candidate is durable suppression semantics and must survive reload. |
| `manual_matching_answer_key` | Blocked | Not persisted or replayed until Sir Convert Task 332 and a later accepted slice enable matching-capable producer state. |
| Later correction kinds | Blocked until approved | Any new kind needs accepted upstream producer semantics and a governed implementation slice. |

Each persisted intent must carry enough binding material to prove it belongs to
the current source state before replay. Skriptoteket must persist the exact
producer-issued request-level `source_binding` fields, not a renamed local
fingerprint:

- local Conversion Hub job id and owning user id;
- `source_authoring_schema_version`;
- optional `source_bundle_id`;
- optional `source_file_sha256`;
- `source_state_sha256`;
- `source_state_signature`;
- item id, sequence, item type, and source item fingerprint;
- correction kind and correction payload; and
- session version or equivalent optimistic-concurrency token.

## Aggregate Invariants

The durable correction-session aggregate is a current-set aggregate. It may keep
history for audit, but only active intents are submitted to Sir Convert during
projection or export.

- The active set has at most one active intent per correction target.
- A correction target is derived from the producer binding plus kind-specific
  item-local identity:
  - `point_correction`: item id, sequence, item type, and source item
    fingerprint;
  - `manual_choice_answer_key`: item binding plus choice interaction id;
  - `manual_gap_open_cloze_answer_key`: item binding plus gap/open-cloze
    interaction id;
  - `item_text_patch`: item binding plus text field and optional choice id or
    gap id for each patch operation;
  - `review_decision`: item binding plus accepted target family; and
  - `candidate_suppression`: item binding plus advisory candidate lineage
    identity and candidate payload digest.
- Submitting a new correction for an existing target replaces the prior active
  intent for that target and increments the session version.
- Reverting a correction deletes or deactivates the active intent for that
  target and increments the session version. Deleted or superseded intents are
  never replayed.
- The aggregate must reject duplicate active targets inside one submitted batch
  before persistence.
- Answer-key corrections and accepted-current-state `review_decision` entries
  are mutually exclusive for the same item and target family. Replacing one with
  the other must be an explicit update that supersedes the prior active intent.
- `candidate_suppression` suppresses only the identified advisory candidate. It
  does not create an answer key, does not create export readiness, and does not
  suppress future distinct candidates unless their lineage identity matches.
- Replay order is deterministic: sort active intents by sequence, item id,
  correction-kind order, interaction or field target, and entry id. The
  correction-kind order is `candidate_suppression`, `review_decision`,
  `item_text_patch`, `point_correction`, `manual_choice_answer_key`,
  `manual_gap_open_cloze_answer_key`; `manual_matching_answer_key` is absent
  until a later approved slice.
- All write APIs must require the caller's expected session version. A stale
  version fails with `409 Conflict` and returns enough current session metadata
  for the client to reload before retrying.
- Source-state mismatch, missing source binding, mismatched item fingerprint,
  or unsupported correction kind is a hard rejection before replay or export.

Projection and export must be replay-based:

1. Skriptoteket loads the owned local job and persisted correction session.
2. Skriptoteket issues fresh producer source state through the HuleEdu Gateway.
3. Skriptoteket rejects stale or mismatched persisted intents before apply.
4. Skriptoteket submits the complete supported correction set to Sir Convert's
   unified apply route.
5. Skriptoteket returns or renders only the replayed effective state,
   target-readiness evidence, and artifact manifest produced by Sir Convert for
   that full set.

No layer may claim a correction is persisted in Sir Convert unless Sir Convert
later accepts and implements a separate durable correction-session contract.
Until then, the correct claim is: persisted in Skriptoteket, applied by Sir
Convert, and displayed from replayed effective state.

## Consequences

- `PR-0332` must not be treated as the durable-session implementation. It may
  consume unified non-matching apply behavior, but persistent teacher workflow
  stability belongs to the follow-on story governed by this ADR.
- `ST-21-04` is unblocked by this accepted ADR. Its implementation tasks are
  `PR-0333` through `PR-0337` and must stay ordered so persistence precedes API
  exposure, replay orchestration, frontend readback, and browser/artifact proof.
- Skriptoteket needs backend application/API/persistence work for correction
  sessions: domain/application models, repository protocol, SQLAlchemy model,
  migration, handlers, OpenAPI/types, and owner-scoped tests.
- The frontend must submit teacher commits to Skriptoteket correction-session
  APIs, then reload/read back persisted correction truth and replayed Sir
  Convert effective state. Component-local selection state is draft-only.
- Replay cost and failure states become explicit product behavior. If Sir
  Convert or Gateway apply is unavailable, Skriptoteket can still show the
  persisted correction intents as saved, but it must label projection/artifact
  freshness as unavailable rather than showing a derived effective state.
- Stale source-state mismatches are hard failures for replay/export. The product
  may offer teacher remediation, but must not silently drop or reinterpret a
  persisted intent.
- Tests and live proof must demonstrate reload/readback from Skriptoteket
  persisted intent state plus Sir Convert replay, not from browser memory.
- Backend proof must cover aggregate uniqueness, replacement, deletion/revert,
  deterministic replay ordering, incompatible active-intent rejection, and
  session-version `409 Conflict` behavior.
- Repository and migration proof must cover owner-scoped correction-session
  persistence and active-target constraints.
- API proof must cover authenticated owner scoping, stale-source rejection,
  unsupported-kind rejection, and optimistic-concurrency conflicts.
