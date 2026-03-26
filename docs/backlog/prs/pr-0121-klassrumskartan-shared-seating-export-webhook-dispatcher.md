---
type: pr
id: PR-0121
title: "Klassrumskartan: shared seating export webhook dispatcher hardening"
status: done
owners: "agents"
created: 2026-03-24
updated: 2026-03-24
stories:
  - "ST-26-01"
tags: ["backend", "klassrumskartan", "export", "webhooks", "hardening"]
acceptance_criteria:
  - "Classroom-planner seating export jobs no longer create one Sir Convert-a-Lot webhook subscription per export job."
  - "A shared seating-export webhook subscription and dispatcher can reconcile conversion completion to the owning local export job by upstream job identity."
  - "The public seating export job API and Vault-backed artifact delivery contract remain unchanged."
  - "Polling fallback remains available so a missed push callback does not strand a completed export job."
---

## Problem

The first shipped seating-export lane works, but it currently creates one Sir
Convert-a-Lot webhook subscription per export job. Under concurrency that can
fan out callback traffic, increase subscription churn, and add avoidable cleanup
and reconciliation overhead.

## Goal

Replace per-job webhook onboarding with a shared seating-export callback
subscription and internal dispatcher while preserving the existing async export
job contract and Vault-backed artifact delivery.

## Current status

- Implemented locally on `main`.
- Seating export jobs now reuse one shared classroom-planner callback
  subscription binding instead of onboarding one webhook subscription per job.
- Callback completion now resolves the owning `SeatingExportJob` by upstream Sir
  Convert job id, while polling fallback remains intact.
- Architecture note (2026-03-26):
  - `ADR-0075` supersedes this webhook architecture for Klassrumskartan-owned
    PDF artifacts
  - the next seating-PDF migration should delete the shared subscription path
    instead of extending it further

## Non-goals

- Changing the teacher-facing seating export job routes or response DTOs.
- Changing the `poster_scene` or HTML/CSS rendering contract.
- Removing the existing polling recovery path.
- Expanding into grouping export, XLSX export, or export-button UX work.

## Implementation plan

- Introduce a shared classroom-planner seating-export webhook subscription seam
  instead of onboarding one Sir Convert-a-Lot webhook per export job.
- Dispatch callback events to the owning `SeatingExportJob` using the stored
  upstream Sir Convert job identifier.
- Keep webhook completion idempotent and continue reusing the existing finalizer
  for Vault persistence and status transitions.
- Preserve polling fallback so a completed upstream job can still be reconciled
  if push delivery is missed or delayed.
- Keep the public export-job routes unchanged:
  `POST /drafts/seating/{draft_id}/exports/jobs`,
  `GET /exports/jobs/{job_id}`, and
  `GET /exports/jobs/{job_id}/download`.

## Test plan

- Focused application tests proving export-job creation no longer performs
  per-job webhook onboarding.
- Focused callback/dispatcher tests proving upstream job events resolve to the
  correct local `SeatingExportJob`.
- Idempotency tests for repeated callback delivery.
- Focused API tests proving the public contract remains unchanged.

## Rollback plan

- Restore per-job webhook onboarding while keeping polling fallback and the
  current export-job API intact.

## Supersession note

- This PR remains historical documentation for the original Sir Convert-based
  seating export lane.
- It is an approved removal target after the local seating-PDF cutover defined
  by `ADR-0075`.
