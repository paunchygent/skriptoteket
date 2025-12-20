---
id: "060-docker-and-compose"
type: "implementation"
created: 2025-12-13
scope: "all"
---

# 060: Docker & Compose Standards

This repo uses Docker Compose for a local PostgreSQL-backed monolith and supports both **production-like** and
**development (hot-reload)** container workflows.

## 1. Compose Spec (Docker Compose v2)

- **REQUIRED**: Compose files **MUST NOT** include a top-level `version:` key. It is obsolete in Docker Compose v2.
- **REQUIRED**: Use the Docker Compose v2 CLI: `docker compose ...` (not the legacy `docker-compose` binary).
- **REQUIRED**: Use the canonical filenames `compose.yaml` (base) and `compose.dev.yaml` (dev overrides).
- **FORBIDDEN**: `docker-compose.yml` / `docker-compose.*` filenames.
- **REQUIRED**: Keep `compose.yaml` as the **base** (production-like) definition.
- **REQUIRED**: Keep `compose.dev.yaml` as **overrides only** (bind mounts, reload, dev-only env).
- **FORBIDDEN**: Deprecated Compose patterns like `links:`. Use service DNS names on the default network instead.

## 2. Canonical Dev Workflow (use PDM scripts)

Prefer the repo scripts over ad-hoc commands:

```bash
# Start dev stack (db + web with hot-reload)
pdm run dev-start

# Stop dev stack
pdm run dev-stop

# Rebuild + start (when deps or Dockerfile changes)
pdm run dev-build-start

# Clean rebuild (when you need to blow away cache/volumes)
pdm run dev-build-start-clean
```

## 3. Builds (no requirements.txt)

- **REQUIRED**: The `Dockerfile` **MUST** use PDM-based installs from `pyproject.toml`/`pdm.lock`.
- **FORBIDDEN**: Reintroducing `requirements.txt`-based installs (`pip install -r requirements.txt`).
- **REQUIRED**: Keep multi-stage targets:
  - `production`: runtime-only deps
  - `development`: adds QC/dev dependencies (ruff/mypy/pytest/etc.)
- **REQUIRED**: Use BuildKit for all image builds (Docker uses BuildKit by default; the legacy builder is deprecated).
- **FORBIDDEN**: Opting out of BuildKit (e.g. `DOCKER_BUILDKIT=0`) or using undocumented toggles (e.g.
  `COMPOSE_DOCKER_CLI_BUILD=0`).
- **REQUIRED**: Canonical build pattern:

```bash
docker compose build
```

## 4. Secrets & Environment

- **FORBIDDEN**: Hardcoding tokens, API keys, or credentials in the repo (including notebooks).
- **REQUIRED**: Inject secrets via environment variables (or a local `.env` that is git-ignored).
- **REQUIRED**: Compose files should reference env vars; never embed secret values.

## 5. Database Image & Locales

- **REQUIRED**: Use a Debian-based Postgres image (`postgres:16`) to avoid Alpine locale/tooling pitfalls.
- **REQUIRED**: If switching to an Alpine-based image in the future, install locale packages and set `LANG`/`LC_ALL` to a
  supported value (otherwise you will see `locale: not found` warnings).

## 6. Readiness

- **REQUIRED**: Healthchecks are allowed, but do not treat `depends_on` as a readiness guarantee.
- **REQUIRED**: Application startup **MUST** tolerate DB startup by retrying connections (or failing fast with a clear
  error).
