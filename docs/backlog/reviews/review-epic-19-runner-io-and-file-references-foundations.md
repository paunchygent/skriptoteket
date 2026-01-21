---
type: review
id: REV-EPIC-19
title: "Review: Runner I/O + file references foundations"
status: approved
owners: "agents"
created: 2026-01-20
reviewer: "lead-developer"
epic: EPIC-19
adrs:
  - ADR-0063
  - ADR-0064
  - ADR-0065
stories:
  - ST-19-01
  - ST-19-02
  - ST-19-03
---

## TL;DR

EPIC-19 establishes a single, cohesive runner request envelope (`/work/request.json`), first-class file references
(session/vault), and runner contract v3 with explicit state semantics, structured errors, and tool-requested session
promotions. This is a breaking, no-shim cutover that reduces tool author complexity and enables reliable multi-step
workflows without path leakage.

## Problem Statement

Runner-based tools currently rely on multiple env-var JSON payloads and implicit file identity/path conventions. This:

- fragments tool author DX across inputs/actions/manifests
- makes multi-step workflows brittle (manual filename passing, path leakage)
- lacks a stable, platform-validated identifier model for selecting/rehydrating files across turns and sources

## Proposed Solution

- Replace env-var JSON payload transport with a single request envelope (`ADR-0063`).
- Introduce `FileRef` (string prefix encoding) + resolver that stages into `/work/input/` and emits a deterministic
  manifest (`ADR-0064`).
- Upgrade runner result contract to v3 with `state_update`, structured `error`, and session promotions with strict
  failure invariants (`ADR-0065`).
- Keep vault persistence explicitly user-initiated (ADR-0059); tools may request session promotions only.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/adr/adr-0063-runner-request-envelope-v1.md` | Request envelope + cutover rules | 8 min |
| `docs/adr/adr-0064-file-references-and-resolver.md` | FileRef encoding + resolver responsibilities | 10 min |
| `docs/adr/adr-0065-runner-contract-v3-state-update-errors-and-session-promotions.md` | Contract v3 + promotion semantics | 10 min |
| `docs/backlog/epics/epic-19-runner-io-and-file-references-foundations.md` | Scope boundaries + invariants | 5 min |
| `docs/backlog/stories/story-19-01-runner-request-envelope.md` | Testable AC + schema | 5 min |
| `docs/backlog/stories/story-19-02-file-refs-resolver-and-promotion.md` | Resolver + promotion plumbing AC | 5 min |
| `docs/backlog/stories/story-19-03-runner-contract-v3-structured-errors-state-update-and-promotions.md` | Failure invariants + v3 parsing | 5 min |
| `docs/backlog/stories/story-14-24-ui-contract-file-references.md` | No-parallel-plumbing alignment | 3 min |
| `docs/backlog/stories/story-14-36-user-file-vault-and-picker.md` | No-parallel-plumbing alignment | 3 min |

**Total estimated time:** ~54 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| FileRef encoding: string prefixes (`session:*`, `vault:*`) | Best DX/UX round-tripping for tools + action forms | [x] |
| Promotion semantics: tool-requested session promotions; vault user-initiated | Enables workflows without auto-persisting user data | [x] |
| Cutover: hard cut to request envelope + contract v3 (no shims) | Avoids parallel mechanisms; aligns with repo policy | [x] |

## Review Checklist

- [x] ADRs define clear contracts
- [x] EPIC scope is appropriate
- [x] Stories have testable acceptance criteria
- [x] Implementation aligns with codebase patterns
- [x] Risks are identified with mitigations

---

## Review Feedback

**Reviewer:** @lead-developer
**Date:** 2026-01-20
**Verdict:** approved

### Required Changes

None.

### Suggestions (Optional)

- Keep `files[].ref` as a canonical identifier and never return filesystem paths in any “available files” listing API.

### Decision Approvals

- [x] FileRef encoding (string prefixes)
- [x] Promotion semantics (session tool-requestable; vault user-initiated)
- [x] Hard cut to request envelope + contract v3

---

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | EPIC-19 + ST-19-* | Added DX gold standard invariants and clarified hybrid promotion semantics |
| 2 | ADR-0024/0031/0039 | Aligned payload/manifest transport references to the request envelope |
| 3 | ST-14-24/14-36 | Tightened “no parallel mechanisms” alignment with FileRef foundations |
