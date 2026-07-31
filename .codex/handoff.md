# Session Handoff

## Snapshot

- Date: 2026-07-31.
- Branch: `main` at `224729b2719f8c3d24a2d730fd1a1c72f62127ac`.
- `TASK-SKRIPT-REP-0003` is done: the current governed corpus uses the shared
  `repository-governance` contract and generated indexes.

## Status

- 396 current legacy records were migrated and 47 ordered parts retain
  oversized source material.
- All 764 terminal records remain byte-for-byte unchanged and historical.
- Current docs use `pdm run docs-validate`; the local validator is available
  only as `python -m scripts.historical_docs.validate_historical_docs` and is
  not bound to current hooks or PDM gates.
- Package-owned scaffold commands replace local current-document templates.
- Current documents contain no absolute Skriptoteket, former checkout, or
  skill-repository machine paths.
- Retained migration evidence is under central task context
  `TASK-SKRIPT-REP-0003/migration-session-v8`.

## How to Run

```bash
pdm run docs-validate
pdm run python -m scripts.historical_docs.validate_historical_docs
pdm run pytest tests/unit/scripts/test_historical_docs_validator.py -q
git diff --check
```

## Known Issues / Risks

- The shared pre-commit stack currently reports auxiliary binding drift for
  `publish-main` and `verify-main-publication`.
- Its targeted pytest hook passes `-q` to the routine wrapper at the wrong CLI
  layer.
- Git-aware migration pairing cannot represent profile-authorized omitted
  retired IDs for cross-type legacy migrations. Clean-main docs validation is
  green after this completed cutover.

## Next Steps

- Reassess `TASK-SKRIPT-REP-0004` against the current corpus before starting
  topology-derived quality adoption; it remains blocked and has no approved
  readiness decision.
- Keep product behavior, deployment, frontend catalog, and Hemma operations
  outside the completed corpus-migration task.
