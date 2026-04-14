---
type: pr
id: PR-0069
title: "Reagent Prep Chef — Fix SDS index missing in Docker (Riskbedömning)"
status: done
owners: "agents"
created: 2026-03-04
updated: 2026-03-04
stories:
  - "ST-20-02"
tags: ["curated-apps", "backend", "docker"]
adrs: ["ADR-0067"]
acceptance_criteria:
  - "When running the app via Docker Compose (dev), the web container can read `data/reagent_prep_chef/sds/index.json` and serve SDS markdown for a known `sds_ref`."
  - "When running the app via production Docker Compose (hemma), Riskbedömning can open SDS markdown in-app (no `SDS index not found` errors)."
  - "The Docker build includes the repo-owned SDS corpus (index + markdown) in the image, or mounts it explicitly in dev, without introducing runtime fetches."
---

## Problem

Riskbedömning depends on the repo-owned SDS index + markdown corpus (ADR-0067). In some Docker environments, the web
container fails with:

- `SDS index not found: data/reagent_prep_chef/sds/index.json`

This blocks “Öppna SDS” even when the corpus exists in the repo.

## Goal

Make the SDS corpus available to the web container in both dev and production Docker deployments.

## Non-goals

- No runtime SDS fetching.
- No PDF-first SDS serving requirement (markdown is the source of truth).

## Implementation plan

1. Ensure the Docker build context includes `data/` and that the production image contains:
   - `data/reagent_prep_chef/sds/index.json`
   - `data/reagent_prep_chef/sds/markdown/`
2. Preferred approach:
   - Bake the index + markdown into the `production` stage in `Dockerfile` (so both prod and `development` inherit it).
3. Optional dev DX improvement:
   - Mount `./data/reagent_prep_chef/sds/` into the dev web container so corpus changes are picked up without rebuild.
4. Rebuild + restart dev containers (`pdm run dev-stack build-start` or `pdm run dev-stack rebuild`).
5. Verify inside the running web container:
   - `test -f /app/data/reagent_prep_chef/sds/index.json`
   - `test -d /app/data/reagent_prep_chef/sds/markdown`
6. Manual UI verification:
   - Reagensberedning → Riskbedömning → “Öppna SDS” renders markdown in-app.

## Test plan

- Local: `pdm run docs-validate`
- Local Docker:
  - `pdm run dev-stack build-start`
  - `docker exec skriptoteket_web test -f /app/data/reagent_prep_chef/sds/index.json`
- Manual: open Riskbedömning and confirm “Öppna SDS” works for a known key.

## Rollback plan

- Revert Docker/compose changes.
- Rebuild images and restart containers.
