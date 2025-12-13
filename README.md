# Skriptoteket (Script Hub)

Teacher-first Script Hub for running curated, upload-based tools via a simple server-driven web UI.

## Quick start

- Install deps: `pdm install -G monorepo-tools`
- Start PostgreSQL (dev): `docker compose up -d db`
- Apply DB migrations: `pdm run db-upgrade`
- Bootstrap first superuser: `pdm run bootstrap-superuser`
- Run locally: `pdm run dev` (serves on `http://127.0.0.1:8000`, login required)
- Validate docs: `pdm run docs-validate`

## Documentation

Start at `docs/index.md` for the PRD, ADRs, and backlog.
