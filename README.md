# Skriptoteket

Skriptoteket is a **teacher-first Script Hub** for municipalities and school organizations: teachers log in, browse a
catalog of curated tools, upload files, run the tool, and download results.

It’s designed to be **self-hosted** and adapted to local IT constraints (on‑prem, private cloud, intranet/VPN-only,
central logging, approved SMTP relays, strict data retention).

## Current status (what’s in this repo)

- **UI:** Full **Vue 3 + Vite SPA** served by the FastAPI backend (SPA history fallback in the backend).
- **Backend:** **FastAPI** monolith with Clean Architecture / DDD layers and protocol-first DI (Dishka).
- **Database:** **PostgreSQL** (users, sessions, tools, versions, runs, audit-ish event streams).
- **Tool execution:** Tools run as **ephemeral sibling Docker containers** (runner image) via the Docker API:
  - `network_mode=none`, `cap_drop=ALL`, read-only root, tmpfs for `/tmp`, resource limits (CPU/mem/pids/timeouts).
- **Storage:** Outputs/artifacts + ephemeral session files + editor sandbox snapshots are stored on disk under
  `ARTIFACTS_ROOT` (with retention cleanup commands).
- **Identity:** Local accounts (email+password) with email verification; future SSO via federation is planned (roles remain
  local).

## Using Skriptoteket (end users)

1. **Register** (or get an account provisioned) and verify your email.
2. Browse the **catalog** by profession/category and open a tool.
3. Upload files / fill in fields and **run** the tool.
4. View results and **download artifacts** (PDF/DOCX/etc. depending on the tool).

Roles:

| Role | Intended use (current enforcement) |
|------|-----------------------------------|
| `user` | Browse and run tools, manage profile/favorites |
| `contributor` | `user` + author tools (editor + sandbox), submit drafts for review, submit suggestions |
| `admin` | `contributor` + review suggestions, publish/depublish tools, publish/request-changes on versions |
| `superuser` | `admin` + user administration and version rollback |

## Quick start (local development)

Prereqs: Python **3.13+**, PDM, Docker, Node **22+** + pnpm.

1) Install deps

```bash
pdm install -G monorepo-tools
pdm run fe-install
```

2) Configure environment

- Copy `.env.example` → `.env` and adjust values as needed.
- Create a local artifacts dir (required for tool execution):

```bash
mkdir -p /tmp/skriptoteket/artifacts
```

3) Start PostgreSQL + migrate

```bash
docker compose up -d db
pdm run db-upgrade
```

4) Bootstrap the first superuser (local dev)

```bash
pdm run bootstrap-superuser
```

5) Run backend + SPA (two terminals)

```bash
# Terminal A
pdm run dev

# Terminal B (SPA dev server; proxies /api to the backend)
pdm run fe-dev
```

Open the SPA at `http://127.0.0.1:5173`.

## Deployment guide for municipal IT

Skriptoteket is intended to run as a small “core” with optional add-ons. The simplest production shape is:

- **Web**: one container (FastAPI + embedded SPA)
- **PostgreSQL**: managed service or your own HA setup
- **Docker Engine access**: for runner containers (can be on the same host or a dedicated runner host via `DOCKER_HOST`)
- **Persistent volume**: for `ARTIFACTS_ROOT`
- Optional: Prometheus/Grafana/Jaeger/Loki, self-hosted LLM endpoints (OpenAI-compatible)

### Minimum production checklist

1) **DNS + TLS**: put the web service behind your standard reverse proxy / ingress. Set:

- `COOKIE_SECURE=true`
- `EMAIL_VERIFICATION_BASE_URL=https://<your-domain>`

2) **Database**: configure `DATABASE_URL` and ensure backups + PITR align with your policies.

3) **Artifacts / retention**: mount a persistent directory/volume and set `ARTIFACTS_ROOT`.

- Schedule retention jobs (cron/systemd timers) using:
  - `pdm run artifacts-prune`
  - `pdm run cleanup-session-files`
  - `pdm run cleanup-sandbox-snapshots`

4) **Email**: configure `EMAIL_PROVIDER=smtp` and point to your municipal SMTP relay.

5) **Runner security**: decide how you want to host tool execution.

- Same host: mount `/var/run/docker.sock` into the web container.
- Separate host: point the web service at a dedicated runner Docker Engine using `DOCKER_HOST` (protect it with TLS and
  network policy; it’s equivalent to root on that host).

6) **Observability**:

- Logs: set `LOG_FORMAT=json` and ship stdout/stderr to your log platform.
- Metrics: scrape `/metrics`.
- Health: probe `/healthz`.
- Tracing (optional): set `OTEL_TRACING_ENABLED=true` and `OTEL_EXPORTER_OTLP_ENDPOINT=...`.

7) **AI features (optional)**:

- For air‑gapped environments: set `LLM_*_ENABLED=false`.
- For self-hosted inference: point `LLM_*_BASE_URL` to your OpenAI‑compatible gateway (llama.cpp, etc.).
- Avoid remote fallback unless you have a clear DPIA/legal basis for sending prompt data to external providers.

### Production via Docker Compose (starting point)

This repo includes a production-oriented Docker setup:

- `Dockerfile` builds the web image and embeds the SPA build output.
- `Dockerfile.runner` builds the runner image used for tool execution.
- `compose.prod.yaml` is a *home-server* deployment file, but works well as a template for municipal infrastructure.

Typical flow:

```bash
# Configure
cp .env.example.prod .env

# Build images
docker compose -f compose.prod.yaml build web
docker compose -f compose.prod.yaml --profile build-only build runner

# Start (web only; DB is expected to be provided externally in compose.prod.yaml)
docker compose -f compose.prod.yaml up -d web

# Migrate DB schema
docker compose -f compose.prod.yaml exec -T web pdm run db-upgrade

# Bootstrap first admin (Superuser)
docker compose -f compose.prod.yaml exec -T web pdm run bootstrap-superuser
```

If you don’t use the repo’s home-server conventions (external `hule-network`, external `shared-postgres`, nginx-proxy
labels), create your own `compose.<municipality>.yaml` by copying `compose.prod.yaml` and adjusting:

- `DATABASE_URL` (point to your PostgreSQL)
- networks/ingress labels to match your platform
- volume mount for `ARTIFACTS_ROOT`

### Adapting Skriptoteket to your municipality

Common adaptations and where they live in the codebase:

- **Professions & categories (taxonomy)**: seeded by migrations (see `migrations/versions/0002_catalog_taxonomy.py`).
- **Identity/SSO**: identity is protocol-driven (`src/skriptoteket/protocols/identity.py`). You can add an external IdP
  integration in `src/skriptoteket/infrastructure/` and wire it in `src/skriptoteket/di/` (roles remain local).
- **Email provider**: protocols in `src/skriptoteket/protocols/email.py`, implementations in
  `src/skriptoteket/infrastructure/email/`.
- **Tool execution policy** (limits/sandbox): env settings in `src/skriptoteket/config.py` (CPU/mem/pids/timeouts,
  retention).
- **Registration policy**: SPA route in `frontend/apps/skriptoteket/src/views/RegisterView.vue`, API endpoint in
  `src/skriptoteket/web/api/v1/auth.py`, and the core rules in
  `src/skriptoteket/application/identity/handlers/register_user.py` (use this to disable self-registration or enforce a
  domain allowlist).
- **Branding/UI**: SPA in `frontend/apps/skriptoteket`; tokens/CSS live under
  `src/skriptoteket/web/static/css/` and `frontend/apps/skriptoteket/src/assets/`.
- **Default tools**: add scripts in `src/skriptoteket/script_bank/` and seed them with `pdm run seed-script-bank` (see
  `docs/runbooks/runbook-script-bank-seeding.md`).

## Key commands

- Run (backend): `pdm run dev` / `pdm run serve`
- Run (SPA): `pdm run fe-dev` / `pdm run fe-build`
- Generate SPA API types from OpenAPI: `pdm run fe-gen-api-types`
- DB migrate: `pdm run db-upgrade`
- Quality: `pdm run format` / `pdm run lint` / `pdm run typecheck` / `pdm run test`
- Docs contract: `pdm run docs-validate`

## Documentation

- Start here: `docs/index.md`
- Operations runbooks: `docs/runbooks/`
- Useful runbooks: `docs/runbooks/runbook-user-management.md`, `docs/runbooks/runbook-runner-image.md`,
  `docs/runbooks/runbook-observability.md`
- Key ADRs: `docs/adr/adr-0004-clean-architecture-ddd-di.md`, `docs/adr/adr-0013-execution-ephemeral-docker.md`,
  `docs/adr/adr-0027-full-vue-vite-spa.md`
