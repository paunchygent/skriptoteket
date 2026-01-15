---
name: local-devops
description: Local development + build/devops workflow for Skriptoteket (FastAPI + Vue/Vite) using PDM. Use when setting up or troubleshooting local dev (`pdm install`, `.env`, `pdm run dev`, frontend proxy/logs), or when changing dependency groups/extras and Dockerfile install commands to avoid PDM group/--prod pitfalls.
---

# Local development (canonical)

## Hard rules

- Do **not** run `docker compose up` in this repo unless the user explicitly requests it.
- Run the backend via `pdm run dev` (host uvicorn), not via Compose.

## Quick start checklist (backend)

1) Ensure `.env` exists (copy from `.env.example`).
2) Ensure tool artifacts directory exists and is configured:
   - Set `ARTIFACTS_ROOT=/tmp/skriptoteket/artifacts` in `.env`
   - Run `mkdir -p /tmp/skriptoteket/artifacts`
3) Install Python deps:
   - `pdm install -G monorepo-tools`
   - If you need browser tooling locally: `pdm install -G monorepo-tools -G dev`
4) Run backend:
   - `pdm run dev`

## Quick start checklist (frontend SPA)

- Install deps: `pdm run fe-install`
- Run SPA dev server: `pdm run fe-dev`
- When debugging API calls, check backend logs from the `pdm run dev` terminal (Vite proxies to `127.0.0.1:8000`).

## Verification (local)

- Health: `curl -sSf http://127.0.0.1:8000/healthz >/dev/null`
- Tokenizer availability (Devstral/Tekken): `pdm run pytest -q tests/unit/infrastructure/llm/test_token_counter_resolver.py`

# PDM groups/extras (avoid rebuild surprises)

## Mental model

- `[project].dependencies` is **always installed** (prod + local).
- `[dependency-groups]` is for **dev-only groups** (lint/test/dev tooling). These are selected with `pdm install -G <group>` (and are incompatible with `--prod`).
- `[project.optional-dependencies]` is for **extras** (runtime feature toggles). These are selected with `pdm install --prod -G <extra>` in production-like installs.

## Known pitfall

- `pdm install --prod -G <dependency-group>` fails with: `--prod is not allowed with dev groups`.
  - Fix by moving that group to `[project.optional-dependencies]` if it must be selectable in prod builds, or by removing `--prod` if it’s dev-only.
