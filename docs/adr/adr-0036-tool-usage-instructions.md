---
type: adr
id: ADR-0036
title: "Tool usage instructions architecture"
status: proposed
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-24
links: ["EPIC-08", "ST-08-13"]
---

## Context

Skriptoteket's tools currently lack user-friendly instructions. The existing `Tool.summary` field serves as a brief description shown in browse lists, but there is no mechanism for providing detailed, step-by-step guidance on how to use a tool effectively.

**Current limitations:**

1. `Tool.summary` is too short for comprehensive instructions
2. No separation between "what the tool does" (summary) and "how to use it" (instructions)
3. Frontend has no markdown rendering (`UiOutputMarkdown.vue` displays raw preformatted text)
4. Users must figure out tool usage through trial and error

**User need:** Teachers want clear, actionable instructions in Swedish that explain how to prepare input files, what to expect, and how to use the output (e.g., "download the file and paste into Outlook's BCC field").

## Decision

### 1. Add `usage_instructions` field to `ToolVersion`

```python
class ToolVersion(BaseModel):
    # ... existing fields
    usage_instructions: str | None = None  # Markdown content
```

**Why ToolVersion (not Tool):**
- Instructions may need updates when code changes
- Version-level allows instructions to evolve with the script
- Follows existing pattern where `settings_schema` lives on ToolVersion

### 2. Separate concerns

| Field | Purpose | Where displayed |
|-------|---------|-----------------|
| `Tool.summary` | Brief description (1-2 sentences) | Browse lists, search results |
| `ToolVersion.usage_instructions` | Detailed how-to guide (markdown) | ToolRunView only |

### 3. Add markdown rendering to frontend

- Install `marked` library for markdown → HTML conversion
- Create reusable markdown renderer component
- Fix existing `UiOutputMarkdown.vue` to properly render markdown

### 4. UI presentation in ToolRunView

- Collapsible section titled "Så här gör du" (collapsed by default)
- Rendered markdown with appropriate typography (prose styling)
- Only shown if `usage_instructions` is non-empty

### 5. Script bank integration

Extend `ScriptBankEntry` to include `usage_instructions`:

```python
class ScriptBankEntry(BaseModel):
    # ... existing fields
    usage_instructions: str | None = None
```

The `seed_script_bank` CLI command syncs this to the database.

## Consequences

### Positive

- Users get clear, contextual help directly in the tool interface
- Markdown allows structured content (headings, lists, emphasis, tables)
- Instructions can be versioned alongside code changes
- Fixes existing broken markdown rendering in tool outputs
- Reusable markdown component benefits other features

### Negative

- Database migration required (new column on `tool_versions`)
- API contract change (`ToolMetadataResponse` gets new field)
- New frontend dependency (`marked`)
- Content creation effort for existing tools

### Neutral

- No impact on existing tools without instructions (field is optional)
- Backward compatible API change (new optional field)
