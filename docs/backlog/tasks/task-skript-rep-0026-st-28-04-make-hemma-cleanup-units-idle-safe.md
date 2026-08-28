---
type: task
id: TASK-SKRIPT-REP-0026
title: ST-28-04 Make Hemma cleanup units idle-safe
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-07-31'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: spec-verifier
  decided_at: '2026-08-28T12:06:12+02:00'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: .orchestration/context/sessions/01a04769-58d6-74a7-901f-7665a1d7ea44/evidence/reviews/TASK-SKRIPT-REP-0026/terminal-spec-verification.md verifies published main 32cb6af37a7252c842aeb0ff097c68cde77da336
task_kind: repository
acceptance_criteria:
  - Given skriptoteket-web is intentionally absent or stopped, when either installed cleanup service runs, then systemd records success and the journal records an explicit skipped/idle outcome.
  - Given skriptoteket-web is running, when either cleanup service runs, then the existing cleanup command executes unchanged and its true exit status remains authoritative.
  - Given Docker access or the cleanup command fails while the app is running, when the unit exits, then systemd records failure and the original diagnostic remains visible.
  - Given the live unit pair is installed, when repository state is reviewed, then both unit sources and one bounded install/update command are tracked and stale login-events guidance is not presented as current host truth.
backlog_document_profile: contract-derived
---

## Implementation Contract

Make the two installed Hemma cleanup domains truthful in three states: completed
cleanup, intentional idle success, and visible real failure. Add one
host-facing wrapper that queries Docker for the exact \`skriptoteket-web\`
container before invoking an existing cleanup command. A successful empty query
means absent. A successful exact match is inspected for \`.State.Running\`; only
\`false\` means stopped. Docker daemon, socket, permission, parsing, ambiguity,
and inspection failures remain non-zero.

When the exact container is running, the wrapper executes the selected existing
cleanup command unchanged so its Docker, permission, database, import, and CLI
exit status and diagnostic remain authoritative. The wrapper accepts only the
two owned cleanup selectors and reports an invalid selector without invoking a
cleanup CLI.

Track only these owned surfaces:

- \`scripts/hemma_cleanup_if_running.sh\`, installed as
  \`/usr/local/libexec/skriptoteket-cleanup-if-running\`;
- the \`skriptoteket-session-files-cleanup\` and
  \`skriptoteket-sandbox-snapshots-cleanup\` service/timer pairs under \`systemd/\`,
  installed with the same basenames under \`/etc/systemd/system/\`;
- \`scripts/install_hemma_cleanup_units.sh\`, invoked from the repository root as
  \`sudo bash scripts/install_hemma_cleanup_units.sh\`; and
- \`tests/unit/scripts/test_hemma_cleanup_units.py\` for wrapper state/argv,
  unit-source, destination, and installer-scope contracts.

The installer captures the five existing destination files before copying,
updates only those destinations, runs \`systemctl daemon-reload\`, and preserves
the current enabled/disabled and active/inactive timer states. This task does
not own or change \`TASK-SKRIPT-REP-0032\`.

## Contract Inputs

- Live Hemma inventory and journal evidence from 2026-07-29 showing that both
  installed services fail with direct \`docker exec\` while \`skriptoteket-web\`
  is intentionally absent and succeed once it runs.
- Closed Skill Repository OQ-005/OQ-006 and the approved
  \`TASK-SKILL-05-01-01\` smallest-owner-local decomposition.
- The \`PR-0280\` future-evidence exception and \`ST-28-04\` follow-up authority.
- Delivered HuleEdu \`TASK-0149\`, whose unchanged
  \`pdm run run-local-pdm hemma-start-hostwide\` invocation remains the
  cross-product integration anchor.
- The approved same-reviewer plan re-review recorded on
  2026-07-29 at 18:41 CEST, which closed the dependency, state-classification,
  controlled-failure, exact-surface, rollback, and ledger findings.
- The retained planning artifact for this task in session
  \`01a04769-58d6-74a7-901f-7665a1d7ea44\`; planning alternatives and review
  history stay there while this document carries accepted contract terms.

## Core Vertical And Performance

The core vertical is one systemd service invocation: the wrapper proves the
exact container state, returns explicit success without cleanup only for proven
absent or stopped state, or replaces itself with the selected current cleanup
CLI when the app is running. The two services share this wrapper and retain
their existing hourly schedules.

The wrapper performs only bounded exact-name Docker queries and one state
inspection before the existing cleanup command. No polling, retry loop,
container start, restart-policy change, hostwide coordinator, login-events
revival, general installer framework, or second scheduling abstraction is
added.

## Validation

- Red/green focused proof for both cleanup domains in running, absent, stopped,
  state-query failure, and running-command-failure states.
- Unit-source proof for the exact container, command, working directory,
  schedule, destinations, and bounded installer scope.
- On Hemma, prove both services complete successfully while the app runs and
  succeed with an explicit skipped journal message while it is intentionally
  absent.
- While \`skriptoteket-web\` runs, launch a collected transient systemd unit with
  the installed wrapper and an invalid selector. It must exit non-zero with the
  selector diagnostic without invoking either destructive cleanup CLI or
  altering application data.
- From HuleEdu after delivered \`TASK-0149\`, rerun
  \`pdm run run-local-pdm hemma-start-hostwide\` unchanged and retain the terminal
  Skriptoteket tier result and later-tier transition.
- \`pdm run lint\`
- \`pdm run typecheck\`
- \`pdm run pytest tests/unit/scripts/test_hemma_cleanup_units.py -q\`
- \`pdm run docs-validate\`
- \`pdm run handoff-validate\`
- \`git diff --check\`

## Stop Conditions

- Live unit bytes differ from the captured pre-implementation baseline.
- The wrapper cannot distinguish proven absent/stopped state from Docker or
  cleanup-command failure.
- Installation would overwrite unrelated systemd units or require a general
  privileged framework.
- Either cleanup domain lacks running, idle, and real-failure proof.
- Delivered HuleEdu \`TASK-0149\` or its unchanged hostwide invocation no longer
  reaches the accepted Skriptoteket boundary.
- Rollback cannot restore every pre-existing destination byte, remove only a
  newly installed destination, reload systemd, and restore timer enablement and
  activity exactly.

## Decided Contract Terms

| ID      | Decided contract term                                                                                                                                                                          |
| ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| P416-01 | Own only the installed session-files and sandbox-snapshots service/timer pairs; do not revive login-events or replace cleanup scheduling.                                                      |
| P416-02 | Return idle success only after a successful exact-name query proves absence or \`.State.Running\` is \`false\`; every Docker access, parsing, ambiguity, or inspection failure stays non-zero. |
| P416-03 | When the container runs, execute the mapped current cleanup CLI unchanged and preserve its true result and diagnostic.                                                                         |
| P416-04 | Track exactly one wrapper, four unit files, one bounded installer, and one focused test; create no generic systemd framework.                                                                  |
| P416-05 | Keep this owner-local leaf under \`ST-28-04\` through the \`PR-0280\` future-evidence exception.                                                                                               |
| P416-06 | Depend on delivered HuleEdu \`TASK-0149\` and retain its unchanged \`hemma-start-hostwide\` integration anchor without changing cross-product orchestration.                                   |
