---
type: pr
id: PR-0416
title: "ST-28-04 Make Hemma cleanup units idle-safe"
status: ready
owners: "agents"
created: 2026-07-29
updated: 2026-07-29
stories:
  - "ST-28-04"
tags:
  - hemma
  - systemd
  - cleanup
  - operations
acceptance_criteria:
  - "Given skriptoteket-web is intentionally absent or stopped, when either installed cleanup service runs, then systemd records success and the journal records an explicit skipped/idle outcome."
  - "Given skriptoteket-web is running, when either cleanup service runs, then the existing cleanup command executes unchanged and its true exit status remains authoritative."
  - "Given Docker access or the cleanup command fails while the app is running, when the unit exits, then systemd records failure and the original diagnostic remains visible."
  - "Given the live unit pair is installed, when repository state is reviewed, then both unit sources and one bounded install/update command are tracked and stale login-events guidance is not presented as current host truth."
---

## Problem

The live `skriptoteket-session-files-cleanup` and
`skriptoteket-sandbox-snapshots-cleanup` services call `docker exec` directly.
Both fail with status 1 while `skriptoteket-web` is intentionally absent and
succeed once it is running. The repository contains cleanup CLIs and stale unit
examples, but no source or installer for the actual live unit pair.

This is the Skriptoteket-owned leaf of Skill Repository
`ST-SKILL-05-01`. It does not own hostwide ordering or HuleEdu startup.

## Decision And Assumption Ledger

| ID | Question | Plausible options | Decision and motivation | Closure authority |
| --- | --- | --- | --- | --- |
| P416-01 | Which units are current? | The installed session-files/sandbox-snapshots pairs; also revive login-events; replace all cleanup scheduling. | Own only the two installed service/timer pairs. This matches live truth and avoids unrelated scheduling work. | Live Hemma inventory and journal discovery, 2026-07-29. |
| P416-02 | When may cleanup skip successfully? | Any `docker exec` failure; only proven absent/stopped; never skip. | Skip only after a successful Docker state query proves the exact `skriptoteket-web` container is absent or proves its `.State.Running` value is `false`. A Docker daemon, socket, permission, parsing, or inspect failure remains non-zero. | Shared `intentionally_idle`/no-masking contract, OQ-005, and user approval. |
| P416-03 | How are real failures treated? | Convert failures to idle; retry indefinitely; preserve the command result. | When the container is running, `exec` the mapped existing CLI unchanged so Docker, permission, database, import, and CLI failures remain non-zero with their original diagnostic. | OQ-005 and current product CLI ownership. |
| P416-04 | How are host files delivered? | Hand-edit live units; create a general deployment framework; track one exact bounded file set and installer. | Track the exact wrapper, four unit files, installer, and focused contract test named below. The installer updates only those destinations. This is the smallest owner-local leaf and does not establish a systemd framework. | Approved TASK-SKILL-05-01-01 owner-local decomposition; retained discovery `0001-skriptoteket-idle-cleanup`; user-approved anti-overengineering boundary. |
| P416-05 | Which parent owns the follow-up? | Reopen PR-0280; create a new epic/story; use the existing post-closeout follow-up exception. | Keep this leaf under ST-28-04 through PR-0280's explicit future-evidence exception. The live unit failures are the qualifying new evidence. | `PR-0280` closeout and `ST-28-04` follow-up authority; approved owner-local decomposition. |
| P416-06 | What integration anchor must remain unchanged? | Prove only the cleanup units; duplicate hostwide orchestration here; rerun the HuleEdu walking skeleton unchanged. | Depend on approved and delivered HuleEdu TASK-0149, then rerun `pdm run run-local-pdm hemma-start-hostwide` from the HuleEdu repository without Skriptoteket-owned orchestration changes. | ST-SKILL-05-01 walking-skeleton rule and approved TASK-SKILL-05-01-01. |

## Goal

Make both cleanup domains truthful in three states: actual cleanup success,
intentional idle success, and visible real failure.

## Non-goals

- Starting or recreating Skriptoteket.
- Changing Docker restart policy or HuleEdu hostwide orchestration.
- Reviving the uninstalled login-events cleanup unit.
- Masking every `docker exec` failure as idle.
- Creating a generic timer/unit installation framework.

## Owned surfaces

- `scripts/hemma_cleanup_if_running.sh` → installed as
  `/usr/local/libexec/skriptoteket-cleanup-if-running`.
- `systemd/skriptoteket-session-files-cleanup.service` and
  `systemd/skriptoteket-session-files-cleanup.timer` →
  `/etc/systemd/system/` with the same basenames.
- `systemd/skriptoteket-sandbox-snapshots-cleanup.service` and
  `systemd/skriptoteket-sandbox-snapshots-cleanup.timer` →
  `/etc/systemd/system/` with the same basenames.
- `scripts/install_hemma_cleanup_units.sh` → invoked from the repository root as
  `sudo bash scripts/install_hemma_cleanup_units.sh`.
- `tests/unit/scripts/test_hemma_cleanup_units.py` owns wrapper argv/state,
  unit-source, destination, and installer-scope assertions.

## Implementation plan

1. Add one small host-facing wrapper. First run a bounded Docker container-list
   query for the exact name. A successful empty result is absent; a successful
   exact match is inspected for `.State.Running`; `false` is stopped. Any
   unsuccessful or ambiguous query exits non-zero.
2. Return explicit skipped success only for absent/stopped state; otherwise
   `exec` the selected existing cleanup command.
3. Check in the two current service/timer pairs and the named bounded installer.
   Before copying, the installer captures the five destination files that
   exist. It copies only those five files, runs `systemctl daemon-reload`, and
   leaves current timer enablement unchanged.
4. Align the cleanup reference/runbook to the actual unit pair and explicit
   three-state outcome.
5. Add focused tests for both cleanup domains and unit/install contracts.

## Test plan

- Red/green wrapper proof for running, absent/stopped, and running-but-failed
  states for both cleanup domains.
- Unit contract proof for exact container, command, working directory, and
  timer schedule.
- Bounded Hemma proof:
  - running app: both services `Result=success` with cleanup completion;
  - intentionally absent app: both services `Result=success` with explicit
    skipped message;
  - controlled running-app failure: while `skriptoteket-web` is running, launch
    a transient `systemd-run --wait --collect` service with the installed
    wrapper and an invalid cleanup selector. The wrapper must first prove the
    app is running, then exit non-zero with the selector diagnostic. This does
    not invoke either destructive cleanup CLI or alter application data.
- After HuleEdu TASK-0149 is delivered, rerun its unchanged integration anchor:
  `pdm run run-local-pdm hemma-start-hostwide`. Retain the terminal
  Skriptoteket tier result and the later-tier transition; do not modify the
  coordinator in this PR.
- `pdm run lint`
- `pdm run typecheck`
- `pdm run pytest tests/unit/scripts/test_hemma_cleanup_units.py -q`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Rollback plan

For every destination that existed, reinstall its captured bytes; remove only
a newly installed destination that had no pre-install file; then run
`systemctl daemon-reload`. Restore the pre-install enabled/disabled and
active/inactive timer states exactly. Do not change application containers,
data, or restart policy during rollback.

## Stop conditions

- The live unit bytes differ from the captured pre-implementation baseline.
- The skip branch cannot distinguish absent/stopped from Docker or command
  failure.
- Installation would overwrite unrelated systemd units or require a general
  privileged framework.
- Either cleanup domain lacks running, idle, and real-failure proof.
- HuleEdu TASK-0149 is not approved and delivered, or its unchanged hostwide
  invocation no longer reaches the accepted Skriptoteket boundary.

## Plan Document Review

- Recorded: `2026-07-29T18:24:45+0200` (`CEST`).
- Reviewer: `plan-document-reviewer`
  `/root/review_skriptoteket_pr0416`.
- Decision: `changes_requested`.
- `readiness_review`: `approved`.
- Reviewed scope: this plan, retained discovery
  `0001-skriptoteket-idle-cleanup`, `EPIC-28`, `ST-28-04`, `PR-0280`,
  Skill Repository `EPIC-SKILL-05` CAP-05-A, ready `ST-SKILL-05-01`,
  approved `TASK-SKILL-05-01-01`, the local PR template/docs contract,
  `.codex/rules/080-home-server-deployment.md`, and the current cleanup
  reference/runbook.
- Governing authority: closed Skill Repository OQ-005/OQ-006, the approved
  owner-local decomposition, and the `PR-0280` future-evidence exception for a
  separate product-owned systemd repair. The live 2026-07-29 unit/journal
  evidence satisfies that exception and supports `ST-28-04` parent fit.
- Findings:
  1. **High** — The test plan does not retain the unchanged HuleEdu hostwide
     walking skeleton as this later product leaf's integration anchor, and the
     plan names no execution dependency on the HuleEdu first executable leaf.
     `ST-SKILL-05-01` explicitly requires both. Add the dependency and exact
     integration-anchor invocation/result; a pending dependency may gate
     execution after readiness, but implementation must not bypass the
     accepted leaf order.
  2. **High** — Lines 59-62 and 71-79 state the desired outcomes without
     closing the safety-critical classification and proof method. Define how a
     successful state query distinguishes exact absent/stopped states from
     Docker daemon, permission, or inspection failures, and name the bounded
     controlled-failure procedure that proves the installed service preserves
     a running-app failure without risking application data or unrelated host
     state. This is required by P416-02/P416-03 and the no-failure-masking
     acceptance criteria.
  3. **Medium** — P416-04 and lines 59-67 do not name the repository-relative
     wrapper, four unit sources, installer, test owners, installer invocation,
     source-to-host destinations, or rollback treatment for newly installed
     files. The validation list also leaves `focused tests` as a placeholder
     rather than an exact command. Record these bounded surfaces and commands
     so implementation cannot invent ownership or widen into a systemd
     framework.
  4. **Medium** — The decision ledger is not in the required task-ledger
     matrix: it omits highly plausible options and motivation, and P416-04 and
     P416-05 do not cite the accepted authority that closes their normative
     choices. Preserve the current decisions, add the missing fields, and cite
     the approved smallest-owner-local decomposition plus the exact
     `PR-0280`/`ST-28-04` future-evidence exception.
- Permitted next step: repair only these derived plan gaps and return the
  changed plan to the same reviewer.
- Status transition: none. Parent implementation of `PR-0416` is not yet
  permitted.
- Residual risk: no Hemma mutation, unit installation, service start, container
  stop, or implementation proof was performed. `pdm run docs-validate` and
  `git diff --check` passed after this review edit.

### Approved Re-review

- Recorded: `2026-07-29T18:41:46+0200` (`CEST`).
- Reviewer: same fixed `plan-document-reviewer`
  `/root/review_skriptoteket_pr0416`.
- Decision: `approved`.
- Changed scope: this repaired plan only, against the four findings above.
- Findings: none.
- Resolution:
  1. Delivered HuleEdu `TASK-0149` is the explicit dependency, and the plan
     retains its unchanged
     `pdm run run-local-pdm hemma-start-hostwide` invocation and terminal
     Skriptoteket/later-tier evidence as the integration anchor.
  2. Only successful exact-name Docker queries can classify absence or stopped
     state. Daemon, socket, permission, parsing, ambiguity, and inspection
     failures remain non-zero. The running-app failure proof uses a transient
     collected systemd unit with the installed wrapper and an invalid selector;
     it invokes neither cleanup CLI and mutates no application data.
  3. The wrapper, four unit sources, installer, focused test, five host
     destinations, install/test invocations, pre-install capture, enablement
     preservation, and exact rollback treatment are bounded and named.
  4. Every ledger row now records plausible options, the selected outcome and
     motivation, and the authority that closes the decision. Parent fit derives
     from the exact `PR-0280` future-evidence exception and the accepted
     owner-local decomposition.
- Permitted next step: the parent may implement `PR-0416` directly. Apply
  `ready -> in_progress` only when implementation starts; this review does not
  change lifecycle status.
- Residual risk: implementation review, installed-unit proof, rollback
  execution, and unchanged real-Hemma hostwide integration evidence remain
  required. `pdm run docs-validate` and `git diff --check` passed after this
  re-review edit.
