---
id: "096-review-workflow"
type: "standards"
created: 2025-12-26
scope: "documentation"
---

# Review Workflow for EPICs and Stories

All proposed implementations **MUST** be reviewed before work begins. This rule defines the mandatory review workflow.

## When Reviews Are Required

| Artifact | Trigger | Reviewer |
|----------|---------|----------|
| ADR | Status = `proposed` | Lead developer or architect |
| EPIC | Status = `proposed` | Lead developer |
| Stories | Part of proposed EPIC | Reviewed with EPIC |

## Review Document Location

```
docs/backlog/reviews/review-epic-{XX}-{short-name}.md
```

## Review Status Flow

```
pending → approved | changes_requested | rejected
```

## Reviewer Responsibilities

For each artifact, evaluate:

1. **Alignment**: Does this solve the stated problem?
2. **Architecture**: Does it follow DDD/Clean Architecture patterns?
3. **Scope**: Is scope appropriate (not too broad, not too narrow)?
4. **Testability**: Are acceptance criteria testable and complete?
5. **Risk**: Are risks identified and mitigations reasonable?

## Post-Review Actions

### If Approved

1. Update review doc status to `approved`
2. Update ADR status: `proposed` → `accepted`
3. Update EPIC status: `proposed` → `active`
4. Stories remain `ready`
5. Review doc is **retained** as decision record

### If Changes Requested

1. Update review doc status to `changes_requested`
2. Author addresses required changes in artifacts
3. Author documents changes in review doc
4. Author requests re-review
5. Reviewer verifies and updates verdict

### If Rejected

1. Update review doc status to `rejected`
2. Document rejection reason
3. ADRs remain `proposed` or move to `deprecated`
4. EPIC moves to `dropped`
5. Review doc is **retained** as decision record

## Key Rules

- **REQUIRED**: Never start implementation on proposed EPICs without approved review
- **REQUIRED**: All key decisions must be explicitly approved in review
- **FORBIDDEN**: Deleting review docs (they serve as decision records)
- **REQUIRED**: Run `pdm run docs-validate` after review status changes

## References

- Full workflow: `docs/reference/ref-review-workflow.md`
- Template: `docs/templates/template-review.md`
- Contract: `docs/_meta/docs-contract.yaml` (review type definition)
