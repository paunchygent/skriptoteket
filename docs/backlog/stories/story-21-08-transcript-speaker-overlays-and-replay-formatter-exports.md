---
type: story
id: ST-21-08
title: "Transcript speaker overlays and replay formatter exports"
status: done
owners: "agents"
created: 2026-06-13
updated: 2026-06-18
epic: "EPIC-21"
dependencies:
  - "ST-21-06"
  - "ST-21-07"
  - "Sir Convert Story 54"
  - "Sir Convert Story 56"
  - "HuleEdu ST-01-09"
  - "REF-current-product-lanes-and-sir-convert-boundary-v1"
acceptance_criteria:
  - "Given a transcript job is running, when Sir Convert reports progress through Gateway, then Skriptoteket renders truthful phase/status, retry state, and cancel/abort outcome without spinner-only waiting states or unstable raw counters presented as reliable progress."
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

- Consume Sir Convert/HuleEdu progress snapshots in the transcript lane and
  render only stable teacher-facing phase/status from them.
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
- `PR-0349` is done: retained live proof now covers upload/cancel progress,
  durable transcript save, speaker overlays, product export, downloads, and
  Mina filer save.
- `PR-0350` is done: the browser-owned replay saga is removed, and the
  DXE/converter pattern is restored so the browser records intent and observes
  product state while Skriptoteket and the producer contracts own orchestration
  and artifact authority.
- `PR-0351` is done: transcript completion/progress/export UX now follows the
  approved mockup contract, autosaves completed transcripts, removes the generic
  manual save gate and old per-artifact export rows, and keeps selected-format
  actions stable as `Ladda ner` and `Mina filer`.
- `PR-0354` is done: follow-up remediation for manual UI findings where
  selected export-format chips rendered as hover/fill without readable selected
  labels, post-upload progress exposed unstable counters, stale formatter
  idempotency jobs could block exports, speaker-name edits needed autosave
  instead of a separate unclear save affordance, and the transcript route did
  not own the mockup's desktop/tablet/small breakpoint contract cleanly.
- `PR-0355` is done: follow-up rail remediation keeps `Avbryt` as a
  reserved, invisible idle slot directly above `Starta transkribering`, removes
  the checkbox-like square icon, updates the empty upload copy to teacher-intent
  language, has retained local remote-proof E2E evidence, and was deployed at
  commit `fe56307c`.

## Live Proof Status

Historical proof
`.artifacts/playwright-pr-0349-transcript-parity-live/20260613T153843Z/`
captured the earlier local trust-lane `401 auth_invalid_internal_identity`
failure and remains useful RCA evidence only.

Latest retained proof
`.artifacts/playwright-pr-0349-transcript-parity-live/20260613T181847Z/`
shows the sanctioned Hemma browser-session path now reaches upload, truthful
running progress, cancel, durable transcript save, and saved-transcript
readback. The blocker moved into Skriptoteket client state: `GET
/speaker-overlays` returned `overlay_count=0`, the subsequent `PUT
/speaker-overlays` also persisted `overlay_count=0`, no
`/formatter-replay/prepare` or `/formatter-replay/complete` requests occurred,
and the UI falsely rendered `Talarnamn sparade.` / `Exportfiler kan skapas.`
while the replay button stayed disabled.

The later production/manual finding is architectural: replay/export can still
become a foreground browser-owned workflow. A manual production export for
transcript `aaf12956-67c3-4cd6-8094-b2e264ad2b59` spent about 119 seconds
between `formatter-replay/prepare` and `formatter-replay/complete` because the
browser was coordinating Sir Convert submit, polling, artifact fetch, and
completion. That violates the DXE/converter boundary requested for this story.

Final retained proof
`.artifacts/playwright-pr-0349-transcript-parity-live/20260614T030725Z/proof-summary.json`
passed after `PR-0350` and production URL fix `14f4b3af...` were deployed. It
shows:

- HuleEdu browser-session ceremony reached the protected transcript lane.
- Upload cancel feedback and running progress rendered.
- Canonical `transcript_json_v1` was saved durably with 27 segments and two
  speaker labels.
- Two speaker display-name overlays were saved.
- Product-owned formatter export succeeded with `transcript_txt`,
  `transcript_md`, `transcript_vtt`, and `transcript_srt`.
- All four downloaded artifacts contained overlay labels and excluded fallback
  labels.
- A representative TXT artifact was saved to Mina filer.

This closes `ST-21-08`. Future transcript work should build on the
product-owned export state boundary rather than restoring browser replay
orchestration.

`PR-0360` / `ST-37-02` adds
[REF-current-product-lanes-and-sir-convert-boundary-v1](../../reference/ref-current-product-lanes-and-sir-convert-boundary-v1.md)
as the durable product-lane boundary reference. For the transcript lane, Sir
Convert owns STT, diarization, formatter replay, and returned artifacts;
Skriptoteket owns saved transcript state, speaker overlays, teacher-facing
export intent, sharing/file actions, and app presentation.

`PR-0351` added the final transcript workspace UX hardening after this retained
production proof. Its local live proof attempt reached the HuleEdu
browser-session route and captured cancel/progress surfaces, then failed before
completion because the local Sir Convert trust lane rejected the product
backend with `auth_invalid_internal_identity` /
`invalid_internal_identity_signature` on
`POST /sir-convert/v2/convert/jobs?wait_seconds=0`. PR-0351-specific behavior
is therefore retained through focused red-first frontend/backend tests,
legacy-surface grep, and approved `REV-PR-0351` review rather than a new
completion-path live artifact.

`PR-0354` then closed the manual remediation findings with fresh local proof.
Retained E2E artifact
`.artifacts/playwright-pr-0349-transcript-parity-live/20260614T210105Z/proof-summary.json`
passed through HuleEdu browser-session auth, transcript creation, product-owned
formatter export, TXT/Markdown/WebVTT/SRT downloads, overlay-label assertions,
autosaved speaker overlays, and Mina filer save. Retained in-app browser
artifacts under `.artifacts/pr-0354-transcript-ui-remediation/20260614T2104Z/`
prove the completed fixture at 1440px stacks the inspector below the
transcript, at 1800px uses side-by-side transcript plus inspector, keeps
selected MD readable, renders no speaker save button, and shows the compact
saved-name status.

`PR-0355` has focused DOM/type proof plus retained local remote-proof E2E:
`pdm run fe-test -- --run src/views/apps/conversion-hub-transcript/TranscriptWorkflowRailShell.spec.ts`,
`pdm run fe-test -- --run src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts`,
`pdm run fe-type-check`, and `pdm run docs-validate` passed. The required local
dev E2E passed at
`.artifacts/playwright-pr-0349-transcript-parity-live/20260615T141002Z/proof-summary.json`,
showing cancel feedback, transcript autosave, saved speaker overlays, all four
formatter downloads, and Mina filer save. Deploy/native Hemma production proof
passed at commit `fe56307c` with deploy log
`/home/paunchygent/apps/skriptoteket/.artifacts/hemma-deploy-20260615-154707.log`.

## Linked Artifacts

- Sir Convert formatter authority:
  `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/backlog/stories/story-54-transcript-formatter-strategies-over-canonical-json.md`
- Sir Convert replay authority:
  `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/backlog/stories/story-56-transcript-speaker-overlay-formatter-replay-over-canonical-json.md`
- HuleEdu Gateway companion:
  `/Users/olofs_mba/Documents/Repos/huleedu/docs/backlog/stories/story-01-09-expose-transcript-formatter-replay-through-sir-convert-auth-edge.md`
- Exam Converter replay precedent:
  `docs/adr/adr-0087-exam-converter-durable-correction-sessions-with-stateless-apply.md`
