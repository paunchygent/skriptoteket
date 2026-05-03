---
type: pr
id: PR-0277
title: "ST-26-07 share-link Teams preview thumbnails"
status: in_progress
owners: "agents"
created: 2026-05-01
updated: 2026-05-02
stories:
  - "ST-26-07"
tags: ["backend", "renderer", "klassrumskartan", "sharing", "social-preview"]
dependencies:
  - "ST-26-06"
  - "PR-0276"
  - "REV-ST-26-07"
acceptance_criteria:
  - "Given authenticated or public guest seating share creation succeeds, when the artifact is persisted, then a 1200x630 link-preview image is generated from the immutable rendered seating HTML/CSS and the full classroom map is visible in the image."
  - "Given authenticated or public guest grouping share creation succeeds, when the artifact is persisted, then a 1200x630 link-preview image is generated from the immutable rendered grouping HTML/CSS and the grouping cards are visible in the image."
  - "Given any active share page is fetched, when a crawler reads the head, then the page includes escaped `og:title`, `og:description`, `og:type`, `og:site_name`, `og:url`, `og:image`, `og:image:secure_url`, `og:image:type`, `og:image:width`, `og:image:height`, `og:image:alt`, Twitter large-card tags, and conservative schema.org JSON-LD."
  - "Given a crawler fetches the preview image URL, when the share is active, then it receives a public image response without authentication, owner-scoped APIs, secrets, token hashes, revoke secrets, or SPA fallback."
  - "Given a share is revoked, expired, purged, or missing, when the preview image URL is fetched, then the route returns deterministic unavailable semantics and does not leak a retained thumbnail."
  - "Given active shares created before this slice exist, when the rollout runs, then active unrevoked grouping and seating shares receive preview metadata/images via the `backfill-classroom-share-previews` command."
  - "Given hostile class, room, group, fixture, or student text exists, when metadata and preview-image generation run, then HTML, Open Graph, JSON-LD, URL, and image-alt contexts are escaped or bounded and covered by tests."
  - "Given the feature is verified, when a never-before-posted production or production-like share URL is posted in Microsoft Teams, then Teams renders the generated preview thumbnail rather than only a text-only card."
---

## Problem

Share pages are good HTML/CSS artifacts once opened, but Microsoft Teams link
previews are unreliable without a fetchable preview image and fuller crawler
metadata. A one-off production diagnostic using a real `SA24D`/`G20` seating
share proved that Teams renders the expected seating arrangement when the page
adds complete Open Graph/Twitter/schema.org metadata and points `og:image` at a
PNG thumbnail generated from the rendered share page.

## Goal

Make renderer-derived link-preview thumbnails a supported feature of all active
Klassrumskartan grouping and seating share links while preserving the existing
public-by-token HTML/CSS share artifact contract.

## Non-goals

- No Teams app, bot, message extension, or Adaptive Card integration.
- No live draft sharing or collaborative editing.
- No replacement of the HTML/CSS share page with an image-only artifact.
- No machine-readable structured roster, placement, or group-membership data in
  JSON-LD.
- No reliance on SPA hydration, browser-local state, owner-scoped APIs, or a
  logged-in user to render previews.

## Implementation plan

1. Add a share-preview asset contract for immutable generated thumbnails:
   - table: `classroom_planner_share_preview_assets`
   - columns: `share_id` primary key / `ON DELETE CASCADE` foreign key to
     `classroom_planner_share_artifacts.id`, `content_type`, `width`,
     `height`, `image_bytes`, `preview_content_hash`,
     `source_content_hash`, `presentation_hash`, `renderer_version`,
     `generated_at`, and `updated_at`
   - one preview asset per share artifact; `content_type` is `image/png`,
     `width=1200`, and `height=630` for this slice
   - `preview_content_hash` is the SHA-256 hash of `image_bytes`
   - `source_content_hash` must equal the share artifact `content_hash` used
     to produce the thumbnail
   - `presentation_hash` and `renderer_version` must match the share artifact
     so old thumbnails can be identified after renderer changes
2. Add the public image route
   `GET /share/classroom/{public_token}/preview.png`, with optional
   `?v=<preview_content_hash>` in generated metadata URLs. The route resolves
   by token hash, checks active/not-revoked/not-expired state, and returns the
   PNG only for active shares. Missing, revoked, expired, or purged shares must
   not return retained image bytes.
3. Add `ClassroomPlannerSharePreviewRendererProtocol` and a Playwright-backed
   infrastructure adapter. The adapter accepts rendered share HTML/CSS plus the
   share kind, renders with a 1200x630 viewport, returns PNG bytes, and has no
   dependency on SPA hydration, owner APIs, cookies, or a browser user session.
4. Define runtime limits:
   - hard timeout: 8 seconds per thumbnail render
   - bounded concurrency: default `CLASSROOM_SHARE_PREVIEW_MAX_CONCURRENCY=2`
     in the web process
   - failure semantics: if preview generation fails during new share creation,
     the share create request fails with a controlled service-unavailable
     domain error and no share artifact/preview asset row is committed
   - backfill failure semantics: the backfill command records the failed share
     id and continues unless `--fail-fast` is supplied
5. Update production runtime dependencies deliberately:
   - move/add the Playwright Python package to the production dependency set or
     an explicitly installed production group
   - install the Chromium browser binary and required OS dependencies in the
     BuildKit Dockerfile path
   - add a production-like Docker smoke proving the web container can render a
     fixture share thumbnail through the adapter
6. Generate thumbnails from the already-rendered share HTML/CSS after share
   render succeeds and before the share create response is considered complete.
   Use the same rendered artifact for authenticated and public guest shares.
7. Make seating thumbnail capture full classroom geometry rather than the
   visible browser viewport. Make grouping thumbnail capture the complete
   grouping presentation or a deterministic top-level card composition.
8. Extend share-page head metadata to include the full crawler/social preview
   contract, including absolute `og:url` and `og:image` URLs derived from
   `PUBLIC_APP_BASE_URL`. Use versioned/hash-based `og:image` URLs so new
   thumbnails get a distinct fetch URL when the preview bytes change.
9. Use exactly this JSON-LD shape:
   - `@context: "https://schema.org"`
   - `@type: "CreativeWork"`
   - `name`
   - `description`
   - `url`
   - `image`
   - `thumbnailUrl`
   - `inLanguage: "sv-SE"`
   - `dateCreated`
   - `isPartOf: {"@type": "WebSite", "name": "Skriptoteket"}`
   - `provider: {"@type": "Organization", "name": "Skriptoteket"}`
   Do not include student/member arrays, `Person` objects, `about`,
   `mentions`, `hasPart`, seat coordinates, placement relationships, group
   memberships, roster JSON, or hidden source payloads in JSON-LD.
10. Add `pdm run backfill-classroom-share-previews` for active pre-existing
   shares. The command must generate preview rows only for active, unrevoked,
   unexpired grouping and seating shares whose `source_content_hash` is absent
   or stale. Keep revoked, expired, or purged shares unavailable.
11. Keep purge/lifecycle behavior aligned so share HTML/CSS and preview assets
   are removed or made inaccessible together.
12. Document Teams cache expectations in the implementation notes: Microsoft
   documents Teams link unfurling results as cached for 30 minutes, so manual
   proof must use a never-before-posted URL and old Teams messages may not
   refresh immediately after backfill or regenerated thumbnails.

## Test plan

- Renderer/metadata unit tests for seating and grouping share HTML:
  complete OG/Twitter/schema.org tags, escaped hostile text, canonical URL,
  image dimensions, no token hashes, no revoke secrets, and no owner ids.
- Preview generation tests proving images are derived from rendered share
  HTML/CSS and use the intended dimensions, content hash, renderer version,
  presentation hash, and source content hash.
- Route tests for active, stale slug, revoked, expired, missing-token, and
  purged preview-image fetches.
- Backfill command tests for active legacy shares, stale source hashes, revoked
  shares, expired shares, purged shares, and `--fail-fast` behavior.
- Focused share creation tests for authenticated and public guest seating and
  grouping paths.
- Production-like Docker smoke proving the configured browser binary is
  installed and can render a fixture thumbnail in the web image.
- Visual proof with real generated seating and grouping thumbnails, including
  a full-classroom seating thumbnail and a grouping card thumbnail.
- Production or production-like manual Teams proof using never-posted share
  URLs that a new seating share and a new grouping share unfurl with the
  generated thumbnail; record that already-posted Teams cards may remain cached
  for roughly 30 minutes.
- `pdm run lint`
- `pdm run typecheck`
- Focused backend tests for the touched share renderer/routes.
- `pdm run docs-validate`
- `git diff --check`

## Implementation State (2026-05-02)

Implemented and deployed to Hemma production at commit
`2bae81a615a169aa70e916695cfaf467f5dbc96a`, pending retained
post-implementation review and fresh Teams unfurl proof before this PR is
marked `done`.

- Added the PostgreSQL-backed `classroom_planner_share_preview_assets` table
  with preview/source hashes, renderer provenance, dimensions, PNG bytes, and
  share-artifact cascade linkage.
- Added `ClassroomPlannerSharePreviewRendererProtocol`, a bounded
  Playwright-backed infrastructure adapter, DI wiring, runtime settings, and
  `pdm run backfill-classroom-share-previews`.
- Authenticated and public guest share creation now generate preview assets from
  finalized rendered share HTML/CSS before persistence; preview failure maps to
  a controlled service-unavailable error and does not commit share/preview rows.
- Added `GET /share/classroom/{public_token}/preview.png?v=<hash>` and active
  lifecycle checks so missing, revoked, expired, stale, or purged shares do not
  leak retained preview bytes.
- Share pages now emit escaped OG/Twitter metadata and the strict
  `CreativeWork` JSON-LD allowlist only when a fresh preview asset exists.
- Visual proof artifacts were generated at
  `.artifacts/pr-0277-share-previews/grouping-preview.png` and
  `.artifacts/pr-0277-share-previews/seating-preview.png`; both are 1200x630 and
  render the complete grouping/seating artifacts.
- Hemma production deployment uses the dedicated
  `pdm run hemma-deploy-share-previews` command, which runs the BuildKit web
  image build, Alembic migration, active-share preview backfill, container
  Playwright PNG smoke, and web health check.
- Hemma Docker Snap revision `3505` / Docker `29.3.1` failed BuildKit/runc
  startup with `ld.so` relocation assertions; the host was recovered by
  reverting the Docker snap to revision `3377` / Docker `28.4.0` before rerun.

Verification run:

- `pdm run pytest -q tests/unit/application/apps/classroom_planner/test_share_artifacts.py tests/unit/application/apps/classroom_planner/test_public_shares.py tests/unit/web/apps/classroom_planner/test_share_pages.py tests/unit/infrastructure/curated_apps/apps/classroom_planner/test_share_renderer.py`
- `pdm run pytest -q tests/integration/infrastructure/repositories/test_classroom_planner_share_artifacts.py`
- `pdm run pytest -q tests/integration/database/test_classroom_planner_migration.py tests/integration/migration_schema_assertions.py --override-ini addopts=''`
- `pdm run pytest -q tests/unit/web/apps/classroom_planner/test_share_pages.py tests/integration/infrastructure/repositories/test_classroom_planner_public_guest_share_concurrency.py`
- `pdm run pytest -q tests/unit/application/apps/classroom_planner/test_authenticated_shares.py tests/unit/web/apps/classroom_planner/test_share_api.py tests/unit/application/apps/classroom_planner/test_public_shares.py tests/unit/web/test_public_apps_classroom_planner_shares.py`
- `pdm run mypy --config-file pyproject.toml src/skriptoteket/application/curated_apps/classroom_planner src/skriptoteket/infrastructure/curated_apps/apps/classroom_planner src/skriptoteket/infrastructure/repositories/classroom_planner_share_artifacts.py src/skriptoteket/web/routes/classroom_planner_share_pages.py src/skriptoteket/protocols/classroom_planner_shares.py`
- `pdm run alembic heads`
- `pdm run backfill-classroom-share-previews --help`
- `pdm run lint`
- `pdm run typecheck`
- `pdm run docs-validate`
- `git diff --check`
- `docker buildx build --progress=plain --target production --load -t skriptoteket-pr0277-preview-smoke .`
- `docker run --rm --env PYTHONPATH=src skriptoteket-pr0277-preview-smoke pdm run python -c "<Playwright preview renderer smoke>"`
  - Output: `container-playwright-smoke: ok size=1200x630 bytes=13329`
- `pdm run hemma-deploy-share-previews`
  - Remote log:
    `/home/paunchygent/apps/skriptoteket/.artifacts/hemma-deploy-20260502-122221.log`
  - Output included: `Backfill classroom share previews complete: scanned=3
    generated=3 failed=0 failed_share_ids=`, `container-playwright-smoke: ok
    size=1200x630 bytes=15141`, and web health `200`.
- Production public metadata proof against the fresh production link returned
  `200`, OG/Twitter/JSON-LD metadata, and an `image/png` preview at
  1200x630 with `preview.png?v=sha256:...`.

Outstanding proof:

- Manual Microsoft Teams proof still requires a never-before-posted production
  or production-like share URL after deployment/backfill.

## Rollback plan

Disable thumbnail generation and omit `og:image` metadata for newly created
shares while leaving existing HTML/CSS share pages and token read routes
available. If generated preview assets are stored separately, purge or detach
only those assets without revoking the underlying share artifacts.
