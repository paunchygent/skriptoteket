---
type: review
id: REV-PR-0277
title: "Review: PR-0277 share-link Teams preview thumbnails implementation"
status: pending
owners: "agents"
created: 2026-05-02
updated: 2026-05-02
reviewer: "lead-developer"
prs:
  - PR-0277
links:
  - EPIC-26
  - ST-26-07
  - REV-ST-26-07
  - ADR-0084
---

## TL;DR

`PR-0277` is ready for retained post-implementation review after the local
implementation of PostgreSQL-backed renderer-derived share preview assets,
Playwright thumbnail generation, active-only preview routes, social metadata,
the backfill command, and production-like BuildKit Chromium smoke. The reviewer
must not approve closeout until fresh Teams unfurl proof is added.

## Problem Statement

This review checks whether the implementation actually satisfies the approved
`ST-26-07`/`PR-0277` contract without weakening the `ST-26-06` public-by-token
HTML/CSS share page, public guest exception, lifecycle, or privacy boundaries.

## Proposed Solution

Review the implementation against the approved storage, renderer, route,
metadata, backfill, and production proof obligations. Verify that preview images
are generated only from immutable rendered share HTML/CSS, are served only for
active shares, and are used only for Teams/social unfurl metadata while the
opened URL remains the HTML/CSS share page.

## Mandatory Repomix Package

- Package:
  `.codex/repomix_packages/repomix-pr-0277-share-previews-post-impl-review.xml`
- Template: `code-review`
- Scope: changed implementation files, migration/model/repository surfaces,
  focused tests, Docker/runtime dependency changes, and governing docs.
- Package size: 29 files, about 89,884 tokens. `pdm.lock` and `docs/index.md`
  are intentionally excluded from the package because they dominated the token
  budget; inspect their local diffs directly when reviewing dependency and docs
  doorway changes.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0277-st-26-07-share-link-teams-preview-thumbnails.md` | Contract, implementation state, proof obligations | 8 min |
| `docs/backlog/stories/story-26-07-klassrumskartan-share-link-teams-preview-thumbnails.md` | Parent acceptance criteria and closeout state | 5 min |
| `migrations/versions/f8a2c6d4e9b1_add_share_preview_assets.py` | Preview asset schema and cascade behavior | 8 min |
| `src/skriptoteket/application/curated_apps/classroom_planner/handlers/share_artifacts.py` | Authenticated create/backfill/preview application flow | 12 min |
| `src/skriptoteket/application/curated_apps/classroom_planner/handlers/public_shares.py` | Public guest preview generation and transaction boundary | 8 min |
| `src/skriptoteket/infrastructure/curated_apps/apps/classroom_planner/share_preview_renderer.py` | Playwright adapter timeout, viewport, fitting, and concurrency | 12 min |
| `src/skriptoteket/web/routes/classroom_planner_share_pages.py` | Active-only image route and metadata injection | 12 min |
| `src/skriptoteket/infrastructure/repositories/classroom_planner_share_artifacts.py` | Atomic create, lifecycle, stale/backfill repository behavior | 12 min |
| `Dockerfile`, `pyproject.toml`, `pdm.lock` | Production Playwright/Chromium runtime setup | 8 min |
| Focused tests under `tests/unit` and `tests/integration` | Coverage for lifecycle, metadata, routes, and persistence | 15 min |

**Total estimated time:** ~100 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Store preview PNG bytes in PostgreSQL | Matches the approved `PR-0277` contract and keeps lifecycle tied to share artifacts | [ ] |
| Generate previews before share persistence | New share creation must fail cleanly with no committed share/preview rows if rendering fails | [ ] |
| Serve preview bytes only after active share resolution | Revoked, expired, missing, and purged shares must not leak retained thumbnails | [ ] |
| Keep JSON-LD to the exact `CreativeWork` allowlist | Avoids machine-readable roster, person, coordinate, placement, and group leakage | [ ] |
| Require BuildKit Chromium smoke and fresh Teams proof before done | Local tests do not prove the production browser runtime or Teams cache behavior | [ ] |

## Review Checklist

- [ ] Behavior matches `ST-26-07` and `PR-0277` acceptance criteria.
- [ ] Migration/schema assertions prove table shape, indexes, and cascade
  behavior.
- [ ] Repository tests prove create/get/backfill/stale hash/lifecycle behavior.
- [ ] Authenticated and public guest share creation fail without commits when
  preview generation fails.
- [ ] Preview image route handles active, stale slug/query, missing token,
  revoked, expired, and purged shares without leaking bytes.
- [ ] Metadata includes escaped OG/Twitter/JSON-LD fields and excludes roster
  arrays, `Person` objects, seat coordinates, placement relationships, group
  memberships, token hashes, revoke secrets, and hidden source payloads.
- [ ] Playwright adapter uses the approved 1200x630 output, 8 second timeout,
  bounded concurrency default, and rendered share HTML/CSS only.
- [ ] Production image setup uses BuildKit and does not require plain
  `docker build`; recorded smoke shows the web image can launch Chromium and
  render a 1200x630 PNG.
- [ ] Visual proof shows one complete seating thumbnail and one grouping
  thumbnail.
- [ ] Fresh Teams proof uses a never-before-posted production or production-like
  share URL.

## Verification

Run or verify recorded output for:

- `pdm run pytest -q tests/unit/application/apps/classroom_planner/test_share_artifacts.py tests/unit/application/apps/classroom_planner/test_public_shares.py tests/unit/web/apps/classroom_planner/test_share_pages.py tests/unit/infrastructure/curated_apps/apps/classroom_planner/test_share_renderer.py`
- `pdm run pytest -q tests/integration/infrastructure/repositories/test_classroom_planner_share_artifacts.py`
- `pdm run pytest -q tests/integration/database/test_classroom_planner_migration.py tests/integration/migration_schema_assertions.py --override-ini addopts=''`
- `pdm run pytest -q tests/unit/web/apps/classroom_planner/test_share_pages.py tests/integration/infrastructure/repositories/test_classroom_planner_public_guest_share_concurrency.py`
- `pdm run pytest -q tests/unit/application/apps/classroom_planner/test_authenticated_shares.py tests/unit/web/apps/classroom_planner/test_share_api.py tests/unit/application/apps/classroom_planner/test_public_shares.py tests/unit/web/test_public_apps_classroom_planner_shares.py`
- `pdm run alembic heads`
- `pdm run backfill-classroom-share-previews --help`
- `pdm run lint`
- `pdm run typecheck`
- `pdm run docs-validate`
- `git diff --check`
- `docker buildx build --progress=plain --target production --load -t skriptoteket-pr0277-preview-smoke .`
- `docker run --rm --env PYTHONPATH=src skriptoteket-pr0277-preview-smoke pdm run python -c "<Playwright preview renderer smoke>"`
  - Expected output includes:
    `container-playwright-smoke: ok size=1200x630 bytes=13329`
- Manual Teams proof with a never-before-posted production or production-like
  share URL.

## Review Feedback

**Reviewer:** `lead-developer`
**Date:** `2026-05-02`
**Verdict:** `pending`

### Required Changes

Pending review. Known proof gap before approval:

1. Fresh Microsoft Teams unfurl proof has not been run against a never-before-
   posted production or production-like share URL.

### Suggestions (Optional)

- Review the renderer fitting CSS with the generated PNG artifacts before
  approving; this is the easiest place for a subtle crop regression to hide.
- If the production Chromium install makes the web image too heavy or flaky,
  stop and reopen the runtime-architecture decision instead of approving a
  silent change.

### Decision Approvals

- [ ] PostgreSQL preview byte storage remains the right storage model.
- [ ] Playwright-backed adapter satisfies the production runtime contract.
- [ ] Active-only image route satisfies the public token/lifecycle contract.
- [ ] Metadata satisfies the conservative social preview and JSON-LD contract.
- [ ] BuildKit and Teams proof are sufficient for closeout.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `PR-0277`, `ST-26-07`, `EPIC-26` | Recorded local implementation state and outstanding proof before done. |
| 2 | `.codex/handoff.md` | Added current implementation state, verification, and next closeout steps. |
| 3 | `REV-PR-0277` | Created this retained post-implementation review request. |
