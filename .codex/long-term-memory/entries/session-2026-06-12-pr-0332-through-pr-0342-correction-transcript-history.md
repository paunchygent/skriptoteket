# Session History: PR-0332 Through PR-0342 Correction And Transcript Lanes

Date: 2026-06-12

## Retained Context

- `ADR-0086`, `PR-0332`, and `REV-PR-0332` established the non-durable unified
  correction consumer/projection boundary for stems/prompts, points, choice keys,
  and gap/open-cloze keys. Matching remains blocked until a real
  matching-capable Sir Convert producer is accepted.
- `ADR-0087` and `ST-21-04` govern durable authenticated teacher correction
  sessions. `PR-0333` through `PR-0336` added owner/job-scoped persistence,
  authenticated read/upsert/revert routes, replay orchestration, and UI restore
  behavior for supported correction intents.
- `PR-0338` and `PR-0339` moved AI-prefill and artifact authority onto replay
  truth: advisory candidates seed the normal facit editor, selection advances
  only after readback/replay/projection, and corrected downloads/saves require
  replay-scoped artifact references.
- `PR-0340` changed report emphasis from raw conversion-warning counts to
  teacher-relevant AI suggestion outcomes and item mapping.
- `PR-0341` separated teacher authoring state from export-owned accepted-current
  state. Durable correction sessions no longer contain `review_decision`,
  `accept_current_state_for_export`, or `conflict_family`.
- `PR-0337` retained live browser/artifact proof at
  `.artifacts/playwright-pr-0337-correction-session-live/20260520T001258Z`.
- `PR-0342` is done with accepted live Gateway proof in
  `docs/backlog/reviews/review-transcript-gateway-live-proof-remediation.md`.
  The proof covers English and Swedish fixtures through Skriptoteket, HuleEdu
  Gateway, Sir Convert, STT/diarization, and canonical `transcript_json`.

## Current Carry-Forward Constraints

- Do not restore the abandoned Task 324 matching route as a bridge, shim, alias,
  wrapper, adapter, or compatibility layer.
- Do not treat current DigiExam adapter restrictions as product limitations:
  the source-neutral IR and QTI/PDF export contract still support matching and
  single-/multi-gap `Lucktext`/open-cloze.
- Transcript follow-up work starts from the live-proven Gateway artifact and
  saved canonical `transcript_json`; no public/no-login, direct Sir Convert,
  local STT, source-audio archive, or formatter-output shortcut is authorized.
