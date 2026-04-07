---
type: review
id: REV-ST-14-35
title: "Review: ST-14-35 tool data libraries"
status: pending
owners: "agents"
created: 2026-01-12
updated: 2026-04-06
reviewer: "external-reviewer"
adrs:
  - ADR-0058
  - ADR-0059
stories:
  - ST-14-35
  - ST-14-36
links:
  - EPIC-14
  - EPIC-19
---

## TL;DR

We propose two reusable per-user data surfaces for tools: datasets for structured lists such as class rosters, and a
file vault for reusable uploads and saved artifacts. The review stays anchored on `ST-14-35`, with `ST-14-36` retained
as supporting governed scope.

## Problem Statement

Tool settings are a single dict and cannot represent reusable lists. Users also re-upload the same files repeatedly,
and run artifacts are not reusable as inputs. Those gaps block workflows like class-based grouping, roster reuse, and
using cleaned outputs as inputs for subsequent runs.

## Proposed Solution

- ADR-0058: per-user datasets library scoped to a tool, with CRUD and a picker. Selected dataset is injected into
  `memory["dataset"]` + `memory["dataset_meta"]`.
- ADR-0059: per-user file vault with explicit save/delete/restore, including save-from-artifact. Selected vault files
  are staged into `/work/input` and appear in the input manifest.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/adr/adr-0058-tool-datasets-library.md` | Dataset contract + memory injection | 10 min |
| `docs/adr/adr-0059-user-file-vault.md` | Vault lifecycle, soft delete + retention | 10 min |
| `docs/backlog/stories/story-14-35-tool-datasets-crud-and-picker.md` | Acceptance criteria | 8 min |
| `docs/backlog/stories/story-14-36-user-file-vault-and-picker.md` | Acceptance criteria + artifact save | 8 min |
| `docs/backlog/sprints/sprint-2026-02-24-tool-data-libraries-v1.md` | Sprint scope + risks | 8 min |

**Total estimated time:** ~44 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Dataset injection shape (`memory["dataset"]` + `memory["dataset_meta"]`) | Clear separation from settings; deterministic; minimal tool changes | [ ] |
| File vault soft delete + restore + retention purge | Safety for accidental deletes; predictable cleanup | [ ] |
| Save run artifacts to vault (explicit user action) | Highest reuse value; avoids repeated exports/uploads | [ ] |

## Review Checklist

- [ ] ADRs define clear contracts
- [ ] EPIC scope is appropriate
- [ ] Stories have testable acceptance criteria
- [ ] Implementation aligns with codebase patterns
- [ ] Risks are identified with mitigations

## Review Feedback

**Reviewer:** external-reviewer
**Date:** 2026-04-06
**Verdict:** pending

### Required Changes

Decide the dataset injection shape and file-vault retention model before implementation starts, and confirm whether
artifact save belongs in this slice or a later follow-up.

### Suggestions (Optional)

Keep `ST-14-36` as supporting governed scope rather than a second primary review gate.

### Decision Approvals

- [ ] Dataset injection shape
- [ ] File vault retention model
- [ ] Artifact save scope

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | Review record | Replaced template placeholders with explicit pending-review decisions for the tool-data libraries split. |
| 2 | ST-14-35 / ST-14-36 | Preserved `ST-14-36` as supporting scope instead of hiding it behind generic placeholder text. |
