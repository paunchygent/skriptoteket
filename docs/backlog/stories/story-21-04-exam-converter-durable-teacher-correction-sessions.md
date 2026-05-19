---
type: story
id: ST-21-04
title: "Exam Converter durable teacher correction sessions"
status: ready
owners: "agents"
created: 2026-05-18
updated: 2026-05-19
epic: "EPIC-21"
dependencies:
  - "ADR-0087"
  - "ADR-0086"
  - "ST-21-03"
  - "PR-0332"
  - "Sir Convert Task 333"
  - "HuleEdu TASK-0567"
acceptance_criteria:
  - "Given ADR-0087 is accepted, when the correction-session aggregate is implemented, then it enforces one active intent per correction target, deterministic replay ordering, explicit replace/delete semantics, incompatible active-intent rejection, and session-version 409 conflicts."
  - "Given ADR-0087 is accepted, when implementation tasks are created for this story, then they split persistence, replay, frontend readback, and proof into PR-sized slices instead of widening PR-0332."
  - "Given an authenticated teacher commits a supported correction, when Skriptoteket accepts it, then the correction is persisted as a source-bound intent owned by that teacher and local Conversion Hub job, not as browser-local state or claimed Sir Convert persistence."
  - "Given a teacher submits accepted-current-state export or advisory-candidate rejection semantics, when Skriptoteket accepts the commit, then `review_decision` and `candidate_suppression` are persisted as durable source-bound intents instead of being recreated from browser-local UI state."
  - "Given persisted correction intents exist for a job, when the teacher navigates away, reloads, or returns to another item, then the UI reads back Skriptoteket persisted intent truth and does not rely on component-local selection state."
  - "Given a projection or export is requested, when Skriptoteket replays corrections, then it submits the complete supported persisted correction set through the HuleEdu Gateway unified Sir Convert apply edge and renders only the returned effective state/readiness evidence."
  - "Given a persisted intent no longer matches producer-issued source state, when replay is attempted, then Skriptoteket fails the replay/export with a stale-source state instead of silently dropping, rewriting, or locally applying the correction."
  - "Given matching correction is requested, when Sir Convert Task 332 is not yet landed and consumed by a later approved slice, then Skriptoteket keeps `manual_matching_answer_key` blocked and does not persist or replay matching intents."
  - "Given AI answer-key candidates exist, when the authenticated teacher reviews facit, then candidates seed the normal editor only and no separate accepted/rejected AI answer-key state is persisted."
  - "Given corrected files are exposed, when the teacher downloads or saves them, then the action is enabled only from replay-provided corrected artifact references, never original job artifacts."
  - "Given the workflow is verified, when browser proof is retained, then it shows multiple committed corrections survive navigation/reload because backend readback and Sir Convert replay drive the visible state."
ui_impact: "Yes (authenticated Exam Converter correction controls must display saved/replayed state distinctly from local drafts and unavailable replay state)."
data_impact: "Yes (new owner-scoped correction-session persistence for authenticated Conversion Hub jobs)."
---

# ST-21-04: Exam Converter Durable Teacher Correction Sessions

## Context

`ST-21-03` delivered the public/authenticated Exam Converter artifact lanes and
the current correction-overlay consumer path. `ADR-0086` establishes that
teacher corrections are source-bound overlays and that Sir Convert owns
effective-state application. Sir Convert Task 333 and HuleEdu TASK-0567 provide
the unified non-matching apply edge, but that edge is stateless.

The product now needs a durable authenticated workflow: teacher-authored point,
choice, gap/open-cloze, item-text, accepted-current-state review, and
candidate-suppression corrections must survive navigation and reload, and
visible projection must come from persisted correction truth plus Sir Convert
replay. This story owns that product capability. It is not owned by `PR-0332`.

## Scope

- Persist authenticated teacher correction intents in Skriptoteket for local
  Conversion Hub jobs.
- Enforce the current-set aggregate invariants defined by `ADR-0087`: one
  active intent per correction target, deterministic replay ordering,
  replace/delete semantics, incompatible active-intent rejection, and
  session-level optimistic concurrency.
- Persist the exact producer-issued `source_binding` fields plus per-item
  binding material before replay.
- Replay the complete persisted supported correction set through the HuleEdu
  Gateway unified Sir Convert apply route.
- Render UI state from Skriptoteket readback and Sir Convert replayed effective
  state, not component-local state.
- Keep matching disabled until Sir Convert Task 332 and a later approved slice.
- Preserve the immutable source IR and source-binding invariants from
  `ADR-0086`.

## Non-Goals

- No Sir Convert durable correction-session persistence.
- No browser-local persistence or local replay ledger as product truth.
- No parser/source IR mutation in Skriptoteket.
- No matching correction persistence before Task 332.
- No implementation outside the ordered `PR-0333` through `PR-0339` plus
  proof-closeout task chain.

## Implementation PR Chain

`ADR-0087` is accepted. Implementation is authorized through these ordered
PR-sized slices:

1. Correction-session backend aggregate and persistence (`PR-0333`, done):
   domain/application models, repository protocol, SQLAlchemy model, migration,
   owner scoping, active-target uniqueness, replace/delete semantics,
   optimistic versioning, and stale-source guards.
2. Correction-session API and generated frontend types (`PR-0334`, done):
   authenticated read/upsert/delete or replace endpoints, `409 Conflict`
   behavior, OpenAPI export, and frontend type regeneration.
3. Replay orchestration (`PR-0335`, done):
   load persisted intents, issue producer source state, validate binding,
   submit the complete supported set to Sir Convert via HuleEdu Gateway, and
   return replayed effective state/readiness.
4. Frontend readback integration (`PR-0336`, done):
   route teacher commits through Skriptoteket correction-session APIs, reload
   saved intents after navigation, and render replayed effective state while
   keeping drafts visually separate.
5. AI prefill editor and replay artifact authority (`PR-0338`, done):
   delete the abandoned reviewed-AI acceptance workflow, make AI candidates
   editor prefill only, preserve answer-key provenance at durable-intent build
   time, advance the UI only after upsert/readback/full replay/projection, and
   gate corrected file actions on replay artifact references rather than
   original job artifacts.
6. Sir Convert replay artifact reference contract (`PR-0339`, done):
   upstream producer/Gateway contract follow-up so correction apply readiness
   exposes replay-scoped corrected artifact references for exportable corrected
   targets. Sir Convert owns this by default; Skriptoteket-owned replay
   artifact storage requires separate product-owner approval.
7. Browser and artifact proof (`PR-0337`, ready after `PR-0339`):
   canonical Playwright proof that multiple committed corrections survive
   navigation/reload, that projection/export state is driven by backend
   readback plus Sir Convert replay, and that corrected file actions use only
   replay-supplied artifact references.

## Notes

- `PR-0332` remains the completed consumer/projection slice for the unified
  non-matching route, while durable teacher workflow stability belongs here.
- `PR-0333` is done. It established the Skriptoteket-owned aggregate,
  owner/job-scoped repository persistence, active-target constraints, exact
  source-binding round-trip, and migration coverage before any API/replay/UI
  surface was added.
- `PR-0334` is done. It exposed the persisted aggregate through authenticated
  owner-scoped read/upsert/revert routes, exported OpenAPI, and regenerated
  frontend API types without adding replay or UI readback behavior.
- `PR-0335` is done. It added non-UI replay orchestration over persisted
  active intents, fresh HuleEdu Gateway source-state issue, source-binding and
  item-fingerprint validation, complete-set unified apply submission, and
  explicit unavailable/stale projection freshness states.
- `PR-0336` is done. It routes supported teacher commits through Skriptoteket
  correction-session APIs, restores saved active intents after navigation or
  reload, renders replayed points/text/keys/review decisions/candidate
  suppression/counters/readiness, keeps drafts distinct from persisted truth,
  keeps matching blocked, and includes a Swedish copy audit so teacher-visible
  messages do not expose internal projection/replay/session terminology.
- `PR-0338` is done. AI candidates now seed only the normal facit editor,
  answer-key provenance is computed during durable-intent construction, UI
  advancement waits for readback/replay/projection, and corrected file actions
  require replay-provided corrected artifact references.
- `PR-0339` is done. Sir Convert owns replay-derived corrected artifact
  references, HuleEdu Gateway passes them through unchanged, and Skriptoteket
  only consumes the replay reference. A Skriptoteket-owned replay artifact
  store is a heavier alternative that needs explicit separate approval.
- Accepted unchanged AI-prefilled facit keeps AI provenance after replay, and
  report warnings are conversion diagnostics rather than remaining teacher
  actions.
- If replay is unavailable, the product may show saved correction intents, but
  it must not show a fresh effective-state projection or unlock artifacts from
  stale derived evidence.
