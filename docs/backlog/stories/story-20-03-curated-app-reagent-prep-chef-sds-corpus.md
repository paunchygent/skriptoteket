---
type: story
id: ST-20-03
title: "Curated app: Reagent Prep Chef — SDS corpus gap fill (markdown-first)"
status: ready
owners: "agents"
created: 2026-03-04
epic: "EPIC-20"
dependencies: ["ADR-0067", "ST-20-02"]
acceptance_criteria:
  - "Given the SDS corpus index is regenerated, when `data/reagent_prep_chef/sds/gaps.md` is produced, then `Missing SDS markdown` is empty (coverage for all hazards keys)."
  - "Given the SDS corpus is updated, when the teacher opens Riskbedömning and clicks 'Öppna SDS' for any curated hazard, then the app shows SDS markdown in-app (no external fetch)."
  - "Given repo storage policy, when git status is checked, then SDS markdown + index/gaps are tracked in git and SDS PDFs remain out-of-git (gitignored)."
ui_impact: "No (data curation; UI already supports SDS markdown rendering)"
data_impact: "Yes (repo-owned SDS markdown corpus + deterministic index)"
---

## Context

We have committed to ADR-0067: SDS is a **markdown-first, offline, repo-owned** corpus for Reagensberedning (Reagent
Prep Chef).

The app UX already supports opening SDS markdown in-app, but the corpus still has coverage gaps for some curated hazards
keys. This story closes those gaps so teachers reliably get SDS access for the curated chemicals we ship.

## Scope

- Fill remaining SDS markdown gaps for the hazards dataset keys (see `data/reagent_prep_chef/sds/gaps.md`).
- Keep the corpus Swedish-first (no language detection in the product).
- Keep PDFs outside git (optional), but keep markdown/index/gaps committed.

## Non-goals

- No runtime SDS fetching from external sources.
- No SDS-derived signal extraction (density/CLP/heuristics). The SDS documents are the product artifact.
