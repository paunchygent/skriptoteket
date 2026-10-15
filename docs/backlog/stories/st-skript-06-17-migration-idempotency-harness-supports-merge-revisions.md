---
type: story
id: ST-SKRIPT-06-17
title: Migration idempotency harness supports merge revisions
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-15'
status: proposed
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SKRIPT-06
acceptance_criteria:
- tests/integration/test_migration_revision_coverage_idempotent.py passes for 6a1e9d3c4b7f
  and every other merge revision; migration_idempotency_support resolves a merge revision's
  parents instead of raising; no assertion or revision mapping is dropped.
links:
  decisions: []
backlog_document_profile: contract-derived
---

## Slice Contract

## Contract Inputs

## Tasks

## Verification

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
