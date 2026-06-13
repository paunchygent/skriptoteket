---
type: story
id: ST-21-08
title: "Transcript speaker overlays and replay formatter exports"
status: blocked
owners: "agents"
created: 2026-06-13
updated: 2026-06-13
epic: "EPIC-21"
dependencies:
  - "ST-21-06"
  - "ST-21-07"
  - "Sir Convert Story 54"
  - "Sir Convert Story 56"
  - "HuleEdu ST-01-09"
acceptance_criteria:
  - "Given a transcript job is running, when Sir Convert reports progress through Gateway, then Skriptoteket renders truthful status, heartbeat, processed seconds, total seconds, chunk progress, retry state, and cancel/abort outcome without spinner-only waiting states."
  - "Given a saved canonical transcript contains diarized speaker labels, when the teacher names speakers, then Skriptoteket persists a typed owner-scoped overlay from canonical speaker labels to display names without mutating the canonical transcript JSON."
  - "Given the teacher requests TXT, Markdown, VTT, or SRT for a saved transcript, when overlay-aware export runs, then Skriptoteket submits saved canonical JSON plus the speaker overlay through HuleEdu Gateway to Sir Convert `transcript_json -> transcript_bundle` replay and uses only returned artifact references."
  - "Given export artifacts are available, when the teacher downloads or saves to Mina filer, then actions use producer-returned overlay-aware artifact references and never browser-local formatting, source-audio reprocessing, loose string parsing, or catch-all typing."
  - "Given transcript content and speaker names may be sensitive, when jobs, overlays, replay requests, downloads, saves, logs, or metrics are handled, then transcript text, utterances, source content, speaker display names, media hashes as labels, and provider/model details are excluded from logs and labels."
ui_impact: "Yes (teachers get truthful progress, speaker naming, export actions, and Mina filer save actions for saved transcripts)."
data_impact: "Yes (new owner-scoped speaker overlay state and replay/export provenance over saved transcript records)."
---

# ST-21-08: Transcript Speaker Overlays And Replay Formatter Exports

## Context

`ST-21-07` / `PR-0343` makes canonical `transcript_json` durable in
Skriptoteket. Sir Convert Story 54 and Task 358 are now accepted, so
product-neutral TXT, Markdown, WebVTT, and SRT formatter artifacts exist for
canonical transcript JSON. The remaining parity gap is product-owned: teachers
need truthful progress, clear cancel feedback, speaker naming, and
download/save actions that respect the same producer-authority model used by
Exam Converter correction replay.

This story settles the post-`PR-0343` product direction. Skriptoteket owns
teacher intent and durable product state. Sir Convert owns deterministic
formatter artifacts. HuleEdu owns the browser-session Gateway edge. No repo
owns a compatibility shim, browser formatter fallback, source-audio replay, or
catch-all typed contract.

## Settled Cross-Repo Contract

- Sir Convert adds a Service API v2 replay conversion route:
  `source.format = transcript_json` and
  `conversion.output_format = transcript_bundle`.
- The replay request accepts saved canonical `transcript_json_v1`, a closed
  requested artifact enum of `txt`, `md`, `vtt`, and `srt`, and a typed
  `speaker_label_overrides` array.
- A speaker override maps one canonical label from the JSON, for example
  `speaker_00`, to one validated display name. Unknown labels, duplicate
  labels, empty names, duplicate names, control characters, and partial or
  malformed transcript JSON are rejected.
- Overrides affect formatter display labels only. Canonical `transcript_json`
  is never rewritten, repaired, or reissued as the overlay truth.
- HuleEdu exposes the route through the existing
  `/sir-convert/v2/convert/jobs*` Gateway edge without response rewriting.
- Skriptoteket downloads and saves only Sir Convert returned artifact
  references for `transcript_txt`, `transcript_md`, `transcript_vtt`, and
  `transcript_srt`.

## Scope

- Consume full Sir Convert/HuleEdu progress snapshots in the transcript lane.
- Persist saved-transcript speaker display-name overlays as Skriptoteket-owned
  intent.
- Request producer formatter replay from saved canonical JSON plus overlay
  intent.
- Add download and Mina filer save actions from producer-returned overlay-aware
  artifact references.
- Add retained live proof that progress, cancel feedback, overlay naming,
  download, and Mina filer save behave through the authenticated product path.

## Non-Goals

- No local STT, diarization, alignment, transcript repair, or source-audio
  reprocessing.
- No browser-local TXT/Markdown/VTT/SRT formatting.
- No mutation of canonical `transcript_json` to store speaker names.
- No public/no-login transcript export lane.
- No fallback to canonical `speaker_00` labels when an overlay-aware export was
  requested and Sir Convert rejects or omits the overlay artifact.

## Implementation Slices

- `PR-0344` is done: transcript lifecycle observability and cancel/abort
  feedback.
- `PR-0345` is done: formatter authority sync and typed artifact selection.
- `PR-0346` is done: saved transcript speaker overlay persistence and edit
  affordances.
- `PR-0347` is done: overlay-aware formatter replay client through HuleEdu
  Gateway.
- `PR-0348` is done: overlay-aware download and Mina filer save actions.
- `PR-0349` is blocked on live Sir Convert internal-identity trust: the
  sanctioned local HuleEdu Gateway signer is rejected by the tunnel lane with
  `auth_invalid_internal_identity` / `invalid_internal_identity_signature`
  before a transcript job can be created.

## Live Proof Status

`PR-0349` retained sanitized evidence under
`.artifacts/playwright-pr-0349-transcript-parity-live/20260613T134340Z/`.
The browser-session ceremony and local transcript lane are reachable, all
HuleEdu shared PostgreSQL targets and the Skriptoteket dev DB are migrated to
head, and Gateway reaches the canonical Sir Convert tunnel backend. The summary
now records `blocker_kind=sir_convert_internal_identity_rejected` with
`auth_invalid_internal_identity` /
`invalid_internal_identity_signature`. The end-to-end parity acceptance criteria
remain unproven because live Sir Convert rejects the local Gateway-signed
submit before progress, cancel, save, overlay, replay, download, or Mina filer
save actions can run.

The story must stay open/blocked until HuleEdu/Sir Convert reconcile the
signer/trusted-public-key lane for local authenticated proof or provide a
sanctioned Hemma/prod browser proof lane for the same product path.

## Linked Artifacts

- Sir Convert formatter authority:
  `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/backlog/stories/story-54-transcript-formatter-strategies-over-canonical-json.md`
- Sir Convert replay authority:
  `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/backlog/stories/story-56-transcript-speaker-overlay-formatter-replay-over-canonical-json.md`
- HuleEdu Gateway companion:
  `/Users/olofs_mba/Documents/Repos/huleedu/docs/backlog/stories/story-01-09-expose-transcript-formatter-replay-through-sir-convert-auth-edge.md`
- Exam Converter replay precedent:
  `docs/adr/adr-0087-exam-converter-durable-correction-sessions-with-stateless-apply.md`
