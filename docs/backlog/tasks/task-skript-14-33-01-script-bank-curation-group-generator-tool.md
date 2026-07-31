---
type: task
id: TASK-SKRIPT-14-33-01
title: Script bank curation + group generator tool
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: ready
readiness_review:
  record: inline
  status: not_required
  approval_protocol: agent-planning:user-closure-gate
  approval_evidence: user closure 2026-07-31
closeout_review:
  record: inline
  status: not_started
story: ST-SKRIPT-14-33
task_kind: story
acceptance_criteria:
- Script bank seeding supports dev/prod profiles and prod seeds curated tools only.
- Curated script bank tools are updated to use runner toolkit helpers and enum action
  fields.
- A new group generator tool is added to the curated script bank.
- Runbooks and guidance reflect the new seeding profiles.
---

## Context

### Problem

Script bank seeding currently uses a single list, which makes it easy to seed test/demo tools into production. Some
curated tools also rely on ad-hoc env parsing instead of the runner toolkit helpers, creating drift from the latest
runner contract and AI guidance. We also need a curated tool for grouping students that uses inputs + settings in a
teacher-first way.

### Goal

- Separate curated vs test tools with explicit seeding profiles (ADR-0056).
- Update curated script bank tools to use runner toolkit helpers and enum action fields.
- Add a curated “group generator” tool that supports roster uploads, group sizing, memory-backed class selection, and
  named group sets.

### Non-goals

- Redesigning the admin editor UI.
- Changing the runner contract.

### Implementation plan

1) Script bank curation
   - Add `seed_group` to `ScriptBankEntry` with `curated` vs `test`.
   - Tag script bank entries accordingly (curated includes the five listed tools).
2) Seeding profiles
   - Extend `seed-script-bank` with `--profile dev|prod` (default `dev`) and `--group` override.
   - Update runbooks to use `--profile prod` for home server.
3) Curated tool updates
   - Refactor curated script bank tools to use `skriptoteket_toolkit` helpers for inputs, manifests, actions, and
     settings (remove manual env parsing).
   - Align any action field kinds to `enum` where applicable.
4) New tool: group generator
   - Add new script under `src/skriptoteket/script_bank/scripts/`.
   - Add new `ScriptBankEntry` with inputs + settings schema (class picker + group size + name).
   - Persist class rosters in memory settings; allow selecting exactly one saved class at a time.
5) Docs updates
   - Update `docs/runbooks/runbook-script-bank-seeding.md` and home-server runbook.
   - Update AI KB/teacher guide if tool guidance changes.
6) Seed + verify locally
   - `pdm run seed-script-bank --dry-run --profile dev`

### Test plan

- `pdm run docs-validate`
- `pdm run seed-script-bank --dry-run --profile dev`
- `pdm run seed-script-bank --dry-run --profile prod`
- Manual: run the curated tools in dev after seeding (verify toolkit-based IO).

### Rollback plan

- Revert the commit(s) and re-run `seed-script-bank --sync-code` from the previous version.

## Decision And Assumption Ledger

The source material below remains authoritative for this section.

## Story Contract Slice

The source material below remains authoritative for this section.

## Contract Inputs

The source material below remains authoritative for this section.

## Plan

The source material below remains authoritative for this section.

## Implementation Steps

The source material below remains authoritative for this section.

## Proof

Verification expectations remain in the retained source material below.

## Validation

Verification expectations remain in the retained source material below.

## Stop Conditions

The source boundaries and recovery limits remain preserved below.

## Lessons Learned

The source material below remains authoritative for this section.

## Notes

The source material below remains authoritative for this section.

## Plan Document Review

The source material below remains authoritative for this section.

## Implementation Review

The source material below remains authoritative for this section.
