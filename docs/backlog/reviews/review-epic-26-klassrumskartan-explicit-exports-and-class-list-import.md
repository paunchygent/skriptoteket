---
type: review
id: REV-EPIC-26
title: "Review: Klassrumskartan explicit exports and class-list import"
status: approved
owners: "agents"
created: 2026-03-24
updated: 2026-03-25
reviewer: "lead-developer"
epic: EPIC-26
adrs:
  - ADR-0069
  - ADR-0071
  - ADR-0072
stories:
  - ST-26-01
  - ST-26-02
  - ST-26-03
  - ST-26-04
  - ST-26-05
---

## TL;DR

EPIC-26 proposes the next Klassrumskartan lane after EPIC-24: explicit teacher-facing exports and bounded class-list import. The core direction is intentionally narrow. Seating ships first as a one-page poster-grade PDF rendered through a standalone export renderer, not through planner print CSS. Class-list import follows as a preview-first teacher confirmation flow for `XLSX`, `TXT`, and `PDF` via the fast Sir Convert-a-Lot lane. Editable `XLSX` exports and grouping exports follow after the seating poster contract is trusted.

## Problem Statement

EPIC-24 deliberately separated live draft work from durable artifacts, but Klassrumskartan still does not offer the explicit export flow that the accepted PRD and ADRs describe. Teachers need a whiteboard-ready seating printout and a practical way to ingest existing class lists without reopening the advanced planner lanes that were intentionally deferred.

## Proposed Solution

Create a new export-first epic instead of extending EPIC-24. The first story introduces a standalone seating export contract plus a one-page `pretty_brutalist_poster` PDF artifact. The second story adds teacher-confirmed class-list import from `XLSX`, `TXT`, and `PDF` via Sir Convert-a-Lot fast parsing. Later stories add seating `XLSX`, then grouping PDF/XLSX, while keeping exports separate from autosave, bounded history, and future smart-placement work. Export planning should keep Klassrumskartan-owned artifacts local to Skriptoteket while using Sir Convert-a-Lot for external/general-purpose conversion and PDF parsing.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/adr/adr-0066-sir-convert-a-lot-v2-as-canonical-conversion-engine.md` | Sir Convert-a-Lot service-boundary context | 5 min |
| `docs/adr/adr-0071-group-seating-studio-fundamentals-workflow-and-saved-artifacts.md` | Draft vs export artifact contract | 6 min |
| `docs/adr/adr-0072-group-seating-studio-class-first-workspace-and-draft-kinds.md` | Export/history/smart-placement boundaries | 5 min |
| `docs/backlog/epics/epic-26-klassrumskartan-explicit-exports-and-class-list-import.md` | Scope and sequencing | 8 min |
| `docs/backlog/stories/story-26-01-klassrumskartan-seating-pdf-poster-export-with-standalone-renderer.md` | First story acceptance criteria | 5 min |
| `docs/backlog/stories/story-26-02-klassrumskartan-class-list-import-from-file-with-preview-and-confirmation.md` | Import scope boundary | 5 min |
| `docs/backlog/stories/story-26-03-klassrumskartan-seating-xlsx-export.md` | Seating spreadsheet artifact shape | 4 min |
| `docs/backlog/stories/story-26-04-klassrumskartan-grouping-pdf-export.md` | Grouping print artifact semantics | 4 min |
| `docs/backlog/stories/story-26-05-klassrumskartan-grouping-xlsx-export.md` | Grouping spreadsheet artifact shape | 4 min |
| `docs/backlog/prs/pr-0118-klassrumskartan-seating-export-contract-and-standalone-poster-scene-model.md` | Contract and renderer decomposition | 5 min |
| `docs/backlog/prs/pr-0119-klassrumskartan-seating-pdf-poster-renderer-and-artifact-delivery.md` | Artifact rendering scope | 5 min |
| `docs/backlog/prs/pr-0120-klassrumskartan-seating-export-action-teacher-flow-and-browser-proof.md` | Teacher flow and proof strategy | 4 min |

**Total estimated time:** ~56 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| New epic instead of extending EPIC-24 | EPIC-24 is closed and explicitly deferred export generation to later work | [ ] |
| Seating export sequence before grouping export | Seating has the clearest whiteboard-print teacher use case and is the preferred future checkpoint source | [ ] |
| Standalone seating poster renderer | Prevent export quality from being constrained by current planner DOM/CSS limitations | [ ] |
| First PDF layout is `pretty_brutalist_poster` | Prioritize high-contrast readability with light branding and no metadata clutter | [ ] |
| Import stays preview-first and bounded | Keep roster ingestion useful without expanding into metadata enrichment or smart-planning prep | [ ] |
| Keep Klassrumskartan-owned artifacts local | Remove unnecessary distributed complexity from renderer-owned teacher artifacts while keeping Sir Convert for general conversion and parsing | [ ] |

## Review Checklist

- [ ] ADRs define clear contracts
- [ ] EPIC scope is appropriate
- [ ] Stories have testable acceptance criteria
- [ ] Implementation aligns with codebase patterns
- [ ] Risks are identified with mitigations

## Review Feedback

**Reviewer:** @lead-developer
**Date:** 2026-03-24
**Verdict:** approved

### Required Changes

- None.

### Suggestions (Optional)

- Confirm whether `ADR-0066` remains sufficient as reference context or whether later implementation should promote/update it once PDF-specific service calls become operationally binding.

### Decision Approvals

- [x] New epic instead of extending EPIC-24
- [x] Seating export sequence before grouping export
- [x] Standalone seating poster renderer
- [x] `pretty_brutalist_poster` as the first layout
- [x] Preview-first bounded import scope
- [x] Keep Klassrumskartan-owned artifacts local

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `EPIC-26`, `ST-26-02`, `REV-EPIC-26` | Removed `ADR-0066` as a hard dependency so EPIC-26 can become actionable without waiting on a broader unresolved ADR. |
| 2 | `ST-26-02`, `ST-26-04` | Trimmed false hard dependencies so sequencing preference does not masquerade as a contract prerequisite. |
| 3 | `REV-EPIC-26`, `ST-26-03`, `ST-26-04`, `ST-26-05` | Added later stories to the review surface and tightened export artifact-shape acceptance criteria for reviewable `ready` status. |
| 4 | `EPIC-26`, `ST-26-01` to `ST-26-05`, `REV-EPIC-26` | Clarified the current export/import planning split: Klassrumskartan-owned artifacts stay local in Skriptoteket, while Sir Convert-a-Lot remains the preferred service boundary for parsing and general conversion workloads. |
| 5 | `ST-26-01`, `PR-0118`, `PR-0119` | Locked the planning contract for seating export around explicit `seatingDraftId`, export-specific HTML/CSS as the canonical intermediate source, deterministic `first name + last initial` poster labels, and required room markers including windows and benches/tables where present. |

## Post-Approval Refinements

- 2026-03-25 backlog tightening aligned the grouping export stories with the approved product direction from the active planning thread:
  - grouping `XLSX` is now explicitly the first grouping export artifact
  - grouping `PDF` now defaults to `A4` portrait and a digital-handout posture for Teams / Google Classroom sharing
  - the workbook and PDF stories now lock more of the artifact shape up front so implementation can be handed to a junior developer with fewer open presentation decisions
- 2026-03-25 seating `XLSX` refinement also locked the remaining workbook-shape questions from the active planning thread:
  - seating `PDF` remains the default export action
  - seating `XLSX` stays in the export menu as a secondary operational artifact
  - the workbook is local/generated in Skriptoteket, not routed through Sir Convert-a-Lot
  - the workbook now has an explicit two-sheet posture with an operational first tab and a secondary presentation sheet
- Added planned implementation-slice docs `PR-0139`, `PR-0140`, and `PR-0141` so the next implementation team can work from file-level checklist docs rather than from generic story text alone.

## Suggested Approval Wording

**Reviewer:** @lead-developer
**Date:** 2026-03-24
**Verdict:** approved

EPIC-26 is approved as the next Klassrumskartan lane after EPIC-24. The package keeps the accepted draft-vs-artifact boundary intact, starts with a no-slop seating PDF poster rendered through a standalone export contract, keeps roster import preview-first and bounded, and defers advanced history, metadata, zoning, and smart-placement work. Klassrumskartan-owned artifacts stay local to Skriptoteket, while Sir Convert-a-Lot remains the preferred dedicated service boundary for parsing and general conversion workloads. The epic may move from `proposed` to `active`, while its stories remain `ready` until implementation begins.
