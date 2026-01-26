---
type: epic
id: EPIC-20
title: "Curated app: Reagent Prep Chef"
status: proposed
owners: "agents"
created: 2026-01-26
outcome: "Teachers can generate a deterministic solution prep sheet (hydrates/purity/dilution) with curated safety output, via a first-class curated app shipped from the repo."
---

## Scope

- Ship the **Reagent Prep Chef** as a curated app (ADR-0023) rendered via Tool UI contract v2 (ADR-0022).
- Bespoke-required SPA view (no generic curated app renderer fallback for this app).
- Strict input validation (Pydantic v2) with teacher-friendly, recoverable UX (no “guessing”).
- Hydrate-aware formula normalization and molar-mass calculation.
- Curated hazards lookup (repo-owned data) with explicit “Consult SDS” fallback on misses.
- Printable export (PDF artifact) and audit-friendly structured outputs (typed outputs + JSON payload).

## Out of scope

- Chemical heuristics or reaction prediction (exothermicity, incompatibilities, etc.).
- Multi-reagent “recipes” or synthesis instructions.
- Online SDS fetching or external chemistry APIs.

## Stories

- [ST-20-01: Curated app — Reagent Prep Chef (v1)](../stories/story-20-01-curated-app-reagent-prep-chef.md)

## Risks

- **False confidence:** mitigate by curated-only safety and explicit SDS fallback.
- **Input ambiguity:** mitigate by strict formula normalization (separator-only) and clear UI copy.
- **Precision/rounding confusion:** mitigate by deterministic rounding rules + warnings for too-small masses.

## Dependencies

- ADR-0022 (Tool UI contract v2)
- ADR-0023 (Curated apps registry + execution)
- ADR-0024 (Tool sessions + ui_payload persistence)
- `docs/reference/ref-curated-app-reagent-prep-chef.md`
