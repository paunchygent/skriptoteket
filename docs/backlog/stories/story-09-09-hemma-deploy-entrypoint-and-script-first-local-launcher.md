---
type: story
id: ST-09-09
title: "Hemma deploy entrypoint and script-first local launcher"
status: done
owners: "agents"
created: 2026-04-07
updated: 2026-04-07
epic: "EPIC-09"
dependencies: ["ADR-0081", "ST-09-08"]
acceptance_criteria:
  - "Given an operator launches a Hemma deploy from the local Skriptoteket repo, when `pdm run hemma-deploy` is executed, then it invokes the existing on-host `scripts/hemma_deploy_and_verify_seating_export.sh` from the documented Hemma checkout path instead of re-implementing deploy logic locally."
  - "Given the local launcher opens a remote shell, when the command is constructed, then it uses the repo-approved quoting-safe SSH execution model to start the checked-in on-host deploy as a detached remote process that survives loss of the initiating local or SSH session."
  - "Given the local launcher successfully hands off to the detached remote deploy, when the local command returns, then it prints the remote PID and remote log path so the operator has canonical follow-up breadcrumbs."
  - "Given operators want a readable live follow path after launch, when they use the documented monitor/follow affordance, then it tails the authoritative raw remote log and filters it to existing `==>` milestone lines plus obvious failure patterns without becoming a second source of truth."
  - "Given the launcher cannot hand off cleanly to the detached remote process, when the local command returns, then it exits non-zero and surfaces the start-up failure/log context clearly enough that operators do not need a second improvised launch path."
  - "Given operators follow the deployment docs, when they look up the Hemma deploy flow, then `pdm run hemma-deploy` is the canonical local initiation path while direct on-host script execution remains documented as the fallback/debug path."
---

## Context

Skriptoteket already has a checked-in Hemma deploy/readiness script, but the
local initiation path is still a raw SSH snippet in the runbook rather than a
stable repo command.

That gap creates avoidable operator drift:

- nested quoting mistakes are easy to introduce
- session-bound launches can die with the initiating local or SSH session
- remote PID/log discovery can spill into ad hoc shell work

This story hardens the operator workflow around the existing deploy script. It
does not replace the current on-host deploy logic.

## Notes

- Preserve `scripts/hemma_deploy_and_verify_seating_export.sh` as the single
  deploy/readiness implementation.
- Add the new local launcher through the repo's PDM script table rather than a
  one-off shell recipe in the runbook.
- Follow the Hemma SSH guidance from `AGENTS.md`: prefer heredoc-based remote
  bash execution instead of nested quoted shell fragments.
- The canonical local launcher must use detached remote start as the default
  path and print the remote PID plus remote log path immediately after handoff.
- Keep the raw remote deploy log as the authoritative record. Any optional
  monitor/follow output should be a best-effort filtered tail over that raw log
  using the existing `==>` milestone markers plus obvious failure patterns.
- Update the relevant runbook/docs so the canonical local path and the
  break-glass direct on-host path are both explicit.
- Verification should include a real Hemma launch through `pdm run
  hemma-deploy` and a recorded note in `.agents/handoff.md`.

## Implementation Summary (as of 2026-04-07)

- Added a thin local detached launcher at
  `scripts/hemma_deploy_start.sh` and exposed it as
  `pdm run hemma-deploy`.
- Added a thin filtered monitor at
  `scripts/hemma_deploy_monitor.sh` and exposed it as
  `pdm run hemma-deploy-monitor`.
- Updated `docs/runbooks/runbook-home-server.md` so the canonical local path is
  now the PDM launcher, the raw remote log remains authoritative, and direct
  on-host execution is documented as fallback/debug only.
- Refined the operator wording after the first live run so
  `scripts/hemma_deploy_start.sh` now says the detached handoff succeeded,
  rather than reading like the full deploy already passed.
- Refined the best-effort monitor after the first live run so
  `scripts/hemma_deploy_monitor.sh` now replays existing milestone/failure
  lines from the authoritative raw log before following new output.
- Live Hemma proof is now complete:
  - `pdm run hemma-deploy` handed off a detached remote deploy with PID
    `1243606`
  - the authoritative raw log was written to
    `/home/paunchygent/apps/skriptoteket/.artifacts/hemma-deploy-20260407-092323.log`
  - that raw log shows commit
    `94be5c23bbfb8294278cf21d3f679ee693277f73` deployed, migrations applied,
    and the seating-export smoke passing
  - the deploy script wrote readiness artifacts under
    `.artifacts/pr-0146-seat-export-cutover-20260407-092323/`
