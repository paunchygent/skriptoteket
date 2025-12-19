---
type: template
id: TPL-sprint-plan
title: "Sprint plan template"
status: active
owners: "agents"
created: 2025-12-19
for_type: sprint
---

Copy, fill in, and save under `docs/backlog/sprints/`:

```markdown
---
type: sprint
id: SPR-YYYY-MM-DD
title: "Sprint YYYY-MM-DD: Short title"
status: planned
owners: "agents"
created: YYYY-MM-DD
starts: YYYY-MM-DD
ends: YYYY-MM-DD
objective: "What success looks like by sprint end."
prd: "PRD-..."
epics: ["EPIC-.."]
stories: ["ST-..-.."]
adrs: ["ADR-...."]
---

## Objective

## Scope (committed stories)

- ST-XX-YY: title (link)

## Out of scope

## Decisions required (ADRs)

- ADR-XXXX: title (status proposed/accepted)

## Risks / edge cases

## Execution plan

## Demo checklist

## Verification checklist

- `pdm run docs-validate`
- Add story-specific verification steps (UI pages, runner flows, etc.)

## Notes / follow-ups
```
