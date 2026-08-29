---
type: task
id: TASK-SKRIPT-39-02-01
title: Stand up the in-process answer-key completion vertical with the Luna profile and Postgres lease
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-08-29'
status: in_progress
closeout_review:
  record: inline
  status: approved
  reviewer: independent-reviewer
  decided_at: '2026-08-29'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: Independent review approved the original vertical and the bounded mixed-exam port repair at 847fae31 with no material findings; the authenticated real-DXE Luna proof then succeeded on that exact reviewed commit (conversion 882f4d81-9eea-44ce-8d63-e1ac65e5af03, enrichment f390fea4-10ae-4009-ab58-e4d3edb613c4, six reconciled Luna lease rows, machine-proposed overlay 9c46587e-853f-4784-b175-3c19bbe2738e, passed QTI package), recorded in handoff.md and retained session 01a04d62-c71c-721c-a43a-76384e182429.
task_kind: story
acceptance_criteria:
  - An overlay-free .dxe converted on the in-process lane produces machine-proposed answer keys through one execution-worker job calling the GPT-5.6 Luna low-effort profile with a Postgres-backed UoW-owned daily token lease reserved before the call, proven by focused tests and one recorded live completion
story: ST-SKRIPT-39-02
backlog_document_profile: contract-derived
---

## Implementation Contract

Build the thin vertical of the answer-key completion lane inside
Skriptoteket, honoring ST-SKRIPT-39-02 terms S1-S5.

- Port the structured-LLM contracts and the Luna answer-key profile from
  sir-convert-a-lot `76983339` into Skriptoteket layering: typed request
  and completion contracts in domain, an httpx OpenAI provider adapter in
  infrastructure behind a protocol seam, the low-reasoning-effort Luna
  profile with the exact model id verified against current OpenAI docs at
  implementation time.
- Lease: one Postgres table (UTC day, tokens reserved) with an Alembic
  migration and a repository behind a protocol; reservation happens in
  the same UoW transaction that records the enrichment attempt; leases
  are never refunded; a typed refusal carries the reset time. No Redis,
  no filesystem counter.
- Worker job: an execution-worker job (existing curated-app job pattern)
  that takes the parsed exam's unkeyed items, requests structured key
  proposals through the profile, and persists them as a machine-proposed
  overlay for the conversion flow; the conversion request never blocks on
  the remote call.
- Readiness parity: source-keyed and overlay-keyed exams behave exactly
  as in ST-SKRIPT-39-01; unkeyed exams gain the proposed-overlay path.
- GLM failover, exhaustion proofs, and the operator status surface belong
  to TASK-SKRIPT-39-02-02; this task must leave clean seams for them
  (provider-selection protocol, lease refusal type) without building them.

## Contract Inputs

- ST-SKRIPT-39-02 slice contract; sircon ADR-SIRCON-0014 and D9-D14.
- Source modules listed in the story; sircon lease tests as the behavior
  pin for no-refund and UTC-reset semantics.
- Skriptoteket execution-worker pattern
  (`skriptoteket.cli run-execution-worker`, existing job handlers),
  migrations workflow (rule 054), config and DI surfaces.
- OpenAI provider docs via the sanctioned docs tooling before code.

## Core Vertical And Performance

One overlay-free `.dxe` submitted on the in-process lane yields a worker
job that reserves the lease, calls Luna once, persists the proposed keys,
and lets the conversion complete with the same readiness semantics as a
teacher overlay. The lease check is a local database write, no extra
network hop; the remote call runs only in the worker.

## Validation

- Focused tests: profile construction, lease reserve/no-refund/UTC-day
  boundaries (clock injected), worker-job lifecycle with a stubbed
  provider, readiness parity, migration idempotency per rule 054.
- Backend gates per `AGENTS.md`: `pdm run lint`, `pdm run typecheck`,
  focused tests.
- One recorded live completion through the Luna profile from the running
  app, recorded in `handoff.md` with the lease row as evidence.

## Stop Conditions

- The Luna model identifier cannot be verified in current provider docs:
  stop and confirm with the user.
- The lease would need cross-repo or shared state to be correct: stop;
  the accepted design is a repo-local sub-allocation.
- Scope pressure toward failover, exhaustion handling, or operator UI:
  stop; TASK-SKRIPT-39-02-02 owns those.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                               |
| --- | ----------------------------------------------------------------------------------------------------------------------------------- |
| T1  | The lease is a Postgres table owned through the UoW, reserved before every provider call, never refunded, partitioned by UTC day.   |
| T2  | Enrichment runs as an execution-worker job; the web request never blocks on the remote call.                                        |
| T3  | The Luna low-effort profile is the only provider path in this task; failover and exhaustion surfaces are seams, not features, here. |
| T4  | Machine-proposed keys persist through the existing overlay semantics with teacher-review and readiness behavior unchanged.          |

## Closeout Evidence

- Reviewed repair commit `847fae31` restored item-scoped enrichment for real
  mixed exams: supported unkeyed items are completed while open-ended items
  retain manual-marking follow-ups.
- The unchanged real `.dxe` (`a274a9d9…`) completed through authenticated
  HuleEdu login and the execution worker using `gpt-5.6-luna` at low effort.
  Six provider calls produced six reconciled lease rows and one
  machine-proposed overlay covering exactly the six eligible MCQs; eleven
  open-ended items remained manual. The conversion and QTI package succeeded.
- Retained evidence is indexed in session
  `01a04d62-c71c-721c-a43a-76384e182429`, captures `0022`-`0028`; the
  consolidated manifest is
  `proof-39-02-01-live-luna-real-847fae31/sanitized-live-evidence.json` under
  the session live-check scratch seam.
