---
type: adr
id: ADR-0042
title: "Flat catalog with label filtering"
status: accepted
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-26
updated: 2025-12-28
---

## Context

The current catalog navigation follows a hierarchical model:

```
/browse → Profession list
/browse/{profession} → Category list
/browse/{profession}/{category} → Tool list
```

This requires 3 clicks to reach any tool. Users cannot:

- See all available tools at once
- Filter across multiple categories
- Search for tools by name
- Share filtered views via URL

Teachers often know roughly what they're looking for but not the exact category. The hierarchical model forces them to guess the right path.

## Decision

### 1. Flat view as primary experience

The `/browse` route shows ALL published tools by default in a single flat list. This replaces the profession-first navigation as the primary entry point.

The hierarchical browse is retained as an alternative path for users who prefer drill-down exploration and to preserve curated app discoverability:

```
/browse/professions → Profession list
/browse/professions/{profession} → Category list
/browse/professions/{profession}/{category} → Tool + curated apps list
```

The flat browse view MUST include an explicit “Bläddra efter yrkesgrupp →” link to `/browse/professions`, and the
existing hierarchical breadcrumbs MUST link back to `/browse/professions` (not `/browse`) to avoid confusing
navigation after the route swap.

### 2. Filter logic: OR within facets, AND across facets

When a user selects multiple labels, filtering behaves as:

- **Within a facet** (professions or categories): selection uses **OR** (union).
  - Example: selecting Svenska + Matematik returns tools tagged with Svenska **OR** Matematik.
- **Across facets**: facets combine with **AND** (intersection).
  - Example: selecting profession Lärare and category Svenska returns tools tagged with (Lärare) **AND** (Svenska).
- Search term (`q`) is an additional **AND** constraint when provided.

Rationale: Teachers exploring the catalog benefit from broader results. Narrowing can be done by adding more specific terms to search.

### 3. Query parameters

```
GET /api/v1/catalog/tools?professions=larare,skolkurator&categories=svenska,matematik&q=ord
```

| Parameter | Format | Logic |
|-----------|--------|-------|
| `professions` | Comma-separated slugs | OR within professions; AND with other facets |
| `categories` | Comma-separated slugs | OR within categories; AND with other facets |
| `q` | Search term | AND constraint; ILIKE on title + summary |

All parameters are optional. With no parameters, returns all published tools.

Unknown slugs are ignored (no error). If a facet parameter is present but all provided slugs are unknown, the
result set is empty (deterministic “no match” instead of “return everything”).

### 4. Response shape

```json
{
  "tools": [
    {
      "id": "uuid",
      "slug": "ordlista-generator",
      "title": "Ordlistegenerator",
      "summary": "Skapar ordlistor från text",
      "is_favorite": true
    }
  ],
  "professions": [
    { "id": "uuid", "slug": "larare", "label": "Lärare", "sort_order": 1 }
  ],
  "categories": [
    { "id": "uuid", "slug": "svenska", "label": "Svenska" }
  ]
}
```

The response includes all professions and categories for the filter UI to render checkboxes/chips. The frontend
MAY cache this taxonomy client-side to avoid re-processing the same arrays on every filter change.

### 5. Search implementation

Simple ILIKE search on `title` and `summary` columns:

```sql
WHERE title ILIKE '%term%' OR summary ILIKE '%term%'
```

This is sufficient for the current tool count (~50-100). Full-text search with ranking (tsvector) is out of scope for this iteration.

### 6. URL reflects filter state

Filter selections are reflected in the URL query string:

```
/browse?categories=svenska,matematik&q=ord
```

This enables:

- Browser back/forward navigation
- Shareable filtered views
- Bookmarking specific filters

### 7. Frontend implementation

```
┌─────────────────────────────────────────────────────────────┐
│ [Search: _______________]                                   │
│ [Bläddra efter yrkesgrupp →]                                │
├─────────────────┬───────────────────────────────────────────┤
│ Yrkesgrupper    │                                           │
│ ☐ Lärare        │  ┌─────────────────────────────────┐      │
│ ☐ Skolkuratorer │  │ Ordlistegenerator          ★    │      │
│                 │  │ Skapar ordlistor från text      │      │
│ Kategorier      │  │ [Välj →]                        │      │
│ ☑ Svenska       │  └─────────────────────────────────┘      │
│ ☑ Matematik     │                                           │
│ ☐ Engelska      │  ┌─────────────────────────────────┐      │
│                 │  │ Mattetest-generator        ☆    │      │
│ [Rensa filter]  │  │ Genererar slumpade mattetest    │      │
│                 │  │ [Välj →]                        │      │
│                 │  └─────────────────────────────────┘      │
└─────────────────┴───────────────────────────────────────────┘
```

- Filter sidebar with checkboxes
- Search input with 300ms debounce
- Tool cards with favorite toggle (star)
- Active filters reflected as URL query params

## Consequences

### Positive

- Teachers can see all tools immediately
- Faster discovery — one page instead of three clicks
- Filter across categories (impossible in hierarchical model)
- Search finds tools by name without knowing category
- Shareable filtered views via URL

### Negative

- Potentially overwhelming if tool count grows large (mitigate with pagination later)
- OR-within-facet may surface too many results for some queries (mitigate via combining facets + search)
- Requires careful routing/breadcrumb updates to avoid regressions in the hierarchical browse flow

### Implementation impact

Backend:

- New `list_published_filtered` method on `ToolRepositoryProtocol`
- New `ListAllToolsHandler` with filter logic
- New `GET /api/v1/catalog/tools` endpoint

Frontend:

- New `BrowseFlatView.vue` component
- New `useCatalogFilters.ts` composable
- Route change: `/browse` uses flat view by default
- New hierarchical entrypoint route: `/browse/professions` (preserves curated apps discoverability)

## Related

- ADR-0041: User favorites and tool bookmarking (is_favorite in response)
- ADR-0003: Script taxonomy (professions and categories model)
- EPIC-16: Catalog discovery and personalization
