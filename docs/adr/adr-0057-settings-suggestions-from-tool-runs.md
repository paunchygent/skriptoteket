---
type: adr
id: ADR-0057
title: "Settings suggestions from tool runs"
status: proposed
owners: "agents"
deciders: ["user-lead"]
created: 2026-01-12
---

## Context

Tools sometimes derive reusable settings from user input (e.g., class rosters). Today, the only way to persist those
settings is manual copy/paste into the settings panel, which is poor UX and error-prone. We need a safe, explicit path
for a tool to propose settings without allowing the runner to write directly to persisted settings.

## Decision

Extend the UI contract v2.x with an optional `settings_suggestions` payload:

```json
{
  "settings_suggestions": [
    {
      "key": "saved_classes_json",
      "label": "Spara klasslista",
      "summary": "Klass: 7A (24 elever)",
      "value": { "7A": ["Anna Andersson", "Bo Berg"] }
    }
  ]
}
```

Rules:

- Suggestions are **non-persistent** until the user clicks “Spara”.
- The UI renders a suggestion card with a single save action (no raw JSON shown by default).
- The backend validates against `settings_schema` and applies the update using existing settings persistence.

## Consequences

- Adds a small UI contract extension, but no DB schema change.
- Requires UI work for rendering suggestion cards and invoking settings save.
- Keeps the security boundary intact: only the web layer persists settings after explicit user action.
