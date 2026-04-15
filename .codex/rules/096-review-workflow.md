---
id: "096-review-workflow"
type: "standards"
created: 2025-12-26
scope: "documentation"
---

# Target-Based Review Workflow

All proposed implementation packages and their governing ADRs must be reviewed before
implementation begins.

## Canonical review shape

- Save review docs under `docs/backlog/reviews/review-{primary-target-lower}-{short-name}.md`.
- Use one primary target per review doc.
- Match the review id to the primary target:
  - `REV-EPIC-XX` + `epic: EPIC-XX`
  - `REV-ST-XX-YY` + `stories: [ST-XX-YY, ...]`
  - `REV-PR-XXXX` + `prs: [PR-XXXX, ...]`
- If `stories:` or `prs:` lists multiple items, the first entry is the primary target and must
  match the review id.
- Supporting governed items may still appear in `stories:`, `prs:`, or `adrs:`, but only one
  primary target drives the filename and review id.
- Record governed ADRs in `adrs:` on the governing epic/story/PR review doc; standalone ADR-target
  review docs are not a current shape.
- Do not create new supplemental PR/story review ledgers inside epic review docs.

## Status flow

```text
pending -> approved | changes_requested | rejected
```

## Required review behavior

1. Review the target backlog item and its frozen decisions first.
2. Name concrete structural risks and disproven assumptions when requesting changes.
3. Keep review docs as retained decision records; never delete them.
4. Run `pdm run docs-validate` after review status or workflow-doc changes.

## Retired shapes

- Sprint docs are legacy records, not a current planning shape.
- New planning should use PRD, ADR, epic, story, PR, and target-based review docs instead.

## References

- Workflow reference: `docs/reference/ref-review-workflow.md`
- Review template: `docs/templates/template-review.md`
- Docs contract: `docs/_meta/docs-contract.yaml`
