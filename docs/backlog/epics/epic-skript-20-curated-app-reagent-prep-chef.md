---
type: epic
id: EPIC-SKRIPT-20
title: 'Curated app: Reagent Prep Chef'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: proposed
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
outcome: Teachers can generate a deterministic solution prep sheet (hydrates/purity/dilution)
  with curated safety output, via a first-class curated app shipped from the repo.
retired_ids:
- EPIC-20
---

## Scope


- Ship the **Reagent Prep Chef** as a curated app (ADR-0023) rendered via Tool UI contract v2 (ADR-0022).
- Bespoke-required SPA view (no generic curated app renderer fallback for this app).
- Strict input validation (Pydantic v2) with teacher-friendly, recoverable UX (no “guessing”).
- Hydrate-aware formula normalization and molar-mass calculation.
- Curated hazards lookup (repo-owned data) with explicit “Consult SDS” fallback on misses.
- Backend-hosted **offline SDS corpus** (markdown-first) for curated chemicals (ADR-0067).
- Printable export (PDF artifact) and audit-friendly structured outputs (typed outputs + JSON payload).

### Source: Out of scope


- Chemical heuristics or reaction prediction (exothermicity, incompatibilities, etc.).
- Multi-reagent “recipes” or synthesis instructions.
- Automated SDS discovery/fetching at runtime (PubChem scraping, provider registries, PDF signal extraction).
- Any direct external SDS URLs in the SPA (SDS must be backend-hosted).

## Epic Contract

No separate epic contract is stated in the source.

## ADR Coverage

No separate adr coverage is stated in the source.

## Contract Inputs

No separate contract inputs is stated in the source.

## Stories


- [ST-20-01: Curated app — Reagent Prep Chef (v1)](../stories/story-20-01-curated-app-reagent-prep-chef.md)
- [ST-SKRIPT-20-02: Curated app — Reagent Prep Chef — Riskbedömning + dokumentation (v1)](../stories/st-skript-20-02-curated-app-reagent-prep-chef-riskbed-mning-dokumentation-v1.md)
- [ST-20-03: Curated app — Reagent Prep Chef — SDS corpus gap fill (ADR-0067)](../stories/story-20-03-curated-app-reagent-prep-chef-sds-corpus.md)

## Epic Verification Plan

No separate epic verification plan is stated in the source.

## Exceptions And Follow-Ups


- ADR-0022 (Tool UI contract v2)
- ADR-0023 (Curated apps registry + execution)
- ADR-SKRIPT-0024 (Tool sessions + ui_payload persistence)
- `docs/reference/ref-curated-app-reagent-prep-chef.md`

## Risks


- **False confidence:** mitigate by curated-only safety and explicit SDS fallback.
- **Input ambiguity:** mitigate by strict formula normalization (separator-only) and clear UI copy.
- **Precision/rounding confusion:** mitigate by deterministic rounding rules + warnings for too-small masses.

## Notes

No separate notes is stated in the source.

## Decision And Assumption Ledger

| source | semantic | carried_forward | Source material is retained in the sections above. | source |

## Plan Document Review

No review evidence is recorded in this migration candidate; the frontmatter gate remains authoritative.

## Epic Closeout Review

No review evidence is recorded in this migration candidate; the frontmatter gate remains authoritative.
