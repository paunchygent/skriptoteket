---
type: epic
id: EPIC-20
title: "Curated app: Reagent Prep Chef"
status: proposed
owners: "agents"
created: 2026-01-26
updated: 2026-03-04
outcome: "Teachers can generate a deterministic solution prep sheet (hydrates/purity/dilution) with curated safety output, via a first-class curated app shipped from the repo."
dependencies: ["ADR-0022", "ADR-0023", "ADR-0024", "ADR-0067"]
---

## Scope

- Ship the **Reagent Prep Chef** as a curated app (ADR-0023) rendered via Tool UI contract v2 (ADR-0022).
- Bespoke-required SPA view (no generic curated app renderer fallback for this app).
- Strict input validation (Pydantic v2) with teacher-friendly, recoverable UX (no “guessing”).
- Hydrate-aware formula normalization and molar-mass calculation.
- Curated hazards lookup (repo-owned data) with explicit “Consult SDS” fallback on misses.
- Backend-hosted **offline SDS corpus** (markdown-first) for curated chemicals (ADR-0067).
- Printable export (PDF artifact) and audit-friendly structured outputs (typed outputs + JSON payload).

## Out of scope

- Chemical heuristics or reaction prediction (exothermicity, incompatibilities, etc.).
- Multi-reagent “recipes” or synthesis instructions.
- Automated SDS discovery/fetching at runtime (PubChem scraping, provider registries, PDF signal extraction).
- Any direct external SDS URLs in the SPA (SDS must be backend-hosted).

## Stories

- [ST-20-01: Curated app — Reagent Prep Chef (v1)](../stories/story-20-01-curated-app-reagent-prep-chef.md)
- [ST-20-02: Curated app — Reagent Prep Chef — Riskbedömning + dokumentation (v1)](../stories/story-20-02-curated-app-reagent-prep-chef-risk-assessment.md)
- [ST-20-03: Curated app — Reagent Prep Chef — SDS corpus gap fill (ADR-0067)](../stories/story-20-03-curated-app-reagent-prep-chef-sds-corpus.md)

## Risks

- **False confidence:** mitigate by curated-only safety and explicit SDS fallback.
- **Input ambiguity:** mitigate by strict formula normalization (separator-only) and clear UI copy.
- **Precision/rounding confusion:** mitigate by deterministic rounding rules + warnings for too-small masses.

## Dependencies

- ADR-0022 (Tool UI contract v2)
- ADR-0023 (Curated apps registry + execution)
- ADR-0024 (Tool sessions + ui_payload persistence)
- `docs/reference/ref-curated-app-reagent-prep-chef.md`
