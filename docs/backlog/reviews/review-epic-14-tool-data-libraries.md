---
type: review
id: REV-EPIC-14
title: "Review: EPIC-14 Tool data libraries (datasets + file vault)"
status: pending
owners: "agents"
created: 2026-01-12
reviewer: "external-reviewer"
epic: EPIC-14
adrs:
  - ADR-0058
  - ADR-0059
stories:
  - ST-14-35
  - ST-14-36
---

## TL;DR

We propose adding two reusable per-user data surfaces for tools: datasets (structured lists such as class rosters) and a
file vault (reusable uploads + saved artifacts). This should reduce repetitive uploads and unlock better tool UX without
changing the runner contract beyond memory injection and input staging.

## Problem Statement

Tool settings are a single dict and cannot represent reusable lists. Users also re-upload the same files repeatedly, and
run artifacts are not reusable as inputs. These gaps block workflows like class-based grouping, roster reuse, and using
cleaned outputs as inputs for subsequent runs.

## Proposed Solution

- ADR-0058: Per-user datasets library scoped to a tool, with CRUD and a picker. Selected dataset is injected into
  `memory["dataset"]` + `memory["dataset_meta"]`.
- ADR-0059: Per-user file vault with explicit save/delete/restore, including save-from-artifact. Selected vault files are
  staged into `/work/input` and appear in the input manifest.

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

---

## Review Feedback

**Reviewer:** @[reviewer-name]
**Date:** YYYY-MM-DD
**Verdict:** [pending | approved | changes_requested | rejected]

### Required Changes

[List specific changes needed, or "None" if approved]

### Suggestions (Optional)

[Non-blocking recommendations]

### Decision Approvals

- [ ] Decision 1
- [ ] Decision 2
- [ ] Decision 3

---

## Changes Made

[Author fills this in after addressing feedback]

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | ADR-0058 | [What was changed] |
| 2 | ADR-0059 | [What was changed] |
