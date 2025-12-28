---
type: story
id: ST-16-03
title: "Flat catalog API with label filtering and search"
status: done
owners: "agents"
created: 2025-12-26
updated: 2025-12-28
epic: EPIC-16
acceptance_criteria:
  - "Given GET /api/v1/catalog/tools with no parameters, when called, then returns all published tools"
  - "Given GET /api/v1/catalog/tools?professions=larare, when called, then returns tools tagged with 'larare' profession"
  - "Given GET /api/v1/catalog/tools?categories=svenska,matematik, when called, then returns tools tagged with svenska OR matematik"
  - "Given GET /api/v1/catalog/tools?professions=larare&categories=svenska, when called, then returns tools tagged with profession larare AND category svenska"
  - "Given GET /api/v1/catalog/tools?q=ordlista, when called, then returns tools with 'ordlista' in title or summary (case-insensitive)"
  - "Given GET /api/v1/catalog/tools with filters, when response returned, then each tool includes is_favorite boolean for authenticated user"
  - "Given GET /api/v1/catalog/tools, when response returned, then includes all professions and categories for filter UI"
  - "Given GET /api/v1/catalog/tools?professions=larare,doesnotexist, when called, then the unknown slug is ignored (no error) and filtering behaves as if only larare was provided"
  - "Given GET /api/v1/catalog/tools?professions=doesnotexist, when called, then returns empty tools list (no match, no error)"
---

## Context

This story implements the flat catalog API endpoint that returns all published tools with optional filtering and search. It enables the new flat browse experience.

## API contract

```
GET /api/v1/catalog/tools?professions=slug1,slug2&categories=slug1,slug2&q=term

Response 200:
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

## Filter logic

Filtering uses OR within each facet and AND across facets:

1. If `professions` specified: Include tools tagged with ANY listed profession
2. If `categories` specified: Include tools tagged with ANY listed category
3. If `q` specified: Include tools where title OR summary contains the term (ILIKE)
4. Facets are combined with AND: tool must match ALL specified facets (professions facet AND categories facet AND q when present)

Example: `?professions=larare&categories=svenska,matematik&q=ord`

- Tool must be tagged with profession "larare" AND
- Tool must be tagged with category "svenska" OR "matematik" AND
- Tool must have "ord" in title or summary

## Implementation notes

### Repository extension

Add to `ToolRepositoryProtocol` in `src/skriptoteket/protocols/catalog.py`:

```python
async def list_published_filtered(
    self,
    *,
    profession_ids: list[UUID] | None = None,
    category_ids: list[UUID] | None = None,
    search_term: str | None = None,
) -> list[Tool]: ...
```

Implement in `src/skriptoteket/infrastructure/repositories/tool_repository.py` with:

- JOIN on `tool_professions` filtered by `profession_id.in_(ids)`
- JOIN on `tool_categories` filtered by `category_id.in_(ids)`
- WHERE clause with `title ILIKE` and `summary ILIKE`
- DISTINCT to avoid duplicates from multiple tag matches

### Handler

Create `src/skriptoteket/application/catalog/handlers/list_all_tools.py`:

1. Resolve profession slugs to IDs (ignore invalid)
2. Resolve category slugs to IDs (ignore invalid)
   - If a facet parameter is present but resolves to no IDs, return 0 tools (no match)
3. Call `list_published_filtered` with resolved IDs
4. Batch-check favorites for returned tools
5. Return tools + all professions + all categories

## Files to create

- `src/skriptoteket/application/catalog/handlers/list_all_tools.py`

## Files to modify

- `src/skriptoteket/protocols/catalog.py` (add list_published_filtered)
- `src/skriptoteket/infrastructure/repositories/tool_repository.py` (implement)
- `src/skriptoteket/application/catalog/queries.py` (add ListAllToolsQuery/Result)
- `src/skriptoteket/web/api/v1/catalog.py` (add GET /tools endpoint)
- `src/skriptoteket/di/catalog.py` (wire handler)

## Testing

- Unit test for handler with various filter combinations
- Integration test for repository filtering
- API test for query parameter parsing
- Test that invalid slugs are silently ignored
