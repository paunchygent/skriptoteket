---
type: pr
id: PR-0075
title: "Textbook corpus — multi-agent manual restoration and verification workflow"
status: ready
owners: "agents"
created: 2026-03-04
updated: 2026-03-04
stories:
  - "ST-22-01"
tags: ["data", "quality", "manual-review"]
acceptance_criteria:
  - "Semantically important changes are applied through issue-scoped manual patch files, not direct bulk rewrites."
  - "Each manual patch has source references, rationale, and verifier approval metadata before apply."
  - "Patch application is deterministic and reversible."
---

## Problem

The most important textbook corruption cannot be solved safely by script alone. We need real manual labor with strong controls.

## Goal

Establish a multi-agent manual restoration lane that is auditable, conflict-safe, and meaning-preserving.

## Non-goals

- No one-shot full-file manual rewrites.
- No self-approval (same agent cannot author and verify the same patch).

## Implementation plan

1. Define issue packet schema and assignment strategy (non-overlapping ranges/IDs).
2. Define manual patch schema (`manual_fixes/*.yaml`) with provenance fields.
3. Implement verifier workflow and deterministic apply order.
4. Add rejection/rework loop for disputed patches.
5. Emit restoration report with accepted/rejected patch counts.

## Test plan

- Schema validation tests for patch files.
- Apply/revert determinism tests.
- Simulated conflict tests to verify non-overlap enforcement.

## Rollback plan

- Revert applied manual patch artifacts from this slice.
- Rebuild from mechanical baseline and patch queue.
