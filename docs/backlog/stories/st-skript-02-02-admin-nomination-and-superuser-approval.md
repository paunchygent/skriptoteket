---
type: story
id: ST-SKRIPT-02-02
title: Admin nomination and superuser approval
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
epic: EPIC-SKRIPT-02
acceptance_criteria:
- Given an admin, when they nominate a user for admin, then the nomination is recorded
  with nominator, rationale, and timestamp.
- Given a superuser, when they view pending nominations, then they can see the nominee,
  nominator, rationale, and creation timestamp.
- Given a superuser, when they approve a nomination, then the nominee becomes an admin
  and the approval decision is recorded with actor and timestamp.
- Given a superuser, when they deny a nomination, then the nominee's role is unchanged
  and the denial decision is recorded with actor and timestamp.
- Given a non-superuser, when they attempt to approve/deny a nomination, then they
  are denied.
retired_ids:
- ST-02-02
---

## Context

### Context

Admins have elevated governance capabilities (including publishing tools and tool script versions). Promoting a user to
admin therefore requires a superuser gate as described in ADR-0005.

### Notes

- Implement with protocol-first DI and an append-only, auditable decision record (mirror the suggestions decisioning
  pattern: nominate → decide).

## Epic Contract Slice

The source material below remains authoritative for this section.

## Contract Inputs

The source material below remains authoritative for this section.

## Live Verification Plan

Verification expectations remain in the retained source material below.

## Non-Goals

The source boundaries and recovery limits remain preserved below.

## Notes

The source material below remains authoritative for this section.

## Decision And Assumption Ledger

The source material below remains authoritative for this section.

## Plan Document Review

The source material below remains authoritative for this section.

## Story Closeout Review

The source material below remains authoritative for this section.
