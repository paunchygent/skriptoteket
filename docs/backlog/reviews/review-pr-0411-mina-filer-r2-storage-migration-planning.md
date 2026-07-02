---
type: review
id: REV-PR-0411
title: "Review: PR-0411 Mina filer R2 storage migration planning"
status: approved
owners: "agents"
created: 2026-07-02
updated: 2026-07-02
reviewer: "ruthless_review_agent"
prs:
  - PR-0411
links:
  - ST-14-39
  - ADR-0088
  - REF-cloudflare-r2-skriptoteket-file-storage-migration-pre-runbook
---

# Review: PR-0411 Mina Filer R2 Storage Migration Planning

## TL;DR

Approved on rereview. The source story now requires migration manifests to use
opaque File Service object references instead of target R2 object keys, so the
planning package consistently preserves the HuleEdu File Service boundary and
keeps direct R2 identity out of Skriptoteket implementation authority.

## Problem Statement

Cloudflare R2 can satisfy S3-compatible object operations, but Skriptoteket's
risk is product-level: identity, owner-scoped metadata, `vault:*` refs,
protected file actions, and migration safety must stay coherent across local,
dev, and production.

## Proposed Solution

Review the planning package as a decision gate, not as an implementation diff.
Approval requires explicit answers for the Skriptoteket-to-HuleEdu File Service
consumer contract, catalog/lifecycle ownership split, metadata, config,
Docker/runtime, migration, rollback, delete/retention, observability, and proof
before any storage code or production env sync starts.

## Artifacts To Review

| Artifact | Focus | Reviewed |
|---|---|---|
| `docs/adr/adr-0088-cloudflare-r2-storage-boundary-for-mina-filer-and-filerefs.md` | Decision, consequences, and open questions | yes |
| `docs/reference/ref-cloudflare-r2-skriptoteket-file-storage-migration-pre-runbook.md` | Architecture, config, Docker, migration phases, stop conditions | yes |
| `docs/backlog/stories/story-14-39-cloudflare-r2-backed-mina-filer-storage-migration.md` | Story contract and non-goals | yes |
| `docs/backlog/prs/pr-0411-st-14-39-mina-filer-r2-storage-migration-planning.md` | Slice acceptance, tests, and rollback requirements | yes |

## Key Decisions

| Decision | Required before approval | Status |
|---|---|---|
| Storage adapter owner | HuleEdu File Service client; no Skriptoteket direct R2 adapter | closed |
| Catalog/list owner | Skriptoteket keeps v1 `Mina filer` catalog/list; File Service list optional | closed |
| Lifecycle owner | HuleEdu File Service owns init, finalize, metadata, download, delete | closed |
| Upload v2 semantic boundary | no essay, BOS, assessment, or batch semantics leak into Skriptoteket | closed |
| Manifest object identity | migration authority must use opaque File Service object references, not target R2 object keys | closed |
| Storage metadata | DB columns, opaque File Service object ref, checksum, lifecycle mirror | retained implementation blocker |
| Runtime config | exact File Service settings, secret-source labels, Docker readiness | retained implementation blocker |
| Migration safety | dry-run, copy, checksum proof, dual-read, cutover, rollback, cleanup | retained implementation blocker |
| Product proof | protected route tests and live shared-auth browser proof | retained implementation blocker |

## Review Checklist

- [x] Adapter choice is explicit: HuleEdu File Service client, not direct R2.
- [x] Skriptoteket catalog/list authority remains local for v1.
- [x] HuleEdu File Service lifecycle ownership covers init, finalize, metadata,
  download, and delete.
- [x] Upload v2 essay, BOS, assessment, and batch semantics are forbidden in
  the Skriptoteket consumer.
- [x] Manifest object identity uses opaque File Service object references, not
  target R2 object keys.
- [x] Storage metadata, object identity, checksum, lifecycle, and quota behavior
  are retained as blockers for the later implementation package.
- [x] Delete, restore, purge, and missing-object states are retained as blockers
  for the later implementation package.
- [x] HuleEdu File Service config surfaces are retained as blockers for the
  later implementation package.
- [x] Docker services, readiness checks, and local test backend are retained as
  blockers for the later implementation package.
- [x] Migration manifest, dry-run, copy, checksum verification, dual-read,
  cutover, rollback, and destructive cleanup gates are retained as blockers for
  the later implementation package.
- [x] Document Converter saved-source batch behavior remains refs-only,
  owner-scoped, ordered, and all-or-nothing.
- [x] Tests and live browser proof requirements cover the real protected routes.
- [x] Logs, metrics, retained artifacts, and handoff text must redact credentials,
  raw object keys, and signed URLs.

## Findings

No open findings on rereview.

### RESOLVED HIGH: Story acceptance still authorizes target object keys in the migration manifest

- File: `docs/backlog/stories/story-14-39-cloudflare-r2-backed-mina-filer-storage-migration.md:15`
- Category: docs-only direct-R2 authority leakage.
- Problem: The acceptance criterion requires migration proof to include
  "target object keys". The ADR and pre-runbook otherwise require Skriptoteket
  to consume HuleEdu File Service, store opaque File Service object references,
  and keep R2 bucket/key values as infrastructure details rather than product or
  domain concepts.
- Why it matters: Story acceptance criteria are implementation authority. A
  future implementer can satisfy the story by exposing or persisting raw R2
  object-key identity in migration manifests, retained proof, or domain-shaped
  metadata even though the validated cross-product contract says Skriptoteket
  should operate through File Service object references.
- Required fix: Replace "target object keys" with "opaque File Service object
  references" or another product-neutral File Service identifier, and align any
  manifest/redaction language so raw R2 bucket/key values remain internal to
  HuleEdu File Service unless a later reviewed tranche explicitly authorizes
  infra-only operator evidence.
- Proof required: rerun
  `rg -n "target object keys|raw R2|direct R2|R2 adapter|Upload v2|essay|BOS|assessment|batch" docs/adr/adr-0088-cloudflare-r2-storage-boundary-for-mina-filer-and-filerefs.md docs/reference/ref-cloudflare-r2-skriptoteket-file-storage-migration-pre-runbook.md docs/backlog/stories/story-14-39-cloudflare-r2-backed-mina-filer-storage-migration.md docs/backlog/prs/pr-0411-st-14-39-mina-filer-r2-storage-migration-planning.md`
  and confirm only forbidden/stop-condition language remains for direct-R2 and
  Upload v2 terms.
- Rereview result: resolved. The story acceptance criterion now names "opaque
  File Service object references", and the proof search no longer returns
  `target object keys`.

## Review Feedback

The main alignment is otherwise correct:

- `ADR-0088` states that Skriptoteket consumes HuleEdu File Service for object
  lifecycle and must not add a Skriptoteket direct R2 adapter in this tranche.
- Skriptoteket keeps `Mina filer` catalog/list authority for v1, with File
  Service list optional until a later reviewed tranche moves browse/catalog
  authority.
- HuleEdu File Service owns init, finalize, canonical metadata, download byte
  retrieval, and final object delete.
- Browser clients are barred from direct R2 credentials, raw object keys, raw
  R2 URLs, and signed-URL leakage in retained evidence.
- HuleEdu Upload v2 essay, BOS, assessment, and batch semantics are consistently
  forbidden for the Skriptoteket consumer contract.

The remaining open metadata, runtime-config, migration, rollback, delete, and
live-proof questions are acceptable as blockers for later implementation only if
the docs keep them out of "decide during implementation" territory, as the ADR
and PR currently state.

## Changes Made

External retained review updated this review artifact only. The implementation
pass changed
`docs/backlog/stories/story-14-39-cloudflare-r2-backed-mina-filer-storage-migration.md`
to replace `target object keys` with `opaque File Service object references`.
No product code was modified by the reviewer.

## Validation

- `sed -n '1,260p' AGENTS.md`
- `sed -n '1,260p' docs/index.md`
- `sed -n '1,260p' docs/_meta/docs-contract.yaml`
- `sed -n '1,260p' .codex/rules/096-review-workflow.md`
- `rg -n "direct R2|R2 adapter|R2 credentials|raw R2|raw object|object key|object keys|Upload v2|essay|BOS|assessment|batch|File Service list|catalog/list|catalog authority|object lifecycle|init|finalize|download|delete" docs/adr/adr-0088-cloudflare-r2-storage-boundary-for-mina-filer-and-filerefs.md docs/reference/ref-cloudflare-r2-skriptoteket-file-storage-migration-pre-runbook.md docs/backlog/stories/story-14-39-cloudflare-r2-backed-mina-filer-storage-migration.md docs/backlog/prs/pr-0411-st-14-39-mina-filer-r2-storage-migration-planning.md docs/backlog/reviews/review-pr-0411-mina-filer-r2-storage-migration-planning.md`
- `rg -n "target object keys|raw R2|direct R2|R2 adapter|Upload v2|essay|BOS|assessment|batch" docs/adr/adr-0088-cloudflare-r2-storage-boundary-for-mina-filer-and-filerefs.md docs/reference/ref-cloudflare-r2-skriptoteket-file-storage-migration-pre-runbook.md docs/backlog/stories/story-14-39-cloudflare-r2-backed-mina-filer-storage-migration.md docs/backlog/prs/pr-0411-st-14-39-mina-filer-r2-storage-migration-planning.md`
- `rg -n "opaque File Service object references|target object keys" docs/backlog/stories/story-14-39-cloudflare-r2-backed-mina-filer-storage-migration.md docs/adr/adr-0088-cloudflare-r2-storage-boundary-for-mina-filer-and-filerefs.md docs/reference/ref-cloudflare-r2-skriptoteket-file-storage-migration-pre-runbook.md docs/backlog/prs/pr-0411-st-14-39-mina-filer-r2-storage-migration-planning.md`
- `pdm run docs-validate` passed after this retained rereview update.
- `pdm run handoff-validate` passed after this retained rereview update.
- `git diff --check` passed after this retained rereview update.

## Decision

approved
