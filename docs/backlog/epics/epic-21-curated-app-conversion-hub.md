---
type: epic
id: EPIC-21
title: "Curated app: Conversion Hub (Sir Convert-a-Lot v2)"
status: active
owners: "agents"
created: 2026-03-01
outcome: "Skriptoteket provides a first-class conversion hub UI (batch + preview) that routes all supported conversions through Sir Convert-a-Lot v2, with no production dependence on the legacy html-to-pdf-preview tool script."
---

## Scope

- Add a **Conversion Hub** curated app (bespoke-required) that exposes a complete UI for the set of
  conversions supported by Sir Convert-a-Lot v2.
- Support batch conversions (multiple files) and a single-PDF preview UX that still uses the normal
  v2 job lifecycle (submit/poll/download).
- Surface v2 PDF layout presets (for example A5/A4/A3 and portrait/landscape) in the UI for relevant
  outputs.
- Migrate tests and remove production reliance on `html-to-pdf-preview`.

## Out of scope

- No new conversion engines inside Skriptoteket (no WeasyPrint/Pandoc pipelines in Skriptoteket
  beyond what's required for tests unrelated to conversion hub).
- No partial/legacy shims for `html-to-pdf-preview` once the curated app exists: callers/tests are
  updated to the new surface.

## Stories (ordered)

- [ ] 1. [ST-21-01: Curated app: Conversion Hub (v1)](../stories/story-21-01-curated-app-conversion-hub-v1.md)
- [ ] 2. [ST-21-02: Migration: retire html-to-pdf-preview + update tests](../stories/story-21-02-migrate-off-html-to-pdf-preview-and-retire-tool.md)

## Risks

- External dependency risk (Sir Convert-a-Lot availability/latency):
  mitigate with timeouts, clear UI progress, and deterministic error surfaces.
- Artifact naming / vault integration drift:
  mitigate by asserting on "PDF exists and is valid" rather than hardcoded filenames in E2E.
- Over-scoping in one PR:
  mitigate via PR-sized tasks with strict ordering (PR-0063..).

## Dependencies

- ADR-0066 (this epic's conversion strategy decision)
- Existing curated apps platform: ADR-0022, ADR-0023, ADR-0024

## Implementation Summary (as of 2026-03-01)

- PR-0063 (docs planning scaffold): done
- PR-0064 (backend v2 client + curated app API surface): done
- PR-0065 (SPA bespoke UI): next
- PR-0066 (migrate tests + retire html-to-pdf-preview): pending
