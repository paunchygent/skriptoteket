---
type: epic
id: EPIC-16
title: "Catalog discovery and personalization"
status: proposed
owners: "agents"
created: 2025-12-26
outcome: "Teachers can discover tools via flat browsing with filters, search, and access personalized favorites/recently-used lists"
---

## Scope

### In scope

- **Flat catalog view** as primary `/browse` experience showing all published tools
- **Label filtering** with profession and category checkboxes (OR logic)
- **Text search** on tool title and summary (ILIKE, case-insensitive)
- **User favorites** (add/remove/list bookmarked tools)
- **Recently used tools** derived from existing `tool_runs` history
- **Home page sections** for favorites and recent tools

### Out of scope

- Full-text search with ranking (tsvector/tsquery)
- Tag suggestions or auto-complete in search
- Tool recommendations based on usage patterns
- Hierarchical browse redesign (retained as-is for users who prefer it)
- Pagination (monitor and add if tool count grows)

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Performance degradation with many tools | Low | Medium | Monitor query times; add pagination if needed |
| Filter UI complexity confuses users | Medium | Low | Follow existing brutalist design patterns; user testing |
| OR filter returns too many results | Low | Low | Clear filter state in URL; "Rensa filter" button |

## Dependencies

- **ADR-0041**: User favorites and tool bookmarking (domain model, API contract)
- **ADR-0042**: Flat catalog with label filtering (filter logic, search approach)

## Stories

| ID | Title | Status |
|----|-------|--------|
| ST-16-01 | Favorites domain model and database migration | ready |
| ST-16-02 | Favorites API endpoints (add/remove/list) | ready |
| ST-16-03 | Flat catalog API with label filtering and search | ready |
| ST-16-04 | Recently used tools API endpoint | ready |
| ST-16-05 | Flat catalog Vue view with filter sidebar | ready |
| ST-16-06 | Tool card favorites toggle (star icon) | ready |
| ST-16-07 | Home view favorites and recently used sections | ready |

## Success criteria

1. Teachers can see all tools on `/browse` without clicking through professions/categories
2. Teachers can filter by multiple labels and search by tool name
3. Teachers can favorite tools and access them quickly from home page
4. Teachers can see their recently used tools on home page
5. Filter state is reflected in URL (shareable, bookmarkable)
