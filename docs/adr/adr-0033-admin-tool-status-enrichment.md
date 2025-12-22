---
type: adr
id: ADR-0033
title: "Admin tool status enrichment for lifecycle visibility"
status: proposed
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-22
links: ["ADR-0014", "ADR-0010", "ST-11-11"]
---

## Context

The AdminToolsView (ST-11-11) presents all tools in a flat list with minimal state information.
Admins cannot easily distinguish between:

1. **Tools in development** (no active version): Tools created from accepted suggestions (ADR-0010)
   that have not yet completed the version review workflow (ADR-0014)
2. **Ready tools** (has active version): Tools with at least one published version that can be
   shown/hidden to users via the publish toggle

For tools in development, admins need visibility into:

- Whether any code has been written yet (`version_count == 0` means "Ingen kod ännu")
- Whether there is a draft being worked on (`latest_version_state == "draft"`)
- Whether a version is pending review (`has_pending_review == true`)

The current `AdminToolItem` DTO only exposes `active_version_id` and `is_published`, which is
insufficient for meaningful status display.

## Decision

### 1. Extend AdminToolItem DTO with version status summary

Add three fields to `AdminToolItem`:

```python
version_count: int              # Total versions for this tool (0 = no code yet)
latest_version_state: str | None  # "draft", "in_review", or None
has_pending_review: bool        # True if any version is IN_REVIEW
```

### 2. Add aggregation method to ToolVersionRepositoryProtocol

Add a new method to efficiently fetch version statistics for multiple tools:

```python
async def get_version_stats_for_tools(
    self, *, tool_ids: list[UUID]
) -> dict[UUID, ToolVersionStats]: ...
```

Where `ToolVersionStats` is a frozen dataclass containing the three fields above.

This method uses the existing indexed columns (`tool_versions.tool_id`, `tool_versions.state`)
to perform efficient aggregation without fetching full version records.

### 3. Frontend two-section layout

The AdminToolsView splits tools into two sections:

| Section | Condition | Display |
|---------|-----------|---------|
| **Pågående** | `active_version_id === null` | Status badge based on version stats |
| **Klara** | `active_version_id !== null` | Publish toggle with "Publicerad"/"Ej publicerad" |

### 4. Swedish status labels

| Condition | Label |
|-----------|-------|
| `version_count == 0` | "Ingen kod" |
| `latest_version_state == "draft"` | "Utkast" |
| `has_pending_review == true` | "Granskas" |
| `active_version_id != null && is_published` | "Publicerad" |
| `active_version_id != null && !is_published` | "Ej publicerad" |

## Consequences

### Benefits

- Clear lifecycle visibility for admins managing tool development pipeline
- No database schema changes required (uses existing indexed columns)
- Consistent with ADR-0014 version lifecycle states
- Frontend logic remains simple (status derived from DTO fields)
- Batch query design minimizes database round-trips

### Tradeoffs

- Additional query per admin tools list (mitigated by batch fetch for all tool IDs)
- Handler now requires `ToolVersionRepositoryProtocol` dependency (acceptable coupling)
- Slightly larger API response payload (three additional fields per tool)
