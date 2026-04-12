# Skriptoteket

Skriptoteket is a **teacher-first Script Hub** for municipalities and school organizations: teachers log in, browse a
catalog of curated tools, upload files, run the tool, and download results.

It’s designed to be **self-hosted** and adapted to local IT constraints (on‑prem, private cloud, intranet/VPN-only,
central logging, approved SMTP relays, strict data retention).

## Current status (what’s in this repo)

- **UI:** Full **Vue 3 + Vite SPA** served by the FastAPI backend (SPA history fallback in the backend).
- **Backend:** **FastAPI** monolith with Clean Architecture / DDD layers and protocol-first DI (Dishka).
- **Database:** **PostgreSQL** (users, identity projections, tools, versions, runs, audit-ish event streams).
- **Tool execution:** Tools run as **ephemeral sibling Docker containers** (runner image) via the Docker API.
  Runs can be **queue-backed** (recommended; default) or **synchronous** (`RUNNER_QUEUE_ENABLED=false`). When queueing
  is enabled, the execution worker must be running.
  - `network_mode=none`, `cap_drop=ALL`, read-only root, tmpfs for `/tmp`, resource limits (CPU/mem/pids/timeouts).
- **UI contract:** Tools return a typed UI payload (**contract v2**) with `outputs[]`, optional `next_actions[]`, and
  optional persisted `state`.
- **Curated apps:** Owner-authored “apps” can be served alongside tools (not managed via the tool editor workflow).
- **Storage:** Outputs/artifacts + ephemeral session files + editor sandbox snapshots are stored on disk under
  `ARTIFACTS_ROOT` (with retention cleanup commands).
- **Identity:** HuleEdu/Hule Education owns browser login, shared session, CSRF, lifecycle ceremonies, and Gateway-signed
  downstream identity context. Skriptoteket keeps product identity projections, profiles, and roles local.

## Using Skriptoteket (end users)

1. **Log in** through the HuleEdu-owned Skriptoteket ceremony, or complete the HuleEdu-hosted
   Skriptoteket standalone registration/lifecycle flow when needed.
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

Tool runs are **queue-backed by default**, so run the execution worker too (or set `RUNNER_QUEUE_ENABLED=false` in
`.env` to force synchronous execution):

```bash
# Terminal C
pdm run run-execution-worker
```

Open the SPA at `http://127.0.0.1:5173`.

For the realm-aware shared-auth proof lane, do not point local callbacks at public
`https://api.hule.education`. Use the dedicated local/non-production HuleEdu Gateway lane from
HuleEdu `TASK-0325`: Skriptoteket stays on `http://localhost:5173`, HuleEdu login UI uses
`http://localhost:5174`, Gateway runs on `http://localhost:8080`, and protected Skriptoteket API
traffic routes through Gateway at `/api/...` with `VITE_DEV_PROXY_TARGET=http://localhost:8080`.
The separate 127 proof uses `http://127.0.0.1:5173`, `http://127.0.0.1:5174`, and
`http://127.0.0.1:8080` consistently. The backend verifier consumes only the local Gateway public
signing key mounted or exported from HuleEdu.

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

1) **Database**: configure `DATABASE_URL` and ensure backups + PITR align with your policies.

2) **Artifacts / retention**: mount a persistent directory/volume and set `ARTIFACTS_ROOT`.

- Schedule retention jobs (cron/systemd timers) using:
  - `pdm run artifacts-prune`
  - `pdm run cleanup-session-files`
  - `pdm run cleanup-sandbox-snapshots`

1) **Email**: configure `EMAIL_PROVIDER=smtp` and point to your municipal SMTP relay.

2) **Runner security**: decide how you want to host tool execution.

- Same host: mount `/var/run/docker.sock` into the web container.
- Separate host: point the web service at a dedicated runner Docker Engine using `DOCKER_HOST` (protect it with TLS and
  network policy; it’s equivalent to root on that host).

1) **Observability**:

- Logs: set `LOG_FORMAT=json` and ship stdout/stderr to your log platform.
- Metrics: scrape `/metrics`.
- Health: probe `/healthz`.
- Tracing (optional): set `OTEL_TRACING_ENABLED=true` and `OTEL_EXPORTER_OTLP_ENDPOINT=...`.

1) **AI features (optional)**:

- For air‑gapped environments: set `LLM_*_ENABLED=false`.
- For self-hosted inference: point `LLM_*_BASE_URL` / `LLM_*_FALLBACK_BASE_URL` to your OpenAI‑compatible gateways
  (llama.cpp, etc.). The default dev/prod examples use local `Devstral-Small-2-24B` and external OpenAI models
  (`gpt-5-nano` for completions; `gpt-5.2` for chat/chat-ops).
- Remote providers are gated by `AI_REMOTE_PROVIDERS_ENABLED` and per-user opt-in (`profile.allow_remote_fallback=true`;
  NULL counts as deny).
- Avoid remote providers unless you have a clear DPIA/legal basis for sending prompt data to external services.

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

# Start (web + worker; DB is expected to be provided externally in compose.prod.yaml)
docker compose -f compose.prod.yaml up -d --build

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
- **Identity/shared auth**: browser auth is HuleEdu-owned. Skriptoteket verifies Gateway-signed
  `InternalIdentityContextV1`, resolves local identity projections, and applies local roles. Do not
  reintroduce app-local browser sessions, CSRF, password collection, or browser-minted identity
  headers.
- **Email provider**: protocols in `src/skriptoteket/protocols/email.py`, implementations in
  `src/skriptoteket/infrastructure/email/`.
- **Tool execution policy** (limits/sandbox): env settings in `src/skriptoteket/config.py` (CPU/mem/pids/timeouts,
  retention).
- **Registration and password lifecycle policy**: browser lifecycle surfaces hand off to HuleEdu
  Gateway/Identity with `app=skriptoteket` and the selected product identity realm. Skriptoteket
  owns the resulting local projection/profile/RBAC behavior, not the browser credential ceremony.
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
- Release notes: `docs/releases/`
- Operations runbooks: `docs/runbooks/`
- Useful runbooks: `docs/runbooks/runbook-user-management.md`, `docs/runbooks/runbook-runner-image.md`,
  `docs/runbooks/runbook-observability.md`
- Key ADRs: `docs/adr/adr-0004-clean-architecture-ddd-di.md`, `docs/adr/adr-0013-execution-ephemeral-docker.md`,
  `docs/adr/adr-0027-full-vue-vite-spa.md`
