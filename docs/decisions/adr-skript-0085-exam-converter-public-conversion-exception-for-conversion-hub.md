---
type: adr
id: ADR-SKRIPT-0085
title: Exam Converter public conversion exception for Conversion Hub
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: accepted
links:
  governing:
  - ADR-SKRIPT-0079
  - ADR-SKRIPT-0066
  - EPIC-SKRIPT-21
  - ST-SKRIPT-21-03
deciders:
- user-lead
retired_ids:
- ADR-0085
---

## Context

### Source: Context

`ADR-SKRIPT-0079` keeps curated apps fail-closed for public access unless each app
declares an explicit public profile. Its initial matrix leaves
`documents.conversion_hub` authenticated-only because anonymous upload,
conversion compute, and artifact delivery carry meaningful abuse and cost
risk.

`ST-SKRIPT-21-03` now separates two Conversion Hub product needs:

- general conversion workloads, which remain authenticated; and
- a narrow Exam Converter lane where a teacher can perform a one-time
  DigiExam/Exam.net migration without signing in.

`PR-0318` has already approved the authenticated Exam Converter adapter through
the HuleEdu Gateway `/sir-convert/v2/convert/...` edge. Opening the public lane
must not weaken that authenticated boundary, expose arbitrary Conversion Hub
routes, or silently convert the whole app to public access.

## Decision

### Source: Decision

This ADR authorizes one narrow exception to `ADR-SKRIPT-0079`:
`documents.conversion_hub` may expose a public `exam_converter` lane while
general Conversion Hub remains authenticated-only.

The registry/profile contract must express this as a scoped public capability,
not as an unqualified app-wide public profile:

```yaml
public_capabilities:
  - scope: exam_converter
    profile: public_browser_runtime
```

The exception contract is:

- `documents.conversion_hub` remains authenticated for general conversion
  workloads, route discovery, arbitrary file conversion, batch conversion, job
  recovery, Vault/MyFiles handoff, and owner-scoped history.
- Only the `exam_converter` public capability may use
  `public_browser_runtime`.
- The public Exam Converter lane may accept `.dxe`, optional sanitized graded
  result PDF, target selection, progress polling, direct artifact downloads,
  and teacher-visible failure/manual-follow-up states.
- Public browser state may track only the active transient upload, job,
  artifact handles, validation outcomes, and correlation id display.
- Public server state must be transient, TTL-bound, and not owner-scoped.
- Public artifacts are direct-download only and must not create Vault/MyFiles
  records, local user-file records, account history, recoverable guest jobs, or
  owner-scoped conversion job rows before login.
- Public helper/API routes must live under a dedicated public namespace, ignore
  ambient account authority, and behave the same whether or not a browser has
  an authenticated session cookie.
- Public routes must enforce MIME/type validation, upload-size caps,
  request-time budgets, concurrency limits, rate limits, structured reason
  codes, short artifact TTLs, and privacy-safe telemetry before calling the
  conversion backend.
- Public routes must not expose Sir Convert service credentials, direct
  `convert.hule.education` browser calls, raw workdirs, arbitrary Sir Convert
  route selection, or authenticated HuleEdu Gateway identity context minting.
- Public bootstrap for `documents.conversion_hub` must expose only the scoped
  `exam_converter` capability and must not expose the general authenticated
  Conversion Hub route list.
- The authenticated Exam Converter lane remains governed by `PR-0318` and the
  HuleEdu Gateway cutover contract; this ADR does not move authenticated
  artifact persistence into the public lane.

## Non-Decisions

The source records no separate non-decision section; adjacent boundaries remain part of the selected decision.

## Consequences

### Source: Consequences

- `ADR-SKRIPT-0079` remains accepted and historically accurate, but its
  `documents.conversion_hub` matrix entry is amended by this ADR for the
  bounded Exam Converter lane.
- The registry model needs a scoped public-capability contract in addition to
  the existing app-wide `public_access_profile`.
- `supports_public_access` and public bootstrap behavior must distinguish
  app-wide public access from scoped public capabilities.
- The public host and backend public API must be scope-aware so
  `/public/apps/documents.conversion_hub` cannot become a general public
  Conversion Hub shell by accident.
- `PR-0319` should freeze the registry/profile contract, public route
  namespace, abuse-control taxonomy, and public bootstrap contract before
  runtime conversion implementation starts.
- The runtime public conversion implementation remains a later slice after
  reviewers can verify the scoped capability boundary.
