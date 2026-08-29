---
type: task
id: TASK-SKRIPT-39-02-02
title: Prove failover, exhaustion fail-close, and operator lease status for the answer-key lane
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-08-29'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: independent-reviewer
  decided_at: '2026-08-29'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: Independent review approved the integrated failover orchestration at 7b32ed60 as behavior-identical to the reviewed transient gate, second-lease transaction, and exhaustion hard stop; authenticated live proofs on local main 6f4baa7a then showed two Luna request failures followed by two real GLM-5.3-flash completions with four non-refundable lease rows and successful conversion, followed by a token-limit-1 typed exhaustion with zero provider calls, zero new leases, and HTTP-200 admin balance, recorded in handoff.md and retained session 01a04d62-c71c-721c-a43a-76384e182429.
task_kind: story
acceptance_criteria:
  - The answer-key lane fails over once to GLM-5.3-flash on provider error drawing from the same lease, fail-closes with an operator-visible status on lease exhaustion with zero provider calls while deterministic conversion continues, and exposes the day lease balance to operators, proven by focused tests and recorded forced-failover and forced-exhaustion checks
story: ST-SKRIPT-39-02
backlog_document_profile: contract-derived
---

## Implementation Contract

Complete the answer-key lane's failure behavior on the seams left by
TASK-SKRIPT-39-02-01, honoring ST-SKRIPT-39-02 terms S1-S5.

- Failover: on provider error or outage from the Luna profile, one
  failover attempt through the GLM-5.3-flash OpenRouter profile (chat
  completions, Bearer auth), drawing its lease from the same daily
  counter. Exhaustion never routes to the backup; the model identifier is
  verified against current OpenRouter docs at implementation time.
- Exhaustion fail-close: when the daily lease cannot cover a reservation,
  the enrichment job fails closed with a typed, operator-visible status
  carrying the UTC reset time; zero provider calls are made; deterministic
  conversion and every other artifact continue unaffected.
- Operator surface: the current day's lease balance (allocated, spent,
  reset time) is readable by operators through an appropriate existing
  operator-facing surface; no teacher-facing UI.
- No degraded modes, no silent retries beyond the single failover, no
  overflow to any paid route.

## Contract Inputs

- ST-SKRIPT-39-02 slice contract; TASK-SKRIPT-39-02-01 seams
  (provider-selection protocol, lease refusal type); sircon D12-D13
  behavior pins and its forced-failover/forced-exhaustion proof shapes.
- OpenRouter provider docs via the sanctioned docs tooling before code.

## Core Vertical And Performance

Two forced paths through the same worker job: a Luna failure that
completes once via GLM with two leases recorded, and an exhausted day
that refuses before any network call. Both leave the conversion's
deterministic artifacts untouched.

## Validation

- Focused tests: single-failover policy, same-lease accounting across
  both profiles, exhaustion refusal with zero provider calls, operator
  status read.
- Backend gates per `AGENTS.md`; recorded forced-failover and
  forced-exhaustion checks in `handoff.md`.

## Stop Conditions

- The GLM model identifier cannot be verified in current provider docs:
  stop and confirm with the user.
- Any pressure to let exhaustion overflow to a paid route or extra
  retries: stop; exhaustion is a hard stop by decision.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                    |
| --- | ------------------------------------------------------------------------------------------------------------------------ |
| T1  | GLM-5.3-flash via OpenRouter is failover-only, draws from the same lease, and is never reached on exhaustion.            |
| T2  | Exhaustion fail-closes with a typed operator-visible status and zero provider calls; deterministic conversion continues. |
| T3  | Operators can read the day's lease balance; teachers see nothing new.                                                    |

## Closeout Evidence

- Forced failover used an unchanged real `.dxe` (`9eb02293…`) with one MCQ
  and one gap-fill. Both items followed Luna request failure to one GLM
  attempt; four lease rows were retained, the GLM overlay covered both items,
  nine manual-marking follow-ups remained, and conversion plus QTI succeeded.
- Forced exhaustion set the daily limit to `1` and failed before either
  provider call with `daily_token_lease_exhausted`; no lease or overlay row was
  added. The authenticated admin endpoint returned HTTP 200 with allocated,
  charged, available, UTC-day, and reset values.
- Retained evidence is indexed in session
  `01a04d62-c71c-721c-a43a-76384e182429`, captures `0032`-`0038`; the
  consolidated manifest is `proof-39-02-02-consolidated.json` under the
  session live-check scratch seam. Ordinary provider configuration was
  restored and web/worker were healthy without another provider call.
