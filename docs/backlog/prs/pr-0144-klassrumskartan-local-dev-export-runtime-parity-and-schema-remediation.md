---
type: pr
id: PR-0144
title: "Klassrumskartan: local-dev export runtime parity and schema remediation"
status: ready
owners: "agents"
created: 2026-03-25
updated: 2026-03-25
stories:
  - "ST-26-03"
  - "ST-26-04"
  - "ST-26-05"
tags: ["backend", "frontend", "ops", "klassrumskartan", "export", "remediation"]
dependencies:
  - "PR-0122"
  - "PR-0125"
  - "PR-0138"
acceptance_criteria:
  - "Given a developer verifies Klassrumskartan through `http://127.0.0.1:5173/apps/classroom.group-seating-studio`, when they follow the documented local lane, then it is explicit whether the browser is targeting host `dev-local` services or Docker services and the matching logs/runtime expectations are documented in the same place."
  - "Given the host `dev-local` lane is used for export verification, when a seating export job is started, then the host backend reaches a resolvable Sir Convert endpoint instead of failing on `host.docker.internal` DNS lookup."
  - "Given a previously completed local seating export exists, when the teacher retries the download from the host verification lane, then the backend serves the artifact from a host-accessible Vault path instead of returning `500 Internal server error`."
  - "Given the current local code expects the `classroom_planner_plan_drafts.smart_enabled` column, when the host app boots against the local dev database, then `/api/v1/apps/classroom.group-seating-studio/drafts/resumable` no longer fails with schema drift."
  - "Given follow-on export work resumes under `ST-26-03`, `ST-26-04`, or `ST-26-05`, when a developer performs the required live verification, then the remediation doc, handoff, and index point them to one reliable local verification lane instead of leaving runtime parity to tribal knowledge."
---

## Problem

The current export failures seen from `http://127.0.0.1:5173/apps/classroom.group-seating-studio`
are local environment failures, not confirmed regressions in the shipped export product state.

The verified problems are:

- the browser route resolves to the host `pdm run dev-local` stack, while recent debugging
  sometimes looked at Docker logs instead
- host-side export creation fails because the host process cannot resolve the configured
  `host.docker.internal:8085` Sir Convert endpoint
- host-side export download fails because the host backend points at
  `/var/lib/skriptoteket/vault`, but the referenced export bytes only exist in the
  container-mounted Vault path
- the host dev database schema is behind current code and throws
  `UndefinedColumnError: classroom_planner_plan_drafts.smart_enabled` on resumable draft boot

Until this is remediated, EPIC-26 export work risks chasing false failures, validating against the
wrong runtime, or shipping new slices without a trustworthy local proof lane.

## Goal

Restore one trustworthy local verification path for Klassrumskartan export work by making the host
`dev-local` runtime explicit, resolvable, and schema-current, while also documenting how that host
lane differs from the Docker stack.

## Non-goals

- Replanning the user-facing export hierarchy for seating or grouping.
- Replacing the existing production/Hemma export deployment path.
- Introducing compatibility shims for stale local schemas or mixed Vault locations.
- Broad refactors of export presentation models or artifact renderers.

## Implementation plan

1. Document the local verification lanes clearly:
   - record that `http://127.0.0.1:5173` hits the host Vite/uvicorn pair when `pdm run dev-local`
     is running
   - record when Docker logs are relevant and when they are not
   - link the chosen lane from docs and handoff so EPIC-26 verification starts in the right place
2. Restore host export runtime parity:
   - make the host dev backend use a resolvable Sir Convert base URL and callback base URL
   - keep the lane aligned with the canonical `SIR_CONVERT_A_LOT_V2_*` policy from `PR-0138`
3. Restore host-local artifact persistence parity:
   - choose a concrete host-local `VAULT_ROOT` and `ARTIFACTS_ROOT` contract for local export work
   - ensure the host backend never points at container-only export bytes during host-lane download
4. Bring the host dev database to the current code contract:
   - apply or document the required migration path so resumable draft bootstrap matches the checked
     out code
5. Re-run live export verification on the repaired local lane and record the exact commands and
   manual proof in `.agents/handoff.md`

## Test plan

- `pdm run docs-validate`
- `pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit`
- `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/components/PlannerExportActionGroup.spec.ts src/views/apps/components/PlannerSeatingWorkspacePane.export.spec.ts src/views/apps/useSeatingExportFlow.spec.ts`
- local host export proof on `http://127.0.0.1:5173/apps/classroom.group-seating-studio`
- targeted host-backend verification for:
  - export-job creation
  - export-job download
  - resumable draft bootstrap

## Rollback plan

- Restore the prior local dev env/runtime configuration if the remediation introduces a new blocker.
- Remove the remediation-specific docs updates if the chosen lane or local-path contract changes.
- Preserve the already-shipped production/Hemma export configuration while reverting local-only
  changes.
