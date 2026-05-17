---
type: adr
id: ADR-0086
title: "Exam Converter teacher-owned correction overlay boundary"
status: accepted
owners: "agents"
deciders: ["user-lead"]
created: 2026-05-17
updated: 2026-05-18
links:
  - "ADR-0066"
  - "ADR-0085"
  - "EPIC-21"
  - "ST-21-03"
  - "PR-0332"
  - "REV-PR-0332"
  - "REF-exam-converter-ui-content-model-v1"
  - "Sir Convert Task 322"
---

## Context

Authenticated Exam Converter now has two distinct review contracts:

- accepted-current-state export, which submits a reviewed export decision for
  the current conversion state without adding answer keys; and
- reviewed AI-facit apply, which submits teacher-accepted advisory suggestions
  as `reviewed_completion_answer_key` overlay entries.

Neither contract is sufficient for the full teacher correction workflow. A
teacher must eventually be able to correct stems/prompts, points, choice keys,
matching keys, and gapped/open-cloze accepted values before creating PDF/QTI
artifacts. That workflow must not be represented as browser-local state, parser
metadata mutation, or a hidden fallback after AI suggestions are rejected.

## Proposed Decision

Teacher-owned Exam Converter corrections should be a source-bound overlay
workflow applied by Sir Convert into effective renderer input and reported back
through effective IR/artifact evidence. Skriptoteket owns the teacher-facing
editor and submits the overlay; Sir Convert owns validation, effective IR
application, target readiness, and PDF/QTI rendering.

The correction boundary is:

- source IR remains immutable parser output;
- browser-local edits never unlock downloads by themselves;
- artifact readiness comes only from the returned Sir Convert bundle;
- teacher edits that start from an AI suggestion use reviewed-completion
  lineage with `review_outcome=teacher_edited` when the upstream contract
  supports that item shape;
- teacher-authored corrections that do not start from an AI suggestion require
  explicit Sir Convert overlay fields such as item patches or manual answer
  keys, not reused advisory metadata;
- rejection and global rejection of suggestions must become explicit submitted
  review semantics before they can affect artifact generation; and
- choice, matching, and gapped/open-cloze keys are first-class supported shapes
  when the source-neutral contract contains the required structure and values.

Every correction overlay must be source-bound. The binding invariant is:

- top-level source file SHA-256;
- source IR schema version;
- source IR SHA-256;
- per-item item id;
- per-item sequence;
- per-item item type; and
- per-item source item fingerprint.

Stale, missing, duplicated, or mismatched binding must fail before any renderer
or target adapter runs. A failed binding is not a teacher-facing degraded export
state.

The correction capability decision is:

| Overlay field | Supported correction meaning | Blocked | Upstream-required |
|---|---|---|---|
| `effective_item_patch` | Visible item-content repair in effective renderer input only, such as prompt/body, choice option text, and source-bound gap visible fields where the upstream DTO validates the exact shape. | New source ids, raw/base64 assets, arbitrary external resources, scoring policy, answer-key provenance, parser provenance, or unbounded context. | Any visible-content correction shape whose source ids, item type, or target adapter validation are not yet represented by the upstream overlay contract. |
| `manual_answer_key` | Teacher-authored answer keys with no AI lineage, including choice keys and gapped/open-cloze accepted values when source gap ids and accepted-value fields are present. | Free-text/manual-marking items as automatically keyed answers, parser/source provenance mutation, or keys that cannot bind to current item-local ids. | Matching keys or other key shapes not exposed by the active upstream route for the current source adapter. |
| `reviewed_completion_answer_key` | Teacher-reviewed AI-facit output, including `accepted_unchanged` and `teacher_edited` outcomes with bounded candidate lineage, when the payload validates against the current item-local structure. | Raw prompts, raw provider output, cross-job trust without submitted lineage, or treating LLM lineage as parser/source provenance. | Reviewed-completion payload kinds not yet accepted by the upstream reviewed-completion contract for the current source adapter. |
| `review_decision` | Accepted-current-state export decisions that explicitly allow a target to render without adding an answer key when the target has a governed unkeyed/manual profile. | Treating rejection as an answer key, treating rejection as export readiness, or using review decisions to hide validation/unsupported-shape failures. | Any rejection/global-rejection artifact effect beyond candidate suppression until the upstream contract defines a submitted review-decision result for it. |
| Points/scoring correction | Supported only through the small Sir Convert producer-owned task immediately before `PR-0332`, which must add a dedicated source-bound points/scoring correction DTO before Skriptoteket exposes point editing. | Browser-local point edits, point changes through `effective_item_patch`, answer-key overlays, or review decisions, and any artifact that implies point changes were persisted before the returned Sir Convert bundle proves the correction. | Any point/scoring UI or full teacher-correction workflow step in Skriptoteket before Sir Convert Task 322 has landed, regenerated the consumer contract, and proved effective IR plus PDF/QTI behavior. |

Rejected AI suggestions are candidate suppression only. Rejection means the
teacher has declined that advisory candidate; it does not create an answer key,
does not approve manual-unkeyed export, does not block a target by itself, and
does not enable PDF/QTI generation. If the teacher wants to export without a
machine-marked key, that is a separate accepted-current-state `review_decision`.
If a future product flow needs rejected-candidate audit or global rejection to
affect generated artifacts, it must be a submitted source-bound review decision
with explicit upstream semantics before files are created.

Artifact proof is part of the decision boundary. A corrected job is not proven
by UI state or overlay submission alone. Proof must include:

- returned effective IR showing the applied correction and source binding;
- target readiness generated after overlay application and target validation;
- PDF inspection showing corrected visible content and/or answer-key values;
- QTI package inspection showing corrected choice, matching, and
  gapped/open-cloze semantics where those shapes are supported; and
- negative inspection proving teacher-facing artifacts do not contain internal
  diagnostics, raw overlay JSON, raw provider prompts/responses, student-result
  data, scores, credentials, or identity markers.

## Consequences

- The teacher editor is a contract-backed correction workflow, not a local UI
  convenience layer.
- The product may show proposed or draft corrections, but final files remain
  governed by returned effective IR, target readiness, and generated artifact
  evidence.
- Missing producer support for a correction shape is a contract gap, not a
  reason for Skriptoteket to invent a local export workaround.
- Points/scoring correction is a producer-owned prerequisite to `PR-0332`, not
  a local Skriptoteket implementation detail. `PR-0332` may consume the
  returned Sir Convert contract only after the small producer task has landed.
- Until this decision is accepted and implemented, the Exam Converter question
  detail surface must not offer local-only edit controls that imply persisted
  correction or export readiness.
