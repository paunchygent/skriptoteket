---
type: task
id: TASK-SKRIPT-REP-0040
title: Retire Sir Convert public-host defaults and align private conversion lanes
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-15'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: ruthless-reviewer
  decided_at: '2026-10-15'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: 'Codex ruthless-reviewer thread 01a13fb4-cc83-7330-abad-921eb7516cf0, rereview of d97caf5b in the Mac retained session 01a13f9f-d6dd-7067-b581-efc395226538, evidence/reviews/TASK-SKRIPT-REP-0040/rereview-d97caf5b.md (copy in Hemma retained session 01a18444-018a-704a-b25f-1868c68bddc4, evidence/rep-0040/): approved, F1 and F2 cleared, no findings remaining. Merged to main as ced7971b. The 2026-10-28 Hemma environment check found no retired-host value in production or staging. Prepared by the Hemma housekeeping lead; the Hemma orchestrator authorizes closure by merging it.'
task_kind: repository
acceptance_criteria:
  - Development and production examples and development Compose use private Sir Convert lanes with no retired-host default or compatibility fallback.
  - The retired hostname cannot establish a preflight remote backend or pass producer validation; seating deployment still rejects its stale environment override.
  - The three current operations documents record retirement and private-lane configuration without changing historical backlog records or claiming live proof.
  - Required local validation is recorded and the candidate is committed on the assigned branch without a push or any Hemma command.
backlog_document_profile: contract-derived
---

## Implementation Contract

Remove `convert.hule.education` runtime defaults after the user's 2026-10-15
retirement confirmation. Docker development uses the canonical private
port-28085 tunnel through `http://host.docker.internal:28085`; explicit host
clients use `http://127.0.0.1:28085`. The production example uses the existing
Compose lane `http://sir_convert_a_lot_prod:8085` on `hule-network`.

Remove the retired hostname from preflight backend allowances, retain the
seating-deployment stale-env rejection with an accurate retirement diagnostic,
and update adversarial rejection and redaction tests. Correct the nginx-proxy
reference, home-server architecture overview and operations runbook part 02.
Historical backlog PR/review/story records remain unchanged. Namecheap DNS
deletion stays with the user. Sir production remains offline by user decision.

## Contract Inputs

- User's implementation assignment and retirement confirmation, 2026-10-15.
  It explicitly delegates private-lane selection, guard treatment and delivery.
- Sir `fix/retire-convert-public-edge` commit `904d0e3f`, accepted
  `ADR-SIRCON-0014`: direct hostname retired; private/Gateway boundaries remain.
- Canonical `sir-convert-a-lot-client` Service v2 private tunnel reference;
  `compose.prod.yaml` web/worker private-service defaults.
- Closed D1-D4 ledger in retained session
  `01a13f9f-d6dd-7067-b581-efc395226538`,
  `evidence/planning/TASK-SKRIPT-REP-0040/plan.md`.

## Core Vertical And Performance

Two bounded execution units: (1) environment/Compose defaults and preflight,
deployment diagnostic and focused tests; (2) the three current operations
documents. The lead integrates both and reconciles the handoff.
Configuration reaches the same existing private converter contract; this task
changes no UI, API route, conversion algorithm or material performance behavior.
A cross-service walking skeleton is outside this maintenance task and cannot
run during the Hemma hold.

## Validation

- `pdm run lint` and `pdm run typecheck`.

- Focused preflight, destination-admission and before-media-copy regression tests:

  ```bash
  pdm run test-sequential \
    tests/unit/scripts/test_sir_convert_trust_lane_preflight.py \
    tests/unit/scripts/test_sir_convert_trust_lane_destinations.py \
    tests/unit/scripts/test_audio_transcription_parity_preflight.py
  ```

- `bash -n scripts/hemma_deploy_and_verify_seating_export.sh` and
  `pdm run shellcheck scripts/hemma_deploy_and_verify_seating_export.sh`.

- Local Compose rendering with synthetic environment values to check web and
  worker defaults; configuration proof does not establish service reachability.

- `pdm run handoff-validate`, `pdm run docs-validate`, and `git diff --check`.

Original candidate `0656bcfe` local execution on 2026-10-15 passed:
22 focused tests (`0002`), full backend
and SPA typecheck (`0004`), shell syntax/ShellCheck (`0005`/`0006`), Compose
rendering (`0012`: 16 endpoint and eight PDF-strategy assertions), lint (`0013`)
and docs validation (`0010`). Complete captures are under the assigned retained
session's `operational-output/commands/01a13f9f-fe59-7ea1-9fcf-c2431433fae6/`.
Initial lint failures were Markdown formatting and two existing overlong
Compose comments; both were repaired. All proof is local/static; no live
service, tunnel, DNS, vhost or certificate verification was performed.

F1/F2 repair on 2026-10-15 replaces raw URL markers and profile-only admission
with parsed scheme/host/port checks. The helper and tests now have separate URL
policy, lane-decision and live-entrypoint files, all below 500 lines. The original
19 test functions and 88 assertions remain. Recorded repair checks passed:
107 focused tests (85 new destination cases), lint, and backend/SPA typecheck.
The three reviewer bypasses now reject in the same network-free probe. Repair
proof is retained in the same session under
`evidence/implementation/TASK-SKRIPT-REP-0040/repair-report.md`; independent
rereview and closeout remain with the parent.

## Stop Conditions

- Run no command on Hemma, including SSH, deployment, restart or conversion proof.
- Do not add a compatibility fallback, push a branch or add attribution lines.
- Preserve concurrent work. Report failed validation and authority gaps to the
  assigning parent; independent review and terminal closeout remain parent-owned.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                      |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| D1  | Use the private tunnel for Docker development and the existing private Docker service for production; no retired-host default or fallback. |
| D2  | Remove the retired preflight allowance; keep the deployment stale-env rejection and update its message; cover rejection and redaction.     |
| D3  | Correct the three current operations documents; preserve historical backlog records and leave DNS deletion to the user.                    |
| D4  | Run assigned local validation, commit on the existing branch, never push or contact Hemma, and return review/closeout to the parent.       |

## Progress

### Closeout 2026-10-28 (Hemma housekeeping lead)

- Merged to main as `ced7971b` (`fix/retire-convert-references` at `d97caf5b`); the
  original reviewer's rereview of `d97caf5b` approved it with no findings remaining.
- Environment check on Hemma, read-only: production web and worker resolve
  `SIR_CONVERT_A_LOT_V2_BASE_URL` to `http://sir_convert_a_lot_prod:8085`; staging
  (`skriptoteket-dev`, checkout `97563a81c`) sets no Sir Convert URL and resolves to
  the settings default `http://127.0.0.1:9010`. No runtime environment or env file on
  Hemma holds `convert.hule.education`. Evidence: Hemma retained session
  `01a18444-018a-704a-b25f-1868c68bddc4`, `evidence/rep-0040/staging-env-check-2026-10-28.md`.
- Later main commits changed `.env.example`, `.env.example.prod` and the two operations
  documents for other tasks; none adds the retired host. The remaining mentions are
  the retirement records and the stale-env rejection guard with its tests.
- Configuration proof only: Sir production stays offline by user decision, so no
  conversion reachability was checked.
- The user deleted the Namecheap CNAME for `convert.hule.education` (reported
  2026-10-28). The name returns NXDOMAIN from 1.1.1.1, 8.8.8.8 and the authoritative
  `dns2.registrar-servers.com`.
