---
type: story
id: ST-SKRIPT-16-08
title: 'Catalog cleanup: curated-apps-only filter + final EPIC-16 review'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: ready
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SKRIPT-16
acceptance_criteria:
- Given the flat /browse view, when loaded, then the 'Bläddra efter yrkesgrupp' entrypoint
  link is removed from the page
- Given the flat catalog, when the user toggles 'Enbart kurerade appar' (separate
  master filter above results), then only curated apps are shown
- Given the curated-apps-only filter, when it is active, then the UI shows a succinct
  subtitle explaining the scope (e.g. 'Visar bara appar utan verktyg')
- Given curated-apps-only is active, when the URL contains the filter flag, then the
  checkbox is pre-selected on load
- Given curated-apps-only is inactive, when the user clears filters, then the master
  filter is also cleared
- Given EPIC-16 stories ST-16-01..07, when final review is performed, then each story's
  acceptance criteria are verified and results are recorded with any follow-ups
retired_ids:
- ST-16-08
---

## Context

Source: `docs/backlog/stories/story-16-08-catalog-cleanup-and-review.md`. Catalog cleanup: curated-apps-only filter + final EPIC-16 review.

ST-16-05 introduced a flat catalog view that supersedes the old "Bläddra efter yrkesgrupp" entrypoint. This cleanup story removes legacy affordances, adds a master filter for curated apps, and finishes with a full EPIC-16 review. - Placement: the "Enbart kurerade appar" checkbox sits **above the results list** (right column), separated from the profession/category facets to make it a distinct master filter. - Subtitle: short, explanatory text to clarify that curated apps are not standard tool-driven UI. ``` ┌─────────────────────────────────────────────────────────────┐ │ Katalog                                                     │ ├──────────────────────────────────────────────────────────

## Epic Contract Slice

The story retains the source behavior slice and its actor/consumer boundary.

## ADR Coverage

Source references: ST-16-05, EPIC-16, ST-16-01..07, ADR-0042.

## Contract Inputs

- Source story and audit-approved migration authority.
- Current epic/relationship fields in candidate frontmatter.

## Live Verification Plan

Verify the story slice through its current tasks and retain focused evidence at closeout.

## Non-Goals

No adjacent capability, terminal record, or unapproved implementation scope is added.

## Notes

### Source evidence

### Context

ST-16-05 introduced a flat catalog view that supersedes the old "Bläddra efter yrkesgrupp" entrypoint. This cleanup
story removes legacy affordances, adds a master filter for curated apps, and finishes with a full EPIC-16 review.

### Decision log

- Placement: the "Enbart kurerade appar" checkbox sits **above the results list** (right column), separated from the
  profession/category facets to make it a distinct master filter.
- Subtitle: short, explanatory text to clarify that curated apps are not standard tool-driven UI.

### UI layout

```
┌─────────────────────────────────────────────────────────────┐
│ Katalog                                                     │
├─────────────────────────────────────────────────────────────┤
│ [Sök verktyg... ____________________________]               │
├─────────────────┬───────────────────────────────────────────┤
│ YRKESGRUPPER    │ [☐ Enbart kurerade appar]                 │
│ ☐ Lärare        │  Visar bara appar utan verktyg            │
│ ...             │                                           │
│ KATEGORIER      │  ┌─────────────────────────────────┐      │
│ ☐ Svenska       │  │ Ordlistegenerator          ★    │      │
│ ...             │  │ [Välj →]                        │      │
│                 │  └─────────────────────────────────┘      │
└─────────────────┴───────────────────────────────────────────┘
```

### Implementation notes

### Flat browse cleanup

- Remove the "Bläddra efter yrkesgrupp" link from `frontend/apps/skriptoteket/src/views/BrowseFlatView.vue`.
- Keep hierarchical browse routes intact; this story only removes the superseded entrypoint.

### Curated-apps-only filter

- Add a master filter checkbox + subtitle above the results list in the flat browse view.
- Treat it as a client-side filter (no API parameter). Filter the mixed catalog list so only `kind = curated_app`
  remains when active.
- Reflect the filter in the URL query (new boolean flag) and hydrate it on load, consistent with other filters.

### Final EPIC-16 review

- Validate ST-16-01..07 acceptance criteria across API + UI.
- Record results and follow-ups in `.codex/handoff.md` and any relevant story docs.

### Files to modify

- `frontend/apps/skriptoteket/src/views/BrowseFlatView.vue`
- `frontend/apps/skriptoteket/src/composables/useCatalogFilters.ts`
- `.codex/handoff.md` (review results)

### Dependencies

- ADR-0042 should be updated and reviewed if the removal of the hierarchical entrypoint changes the accepted contract.

## Decision And Assumption Ledger

| ID | Type | Status | Question/Assumption | Recommendation/Decision | Source |
| --- | --- | --- | --- | --- | --- |
| MIG-ST-SKRIPT-16-08 | migration | closed | How is source meaning preserved? | Preserve the source story contract and current status while changing identity only. | ST-SKILL-08-06; TASK-SKRIPT-REP-0003 |

## Plan Document Review

No specialist approval is asserted; parent review remains required.

## Story Closeout Review

No closeout evidence is asserted in this candidate.
