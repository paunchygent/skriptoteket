---
type: task
id: TASK-SKRIPT-39-04-24
title: The exam import count rises while the questions convert
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-22'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - During a Word or PDF import, a count explicitly labeled as AI output received rises before the whole batch is published
  - The batch cap stays at 16 and final results continue through the ordinary conversion and admission path
  - Received-output progress does not advance the saved-result count or make pending questions editable
  - Streaming retains existing door-owned usage and overage policy, including missing-charge handling
story: ST-SKRIPT-39-04
backlog_document_profile: contract-derived
---

## Implementation Contract

During a Word or PDF exam import, report the distinct questions for which complete AI
output has been received while the existing conversion batch is still running. Label
this as received output, separately from saved results and editable questions (D2).

- Keep the existing cap at 16 question families (D1). Observe the existing structured
  conversion response. Current producer inputs are the starting point, not frozen
  requirements; ordinary producer/protocol adaptation remains an implementation choice.
- Frame complete elements of the response's `items` array and project their declared
  question-owned anchors onto the existing question identities. Mark receipt for every
  question addressed, including review/type-conflict output and an item addressing more
  than one question. Repeated observation leaves receipt set. This is observation, not
  an additional content, ownership, ambiguity or correctness gate (D3).
- Return the final response through ordinary conversion/admission. Receiving output
  neither unlocks a placeholder nor changes the saved-result count or job terminal state.
  Keep normal liveness while work continues, including when all output has arrived.
- Store receipt independently in existing job progress and expose its count through
  status. Reuse the existing UoW serialization and worker/lease fence; preserve receipt
  through first and subsequent batch saves. Saved revisions and editor units retain
  their meaning. Start with current polling and use real visibility evidence to guide
  any needed delivery adjustment.
- Product wording must describe received output. Draft Swedish: "AI-svar mottagna för
  N av M frågor"; English meaning: "AI output received for N of M questions". Settle
  the exact wording through normal frontend ownership. Neither count promises correctness.

Non-goals: smaller batches, incremental admission/saving inside a response, or a new
AI validation or accounting policy. Receipt need not equal the total at terminal success:
a source-review fallback can be saved without any converter output for that question.

## Contract Inputs

- ST-SKRIPT-39-04 and TASK-SKRIPT-39-04-23: existing Word/PDF import, phase reporting
  and live signal. TASK-SKRIPT-39-05-13 D6 selects 16 families.
- User decisions, 2026-10-22: preserve 16; "Show AI output received ... count observed
  question output; keep saved/editable status separate." Planning closure uses
  `agent-planning:user-closure-gate`; source discovery is in retained
  `01a1647c-736c-7c8c-827d-c8b616ccb074`, `evidence/planning/in-batch-progress-investigation.md`.
  The acceptance and implementation authority record is
  `evidence/planning/astra-plan-accepted-and-implementation-authorized.md`;
  it supersedes earlier parent plan restrictions, including those in
  `evidence/planning/accepted-progress-contract.md`.
- Astra Lead Architect advisory `evidence/architecture/astra-truthful-progress-user-intent.md`
  in that retained root; the user selected "Use Astra's lean replacement" on 2026-10-22.
  This accepts the replacement plan; the advisory has no reviewer-owned readiness verdict.
- Planning baseline seams: `answer_key_structured_provider.py` buffers with `stream: false`;
  `DocxBuildRoundExchange` awaits the whole response; `admit_batch` checks all entries;
  `DocxConversionProgressProtocol.batch_ready` publishes admitted results;
  `examWorkspaceConversionStatusPoll.ts` displays the saved count as `klara`.
- Shared transport baseline: `LlmDoorClientProtocol.stream` exists; the door settles
  usage but did not expose its settled per-call charge to Skriptoteket. Extend that
  transport under TASK-HULE-14-03-07. The first streamed exam path replaces the old
  non-streaming premise by consuming its door-owned charge event, preserving TASK-SKRIPT-41-01-03
  C7/C8: apply existing charges/cap; missing charges count no overage and are logged;
  do not add fail-closed receipt requirements or local price estimates. Capped production
  use needs normal stream charges connected; local work can proceed in parallel.

## Core Vertical And Performance

Core vertical: import a representative Word exam exercising the existing 16-family batch;
observe question-output receipts before the response completes, then ordinary saved and
editable results. Walk the PDF entry route through the same behavior. Existing liveness
covers waits before question output arrives.

Bounded implementation units:

1. Structured observation: stream text through the provider/exchange, frame complete
   item output, report question identities and return the ordinary final response,
   status and usage. Adapt recording/test providers at the same seam.
2. Job/status projection: persist independent receipt state through existing fencing
   and first/subsequent saves; expose the count and generated API types. This can
   proceed against the receipt port while unit 1 is built.
3. Workspace display: received-output wording and count, with existing liveness,
   revision following and locks. Integrate units 1–2 for focused Word/PDF proof.
4. Shared transport: the HuleEdu owner exposes settled stream charges; Skriptoteket's
   door client consumes them and applies existing policy. Work can proceed alongside
   units 1–3; connect it before general capped use. Do not stop consuming the stream at
   a provider terminal event if the door settlement follows it.

This observes the existing call; no extra request for progress is needed. There is no
batch comparison, performance target or mandatory token/timing report. Diagnose buffering
if real progress is hidden; no performance or correctness improvement is assumed (D4).

## Validation

- A fragmented structured stream reports complete item output before the terminal
  result and preserves final content/status/usage. Cover nested/escaped JSON and an
  unfinished tail; use existing terminal/transport failure semantics. Do not repeat
  producer content validation in the observer.
- A small receipt test covers review/type-conflict output, repeat observations and an
  item addressing multiple questions without an admission gate.
- Progress integration covers interleaved receipt/batch writes, first-save preservation
  and the existing stale-owner fence. Receipt changes neither revision nor editor units.
- Focused frontend checks cover received output before a saved revision, continued
  running at all-output-received and unchanged edit locking; reuse existing revision tests.
- Door checks show settled charges reach the caller once, the existing cap applies,
  terminal/settlement ordering works and missing-charge behavior is unchanged.
- Walk Word and PDF imports in the real workspace: visible intermediate receipts, then
  ordinary saved/editable results. Synthetic fragments prove parsing, not live visibility.
  The user assigned this walk to the MacBook parent on 2026-10-22; code publication
  hands over that proof and does not establish visible-progress acceptance.

## Implementation Evidence

2026-10-22: Pi implemented structured-stream observation, complete-item framing,
independent fenced receipt persistence, required status/API types and the workspace
count. Focused provider, converter, PostgreSQL and frontend tests pass; combined
lint/typecheck and frontend build pass. Reports and captures are in retained root
`01a1647c-736c-7c8c-827d-c8b616ccb074`, `evidence/implementation/`.
TASK-HULE-14-03-07 supplies settled stream charges; its affected check passes
1,275 tests after isolating two existing test fixtures from changing defaults.

Opus 5.5 reviewed the code; its original `changes_requested` verdict is retained at
`evidence/reviews/task-skript-39-04-24-code-review.md`. Both medium findings were
repaired by fresh Pi units: receipt labels and progress fields say received, the
premature editability hint is removed, and per-part admission is extracted from the
pipeline (448 lines; helper 110). Repair proof passes: 49 focused frontend tests,
101 backend tests, scoped lint/typechecks and frontend build. An existing door-limit
fixture now emits the requested SSE format and settled charge; its four failing
cases pass without changing policy or assertions. Parent admits these medium repairs
without rereview under the review's permitted next step and
`agent-overseer:approved-review-closeout`.

The prose review's D1 and authority clarifications were repaired and validated;
its original verdict is at `evidence/reviews/progress-contract-prose.md`.
The task stays in progress for the MacBook parent's Word/PDF walk; no terminal task
transition, live visibility or production deployment is claimed.

## Stop Conditions

Escalate a concrete conflict with the user's cap/meaning decisions, saved/editable
semantics or shared-service authority. Do not silently bypass existing spending policy
or claim visible-progress acceptance if actual delivery still produces only a final jump.
Ordinary parser/protocol/schema adaptation is not itself a stop condition.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                    |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | Keep the existing cap of 16 question families (user, 2026-10-22).                                                                                                                                                                        |
| D2  | The rising count means AI output received for distinct questions; saved/editable status remains separate (user, 2026-10-22).                                                                                                             |
| D3  | Adopt Astra's observation plan without new consumer admission rules or blanket freezes; keep saved/editable semantics separate and retain C7/C8 spending policy through a narrow shared transport extension (user adoption, 2026-10-22). |
| D4  | Use focused stream, receipt, persistence, display and door checks plus real Word/PDF proof; add no benchmark, mandatory timing/token report or new correctness gate (Astra plan adopted by user, 2026-10-22).                            |
