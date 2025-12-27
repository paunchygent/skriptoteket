# Skriptoteket (Script Hub)

Teacher-first Script Hub for running curated, upload-based tools. FastAPI backend + Vue/Vite SPA frontend (migration in progress; production still uses SSR/HTMX until cutover).

## Quick start

- Install deps: `pdm install -G monorepo-tools`
- Start PostgreSQL (dev): `docker compose up -d db`
- Apply DB migrations: `pdm run db-upgrade`
- Bootstrap first superuser: `pdm run bootstrap-superuser`
- Run locally: `pdm run dev` (serves on `http://127.0.0.1:8000`, login required)
- Validate docs: `pdm run docs-validate`

## Frontend (SPA)

- Install frontend deps: `pdm run fe-install`
- Run SPA dev server: `pdm run fe-dev`

## Documentation

Start at `docs/index.md` for the PRD, ADRs, and backlog.
