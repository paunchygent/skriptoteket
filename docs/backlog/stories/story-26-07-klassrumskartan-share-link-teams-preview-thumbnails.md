---
type: story
id: ST-26-07
title: "Klassrumskartan share-link Teams preview thumbnails"
status: in_progress
owners: "agents"
created: 2026-05-01
updated: 2026-06-14
epic: "EPIC-26"
dependencies:
  - "ST-26-06"
  - "PR-0274"
  - "PR-0273"
  - "PR-0276"
  - "ADR-0084"
acceptance_criteria:
  - "Given a new seating share link is created, when the URL is posted in Microsoft Teams, then Teams can render a large preview image that shows the full classroom arrangement derived from the immutable HTML/CSS share artifact."
  - "Given a new grouping share link is created, when the URL is posted in Microsoft Teams, then Teams can render a large preview image that shows the grouping artifact derived from the immutable HTML/CSS share artifact."
  - "Given a share page is opened directly, when the browser loads the share URL, then the primary artifact remains the server-rendered HTML/CSS page and does not become an image-only export."
  - "Given a preview image is generated, when its provenance is inspected, then it is mechanically derived from the same canonical rendered share artifact and presentation payload used by the public share page, not hand-authored or separately browser-supplied."
  - "Given Teams, Google Classroom, an LMS, or another crawler fetches the share page, when it reads metadata, then it sees complete escaped Open Graph/Twitter/schema.org metadata with `og:image`, image dimensions, canonical share URL, artifact title, and description."
  - "Given share links can contain class, room, group, and student names, when metadata or preview-image routes are fetched, then the public-by-token/no-owner-API/no-secret/no-indexing contract from `ST-26-06` remains intact."
  - "Given active share artifacts existed before this feature shipped, when the rollout strategy is applied, then those active links either receive backfilled preview metadata/images or use a documented lazy-generation path so active seating and grouping links are not left permanently text-only."
  - "Given a share is revoked, expired, purged, or missing, when its HTML page or preview image URL is fetched, then unavailable status, noindex headers, cache behavior, and leak-free responses remain deterministic and tested."
---

## Context

The `ST-26-06` share-link lane already makes grouping and seating plans
available as immutable public HTML/CSS artifacts. A production diagnostic on
2026-05-01 proved that Microsoft Teams reliably unfurls a seating share when
the page includes full Open Graph/Twitter/schema.org metadata and an
`og:image` PNG thumbnail derived from the actual share page. The diagnostic URL
kept the share page as HTML/CSS, generated the thumbnail mechanically from that
rendered page, and Teams showed the seating arrangement as expected.

This story turns that discovery into the supported product behavior for
Klassrumskartan share links. Retained review gate: `REV-ST-26-07`.

## Notes

- This is a follow-up to `ST-26-06`, not a replacement for the share artifact
  model.
- The opened URL must remain the real HTML/CSS share page.
- Preview images are link-preview thumbnails only; they do not replace
  rendered share HTML/CSS, print CSS, renderer provenance, or presentation
  hashes.
- Seating thumbnails should capture the full classroom map, not a viewport crop
  of only the top-left of the page.
- Grouping thumbnails should capture the grouping presentation in the same
  share-page visual language.
- Metadata should stay conservative and avoid structured student rosters or
  machine-readable placement/group membership lists beyond what is visible in
  the preview image and direct share page.
- Generated preview assets are stored in the share-preview asset table defined
  by `PR-0277`, are addressed through the public share token, and must follow
  the same active/revoked/expired/purged lifecycle as the share artifact.
- `PR-0279` is linked because shared-link seating label typography changes the
  immutable HTML/CSS that preview PNGs are generated from. Any renderer-version
  or output change in that slice must either regenerate/backfill active preview
  assets or prove existing stale-preview detection already forces fresh assets.
  `PR-0279` closed this contract on 2026-05-03: backfill now refreshes active
  old seating artifacts from `presentation_payload` before regenerating previews,
  and the Hemma production rerun after deploy returned `scanned=0 generated=0
  refreshed=0 failed=0`, so no active stale seating preview rows remained.
- The thumbnail runtime is a backend infrastructure adapter behind an
  application protocol. It must not depend on SPA hydration, browser-local
  state, owner-scoped APIs, or a logged-in user.
- Existing active links matter: the implementation slice must choose and prove
  either a bounded backfill path or lazy generation for active unrevoked shares.
- `REV-ST-26-07` is approved. The first implementation slice is `PR-0277`.
- `PR-0277` is implemented and deployed to Hemma production with PostgreSQL
  preview assets, Playwright-derived 1200x630 thumbnails, active-only preview
  routes, OG/Twitter/JSON-LD metadata, and the backfill command. Production
  backfill generated 3 preview assets and public metadata/image proof succeeded
  for the current production share URL. It remains `in_progress` until fresh
  Teams unfurl proof and retained post-implementation review are recorded.
  Production-like and on-host BuildKit Chromium smoke are recorded in `PR-0277`.
- `PR-0353` is the follow-up remediation task for the Node `[DEP0169]`
  warnings observed during the Hemma production Playwright browser install on
  2026-06-14. The task keeps the Playwright-backed thumbnail contract intact
  while removing the build warning or, if the supported upgrade path cannot do
  that, moving browser rendering behind an explicit renderer image/service
  boundary.
