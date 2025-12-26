---
type: adr
id: ADR-0042
title: "Flat catalog with label filtering"
status: proposed
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-26
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

The old hierarchical browse is retained as an alternative path for users who prefer drill-down exploration.

### 2. Filter logic: OR (union)

When a user selects multiple labels (professions or categories), the filter uses OR logic:

- Selecting "Svenska" + "Matematik" shows tools tagged with Svenska **OR** Matematik
- This maximizes discovery — users see more options, not fewer

Rationale: Teachers exploring the catalog benefit from broader results. Narrowing can be done by adding more specific terms to search.

### 3. Query parameters

```
GET /api/v1/catalog/tools?professions=larare,skolkurator&categories=svenska,matematik&q=ord
```

| Parameter | Format | Logic |
|-----------|--------|-------|
| `professions` | Comma-separated slugs | OR filter |
| `categories` | Comma-separated slugs | OR filter |
| `q` | Search term | ILIKE on title + summary |

All parameters are optional. With no parameters, returns all published tools.

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
    { "id": "uuid", "slug": "larare", "label": "Lärare" }
  ],
  "categories": [
    { "id": "uuid", "slug": "svenska", "label": "Svenska" }
  ]
}
```

The response includes all professions and categories for the filter UI to render checkboxes/chips.

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
- OR logic may surface too many results for some queries

### Implementation impact

Backend:

- New `list_published_filtered` method on `ToolRepositoryProtocol`
- New `ListAllToolsHandler` with filter logic
- New `GET /api/v1/catalog/tools` endpoint

Frontend:

- New `BrowseFlatView.vue` component
- New `useCatalogFilters.ts` composable
- Route change: `/browse` uses flat view by default

## Related

- ADR-0041: User favorites and tool bookmarking (is_favorite in response)
- ADR-0003: Script taxonomy (professions and categories model)
- EPIC-16: Catalog discovery and personalization
