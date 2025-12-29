---
type: runbook
id: RUN-home-server
title: "Runbook: Home Server Operations"
status: active
owners: "olof"
created: 2025-12-16
updated: 2025-12-29
system: "hemma.hule.education"
---

Operations guide for the home server hosting Skriptoteket and future HuleEdu services.

## Setup

### Server Access (SSH)

```bash
# Remote access (via dynamic DNS)
ssh hemma

# Local network access
ssh hemma-local
```

### Repo + Compose Layout (Production)

- App repo: `~/apps/skriptoteket/`
- Production compose: `compose.prod.yaml` (uses `shared-postgres` on `hule-network`)
- Observability stack: `compose.observability.yaml`
- Development compose: `compose.yaml` (local postgres only)

**Critical**: Production uses `compose.prod.yaml`, NOT `compose.yaml`.

### Command Patterns (Use These)

```bash
# 1) Compose commands (from repo root)
ssh hemma "cd ~/apps/skriptoteket && docker compose -f compose.prod.yaml <command>"

# 2) Run CLI inside web container (compose)
ssh hemma "cd ~/apps/skriptoteket && docker compose -f compose.prod.yaml exec -T -e PYTHONPATH=/app/src web pdm run python -m skriptoteket.cli <command>"

# 3) Direct docker exec (used by systemd timers)
ssh hemma "/snap/bin/docker exec -e PYTHONPATH=/app/src skriptoteket-web pdm run python -m skriptoteket.cli <command>"
```

### Architecture Overview

```text
┌─────────────────────────────────────────────────────────────┐
│                        Internet                              │
└────────────────────────────┬────────────────────────────────┘
                             │ :80/:443 (HTTP/HTTPS)
┌────────────────────────────▼────────────────────────────────┐
│  nginx-proxy (nginxproxy/nginx-proxy:1.6)                    │
│  - Auto-discovers containers via VIRTUAL_HOST env var        │
│  - SSL termination (certs from acme-companion)               │
│  - Routes: skriptoteket.hule.education → skriptoteket-web   │
│            grafana.hemma.hule.education → grafana           │
│            prometheus.hemma.hule.education → prometheus     │
├──────────────────────────────────────────────────────────────┤
│  acme-companion (nginxproxy/acme-companion:2.4)              │
│  - Auto-generates Let's Encrypt certificates                 │
│  - Listens for LETSENCRYPT_HOST env vars on containers       │
│  - Auto-renews before expiry                                 │
└────────────────────────────┬────────────────────────────────┘
                             │
    ┌────────────────────────┼────────────────────────┐
    │                        │                        │
    ▼                        ▼                        ▼
┌─────────────┐      ┌─────────────┐         ┌─────────────┐
│ skriptoteket │      │   grafana   │         │ prometheus  │
│     :8000    │      │    :3000    │         │    :9090    │
└─────────────┘      └─────────────┘         └─────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  shared-postgres (hule-network)                              │
│  - PostgreSQL 16 (shared across services)                   │
│  - Data in persistent volume                                │
└─────────────────────────────────────────────────────────────┘
```

### Add a New Service to nginx-proxy

Add these env vars to the service and expose its internal port:

```yaml
environment:
  - VIRTUAL_HOST=myservice.hemma.hule.education
  - VIRTUAL_PORT=8080  # Internal port the service listens on
  - LETSENCRYPT_HOST=myservice.hemma.hule.education
expose:
  - "8080"
```

Then add a DNS A record for `myservice.hemma` pointing to `83.252.61.217` (or your current IP).
The acme-companion will automatically generate SSL certificates.

### Infrastructure Layout

```text
~/apps/skriptoteket/           # Application repository
  compose.prod.yaml            # Production compose (uses shared-postgres)
  compose.yaml                 # Development compose (local postgres)
  compose.observability.yaml   # Observability stack (independent lifecycle)
  Dockerfile                   # Web app image
  Dockerfile.runner            # Script runner image
  .env                         # Local environment (never commit)

~/infrastructure/              # Shared infrastructure (nginx-proxy + acme-companion + postgres)
  docker-compose.yml           # nginx-proxy, acme-companion, shared-postgres
  .env                         # POSTGRES_ADMIN_PASSWORD, LETSENCRYPT_EMAIL
  postgres/
    init/                      # DB init scripts (create databases/users)
```

### Infrastructure Compose Services

| Service | Image | Purpose |
|---------|-------|---------|
| `nginx-proxy` | `nginxproxy/nginx-proxy:1.6` | Auto-configuring reverse proxy |
| `acme-companion` | `nginxproxy/acme-companion:2.4` | Auto SSL certificate management |
| `shared-postgres` | `postgres:16-alpine` | Shared PostgreSQL for all services |

## Daily Ops

### Quick Status Check

```bash
# All containers
ssh hemma "docker ps"

# Skriptoteket + core services
ssh hemma "docker ps | grep -E 'skriptoteket|nginx|postgres'"
```

### View Logs

```bash
# Web application logs
ssh hemma "docker logs -f skriptoteket-web"

# Nginx access logs
ssh hemma "docker logs -f nginx-proxy"

# Database logs (check for query errors)
ssh hemma "docker logs -f shared-postgres"
```

**Tip**: Skriptoteket logs are structured (JSON in production) and support `X-Correlation-ID` for cross-request
debugging. See [runbook-observability.md](runbook-observability.md).

### Restart Services

```bash
# Restart Skriptoteket (preserves network connections)
ssh hemma "cd ~/apps/skriptoteket && docker compose -f compose.prod.yaml restart"

# Restart observability stack
ssh hemma "cd ~/apps/skriptoteket && docker compose -f compose.observability.yaml restart"

# nginx-proxy auto-reloads when containers change (no manual reload needed)
```

### Disk Space / Session Cleanup

Session files are stored in `ARTIFACTS_ROOT/sessions/` (prod: `/app/.artifacts/sessions/`). An hourly systemd timer
runs TTL cleanup automatically.

```bash
# Check timer status
ssh hemma "systemctl list-timers | grep skriptoteket"

# View cleanup logs
ssh hemma "journalctl -u skriptoteket-session-files-cleanup.service -n 50 --no-pager"

# Manual trigger (if needed)
ssh hemma "sudo systemctl start skriptoteket-session-files-cleanup.service"
```

Manual cleanup commands:

```bash
# TTL-based cleanup (same as timer runs)
ssh hemma "/snap/bin/docker exec -e PYTHONPATH=/app/src skriptoteket-web pdm run python -m skriptoteket.cli cleanup-session-files"

# DANGER: Delete ALL session files (requires --yes)
ssh hemma "/snap/bin/docker exec -e PYTHONPATH=/app/src skriptoteket-web pdm run python -m skriptoteket.cli clear-all-session-files --yes"
```

### Sandbox Snapshot Cleanup (DB)

Sandbox preview snapshots are stored in PostgreSQL with a TTL (24h). Cleanup is scheduled server-side via systemd.

Unit files:

```ini
# /etc/systemd/system/skriptoteket-sandbox-snapshots-cleanup.service
[Unit]
Description=Skriptoteket sandbox snapshot cleanup
Requires=snap.docker.dockerd.service
After=snap.docker.dockerd.service

[Service]
Type=oneshot
ExecStart=/snap/bin/docker exec -e PYTHONPATH=/app/src skriptoteket-web pdm run python -m skriptoteket.cli cleanup-sandbox-snapshots
```

```ini
# /etc/systemd/system/skriptoteket-sandbox-snapshots-cleanup.timer
[Unit]
Description=Run sandbox snapshot cleanup hourly

[Timer]
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and verify:

```bash
ssh hemma "sudo systemctl daemon-reload"
ssh hemma "sudo systemctl enable --now skriptoteket-sandbox-snapshots-cleanup.timer"
ssh hemma "systemctl list-timers | grep skriptoteket-sandbox-snapshots"
ssh hemma "journalctl -u skriptoteket-sandbox-snapshots-cleanup.service -n 50 --no-pager"
```

Live note (hemma): timer is enabled and runs hourly; see `systemctl status skriptoteket-sandbox-snapshots-cleanup.timer`.

Manual trigger:

```bash
ssh hemma "sudo systemctl start skriptoteket-sandbox-snapshots-cleanup.service"
```

### Login Events Cleanup (DB)

Login event audit rows are retained for 90 days. Cleanup is scheduled server-side via systemd.

Unit files:

```ini
# /etc/systemd/system/skriptoteket-login-events-cleanup.service
[Unit]
Description=Skriptoteket login events cleanup
Requires=snap.docker.dockerd.service
After=snap.docker.dockerd.service

[Service]
Type=oneshot
ExecStart=/snap/bin/docker exec -e PYTHONPATH=/app/src skriptoteket-web pdm run python -m skriptoteket.cli cleanup-login-events
```

```ini
# /etc/systemd/system/skriptoteket-login-events-cleanup.timer
[Unit]
Description=Run login events cleanup daily

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and verify:

```bash
ssh hemma "sudo systemctl daemon-reload"
ssh hemma "sudo systemctl enable --now skriptoteket-login-events-cleanup.timer"
ssh hemma "systemctl list-timers | grep skriptoteket-login-events"
ssh hemma "journalctl -u skriptoteket-login-events-cleanup.service -n 50 --no-pager"
```

Manual trigger:

```bash
ssh hemma "sudo systemctl start skriptoteket-login-events-cleanup.service"
```

### SSL Certificate

Check expiry:

```bash
ssh hemma "docker exec nginx-proxy cat /etc/nginx/certs/live/skriptoteket.hule.education/fullchain.pem | openssl x509 -noout -dates"
```

Renew:

```bash
ssh hemma "cd ~/infrastructure && docker compose run --rm certbot renew"
ssh hemma "docker exec nginx-proxy nginx -s reload"
```

## Deploy

### Standard Deploy (Code Changes)

```bash
ssh hemma "cd ~/apps/skriptoteket && git pull && docker compose -f compose.prod.yaml up -d --build"
```

If migrations are needed:

```bash
ssh hemma "cd ~/apps/skriptoteket && docker compose -f compose.prod.yaml exec web pdm run db-upgrade"
```

### Deploy with Force Recreate

Use when `compose.prod.yaml` changes (networks, volumes, environment).

```bash
ssh hemma "cd ~/apps/skriptoteket && docker compose -f compose.prod.yaml up -d --force-recreate"
```

### Rollback

```bash
# Check available commits
ssh hemma "cd ~/apps/skriptoteket && git log --oneline -10"

# Checkout previous version
ssh hemma "cd ~/apps/skriptoteket && git checkout <commit-hash>"

# Rebuild and restart
ssh hemma "cd ~/apps/skriptoteket && docker compose -f compose.prod.yaml up -d --build"
```

## Data

Production uses `shared-postgres` (external container on `hule-network`).

### Connect to Database

```bash
ssh hemma "docker exec -it shared-postgres psql -U postgres -d skriptoteket"
```

### Backup Database

```bash
ssh hemma "docker exec shared-postgres pg_dump -U postgres skriptoteket > ~/backups/skriptoteket-\$(date +%Y%m%d).sql"
```

### Restore Database

```bash
ssh hemma "docker exec -i shared-postgres psql -U postgres -d skriptoteket < ~/backups/skriptoteket-YYYYMMDD.sql"
```

### Run Migrations

```bash
ssh hemma "cd ~/apps/skriptoteket && docker compose -f compose.prod.yaml exec web pdm run db-upgrade"
```

### Full Database Reset (DANGER)

This destroys all data. Only use for fresh installations. `shared-postgres` is external and not managed by this compose.

```bash
ssh hemma "cd ~/apps/skriptoteket && docker compose -f compose.prod.yaml down"

# Connect to shared-postgres and drop/recreate database
ssh hemma "docker exec -it shared-postgres psql -U postgres -c 'DROP DATABASE IF EXISTS skriptoteket;'"
ssh hemma "docker exec -it shared-postgres psql -U postgres -c 'CREATE DATABASE skriptoteket;'"

# Restart and run migrations
ssh hemma "cd ~/apps/skriptoteket && docker compose -f compose.prod.yaml up -d"
ssh hemma "cd ~/apps/skriptoteket && docker compose -f compose.prod.yaml exec web pdm run db-upgrade"
ssh hemma "cd ~/apps/skriptoteket && docker compose -f compose.prod.yaml exec -T -e PYTHONPATH=/app/src web pdm run python -m skriptoteket.cli bootstrap-superuser --email admin@hule.education --password 'CHANGE_THIS_PASSWORD'"
ssh hemma "cd ~/apps/skriptoteket && docker compose -f compose.prod.yaml exec -T -e PYTHONPATH=/app/src web pdm run python -m skriptoteket.cli seed-script-bank --actor-email admin@hule.education --actor-password 'CHANGE_THIS_PASSWORD'"
```

### User Management

See [runbook-user-management.md](runbook-user-management.md) for details.

```bash
# Bootstrap superuser (first-time setup only)
ssh hemma "cd ~/apps/skriptoteket && docker compose -f compose.prod.yaml exec -T -e PYTHONPATH=/app/src web pdm run python -m skriptoteket.cli bootstrap-superuser --email 'admin@example.com' --password 'SECURE_PASSWORD'"

# Provision additional user
ssh hemma "cd ~/apps/skriptoteket && docker compose -f compose.prod.yaml exec -T -e PYTHONPATH=/app/src web pdm run python -m skriptoteket.cli provision-user --actor-email 'admin@example.com' --actor-password 'ADMIN_PASSWORD' --email 'user@example.com' --password 'USER_PASSWORD' --role user"
```

### Script Bank Seeding

See [runbook-script-bank-seeding-home-server.md](runbook-script-bank-seeding-home-server.md).

```bash
# Seed all scripts from repository
ssh hemma "cd ~/apps/skriptoteket && docker compose -f compose.prod.yaml exec -T -e PYTHONPATH=/app/src web pdm run python -m skriptoteket.cli seed-script-bank --actor-email admin@hule.education --actor-password 'PASSWORD'"

# Sync code changes from repo to existing tools
ssh hemma "cd ~/apps/skriptoteket && docker compose -f compose.prod.yaml exec -T -e PYTHONPATH=/app/src web pdm run python -m skriptoteket.cli seed-script-bank --actor-email admin@hule.education --actor-password 'PASSWORD' --sync-code"
```

## Observability

The observability stack runs independently via `compose.observability.yaml`.

### Start/Stop

```bash
# Start observability stack
ssh hemma "cd ~/apps/skriptoteket && docker compose -f compose.observability.yaml up -d"

# Stop observability stack
ssh hemma "cd ~/apps/skriptoteket && docker compose -f compose.observability.yaml down"

# Restart (e.g., after config changes)
ssh hemma "cd ~/apps/skriptoteket && docker compose -f compose.observability.yaml restart"
```

### Components

| Service | Port | URL | Purpose |
|---------|------|-----|---------|
| Grafana | 3000 | https://grafana.hemma.hule.education | Dashboards |
| Prometheus | 9090 | https://prometheus.hemma.hule.education | Metrics |
| Jaeger | 16686 | https://jaeger.hemma.hule.education | Tracing |
| Loki | 3100 | - | Log aggregation |
| Promtail | - | - | Log collection |

Prometheus and Jaeger are protected by basic auth; see `docs/runbooks/runbook-observability.md` for access notes.

### View Observability Logs

```bash
ssh hemma "docker logs -f grafana"
ssh hemma "docker logs -f prometheus"
ssh hemma "docker logs -f jaeger"
ssh hemma "docker logs -f loki"
```

### Metrics

```bash
# Via metrics endpoint
ssh hemma "curl -s https://skriptoteket.hule.education/metrics | grep skriptoteket_session_files"

# Example output:
# skriptoteket_session_files_bytes_total 12345.0
# skriptoteket_session_files_count 42.0
```

## Troubleshooting

### 502 Bad Gateway

**Symptom**: nginx returns 502 after container restart.

**Cause**: Web container not connected to `hule-network`.

**Fix**:
```bash
# Verify network membership
ssh hemma "docker network inspect hule-network --format '{{json .Containers}}' | python3 -m json.tool | grep skriptoteket"

# If missing, reconnect manually (temporary fix)
ssh hemma "docker network connect hule-network skriptoteket-web"

# Permanent fix: redeploy with compose.prod.yaml
ssh hemma "cd ~/apps/skriptoteket && docker compose -f compose.prod.yaml up -d --force-recreate"
```

### 307 Redirect to HTTP Instead of HTTPS

**Symptom**: Clicking links redirects to `http://` URL, breaking the site.

**Cause**: Uvicorn doesn't know original scheme was HTTPS.

**Fix**: Ensure `pyproject.toml` serve command includes proxy headers:
```toml
serve = "uvicorn ... --proxy-headers --forwarded-allow-ips='*'"
```

And nginx sets the header:
```nginx
proxy_set_header X-Forwarded-Proto $scheme;
```

### 500 Internal Server Error on All Routes

**Symptom**: Every page returns 500 error.

**Cause**: Usually database tables missing (migrations not run).

**Diagnosis**:
```bash
# Check web container logs for "relation does not exist" errors
ssh hemma "docker logs skriptoteket-web --tail 50"
```

**Fix**:
```bash
ssh hemma "cd ~/apps/skriptoteket && docker compose -f compose.prod.yaml exec web pdm run db-upgrade"
```

### CLI Commands Fail with "No module named 'skriptoteket'"

**Cause**: PYTHONPATH not set for PEP 582 mode.

**Fix**: Always include `-e PYTHONPATH=/app/src` when running CLI commands:
```bash
docker compose exec -T -e PYTHONPATH=/app/src web pdm run python -m skriptoteket.cli <command>
```

### Container Won't Start

```bash
# Check logs for errors
ssh hemma "docker logs skriptoteket-web 2>&1 | tail -50"

# Check if port is in use
ssh hemma "lsof -i :8000"
```

### DNS Not Resolving

```bash
# Check DDNS status
ssh hemma "systemctl status ddclient"

# Force DDNS update
ssh hemma "ddclient -force"

# Check external IP
ssh hemma "curl -s ifconfig.me"

# Verify DNS at nameserver
dig +short skriptoteket.hule.education @pdns1.registrar-servers.com
```

### Disk Space

```bash
# Check disk usage
ssh hemma "df -h"

# Docker disk usage
ssh hemma "docker system df"

# Clean up unused Docker resources
ssh hemma "docker system prune -f"

# Prune old artifact directories
ssh hemma "cd ~/apps/skriptoteket && docker compose -f compose.prod.yaml exec -T -e PYTHONPATH=/app/src web pdm run python -m skriptoteket.cli prune-artifacts"
```
