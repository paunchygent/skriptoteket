---
type: adr
id: ADR-SKRIPT-0075
title: Klassrumskartan local export artifacts and conversion boundary
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: proposed
deciders:
- user-lead
retired_ids:
- ADR-0075
---

## Context


Klassrumskartan now has three distinct export families:

- seating PDF
- seating XLSX
- grouping XLSX/PDF

The XLSX lanes are already local, and grouping PDF is now proven as a local
WeasyPrint renderer owned by Skriptoteket. The remaining outlier is seating PDF,
which still depends on Sir Convert-a-Lot for HTML/CSS -> PDF conversion plus a
larger async lifecycle:

- external job submission
- webhook onboarding and callback dispatch
- callback/poll reconciliation
- external-job state recovery
- service auth and upstream dependency wiring

That complexity is not inherent to Klassrumskartan’s teacher-facing artifacts.
Seating PDF is, like grouping PDF, a renderer-owned document generated from a
controlled presentation model inside Skriptoteket.

Sir Convert-a-Lot remains valuable for a different class of problems:

- public/general-purpose conversion workloads
- cross-format conversion such as `pdf -> md`, `pdf -> docx`, `docx -> pdf`
- conversion surfaces exposed through Conversion Hub

Treating Klassrumskartan’s app-owned PDFs as if they belong to the same service
boundary has created an unnecessary distributed-system seam in the hottest
teacher export path.

## Decision


- Klassrumskartan app-owned export artifacts are rendered and finalized locally
  inside Skriptoteket.
- This rule applies to:
  - seating PDF
  - grouping PDF
  - seating XLSX
  - grouping XLSX
- Sir Convert-a-Lot remains the canonical external conversion service for:
  - Conversion Hub
  - class-list import PDF extraction
  - public/general-purpose `html/css -> pdf`
  - other cross-format conversion workloads
- Klassrumskartan must not depend on Sir Convert webhook orchestration,
  callback reconciliation, or upstream trusted-bundle policy for its own PDF
  export artifacts.

## Non-Decisions

No separate non-decisions is stated in the source.

## Consequences


- Seating PDF should migrate to the same local render/finalize model already
  used by grouping PDF.
- The seating-specific Sir Convert webhook/subscription path becomes removable
  after the cutover.
- Skriptoteket still needs a local ownership/download ledger for any flows that
  truly remain Sir Convert-backed, but Klassrumskartan PDFs are no longer one of
  those flows.
- ADR-SKRIPT-0066 remains valid for Conversion Hub and general conversion surfaces, but
  not as a blanket rule for curated app-owned export artifacts.

### Source: Migration direction


1. Record this boundary first in docs and backlog.
1. Migrate seating PDF export to a local renderer/finalizer path with no
   backwards-compatibility shims.
1. Remove the seating-specific Sir Convert webhook/subscription/reconciliation
   path after the local cutover.
1. Keep Sir Convert integration only where Skriptoteket is acting as a client of
   an external conversion service rather than as the owner of the export
   renderer.
