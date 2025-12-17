---
type: reference
id: REF-devops-skill-research
title: "DevOps Skill Research"
status: active
owners: "agents"
topic: "devops"
created: 2025-12-17
---

# Research for DevOps Skill Construction

Research document for creating the `skriptoteket-devops` Claude skill.

**Created:** 2025-12-17
**Sources:** Runbooks, ADRs, Docker configs, CLI code, pyproject.toml

---

## 1. Server Architecture Overview

### SSH Access

```bash
ssh hemma              # Via hemma.hule.education (dynamic DNS)
ssh hemma-local        # Via 192.168.0.9 (local network, faster)
```

- Passwordless sudo configured
- Dynamic DNS via Namecheap ddclient (auto-updates IP)

### Infrastructure Layout

```
~/apps/skriptoteket/           # Application repository
  compose.yaml                 # Dev compose
  compose.prod.yaml            # Production compose
  Dockerfile                   # Web app image
  Dockerfile.runner            # Script runner image
  .env                         # Local environment (never commit)

~/infrastructure/              # Shared infrastructure
  nginx/
    conf.d/
      skriptoteket.conf        # Nginx site config
    certs/                     # SSL certificates
  compose.yaml                 # nginx-proxy, certbot
```

### Network Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Internet                              │
└────────────────────────────┬────────────────────────────────┘
                             │ :443 (HTTPS)
┌────────────────────────────▼────────────────────────────────┐
│  nginx-proxy (hule-network)                                  │
│  - SSL termination                                           │
│  - Reverse proxy to skriptoteket-web:8000                   │
│  - Sets X-Forwarded-Proto header                            │
└────────────────────────────┬────────────────────────────────┘
                             │ :8000
┌────────────────────────────▼────────────────────────────────┐
│  skriptoteket-web (hule-network + skriptoteket_default)     │
│  - Uvicorn with --proxy-headers                             │
│  - Reads X-Forwarded-Proto for correct redirects            │
└────────────────────────────┬────────────────────────────────┘
                             │ :5432
┌────────────────────────────▼────────────────────────────────┐
│  shared-postgres (hule-network) [PROD]                       │
│  skriptoteket-db-1 (skriptoteket_default) [DEV]             │
│  - PostgreSQL 16                                             │
└─────────────────────────────────────────────────────────────┘
```

**Critical:** Web container must be on BOTH networks:
- `hule-network` for nginx-proxy to reach it
- `skriptoteket_default` for database connectivity (dev only)

---

## 2. Docker Configuration: Dev vs Prod

| Aspect | Development | Production |
|--------|-------------|------------|
| **Compose file** | `compose.yaml` + `compose.dev.yaml` | `compose.prod.yaml` |
| **Database** | Local `skriptoteket-db-1` | Shared `shared-postgres` |
| **Network** | `skriptoteket_default` + `hule-network` | `hule-network` only |
| **Container name** | `skriptoteket_web` | `skriptoteket-web` |
| **Port exposure** | `8000:8000` on localhost | Not exposed (behind proxy) |
| **DB port** | `55432:5432` (debug access) | Not exposed |
| **Docker socket** | Mounted (rw) | Mounted (ro) |
| **Artifacts** | `./.artifacts` bind mount | `artifacts_data` named volume |
| **Health check** | None | HTTP /health every 30s |

### Environment Variables

**Development (.env.example):**
```bash
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:55432/skriptoteket
BOOTSTRAP_SUPERUSER_EMAIL=superuser@local.dev
BOOTSTRAP_SUPERUSER_PASSWORD=change-me
RUNNER_IMAGE=skriptoteket-runner:latest
RUNNER_MAX_CONCURRENCY=1
ARTIFACTS_ROOT=./.artifacts
LOG_FORMAT=console
```

**Production (.env.example.prod):**
```bash
SKRIPTOTEKET_DB_PASSWORD=change-me
SECRET_KEY=generate-with-python-secrets-token-urlsafe-32
LOG_FORMAT=json
```

---

## 3. CLI Commands Reference

All CLI commands require `-e PYTHONPATH=/app/src` in Docker containers.

### Bootstrap Superuser (First-time Setup)

```bash
# Local dev
pdm run bootstrap-superuser

# Docker (interactive)
docker exec -it -e PYTHONPATH=/app/src skriptoteket-web pdm run bootstrap-superuser

# Home server
ssh hemma "cd ~/apps/skriptoteket && docker compose exec -it -e PYTHONPATH=/app/src web pdm run python -m skriptoteket.cli bootstrap-superuser --email 'admin@example.com'"
```

### Provision User

```bash
# Local dev
pdm run provision-user

# Home server (non-interactive with -T)
ssh hemma "cd ~/apps/skriptoteket && docker compose exec -T -e PYTHONPATH=/app/src web pdm run python -m skriptoteket.cli provision-user --actor-email 'admin@example.com' --actor-password 'ADMIN_PASSWORD' --email 'newuser@example.com' --password 'USER_PASSWORD' --role user"
```

**Roles:** `user`, `contributor`, `admin`, `superuser`

### Seed Script Bank

```bash
# All scripts
ssh hemma "cd ~/apps/skriptoteket && docker compose exec -T -e PYTHONPATH=/app/src web pdm run python -m skriptoteket.cli seed-script-bank --actor-email admin@hule.education --actor-password 'PASSWORD'"

# Dry run first
... --dry-run

# Single tool
... --slug ist-vh-mejl-bcc

# Sync metadata only
... --sync-metadata

# Sync code changes (creates new version if differs)
... --sync-code

# Full sync
... --sync-metadata --sync-code
```

### Database Migrations

```bash
# Local dev
pdm run db-upgrade

# Home server
ssh hemma "cd ~/apps/skriptoteket && docker compose exec web pdm run db-upgrade"
```

### Prune Artifacts

```bash
# With defaults from settings
pdm run artifacts-prune

# Custom retention
pdm run artifacts-prune --retention-days 14

# Dry run
pdm run artifacts-prune --dry-run
```

---

## 4. Deploy Procedures

### Standard Deploy

```bash
ssh hemma "cd ~/apps/skriptoteket && git pull && docker compose -f compose.prod.yaml up -d --build"
```

### Deploy with Migrations

```bash
ssh hemma "cd ~/apps/skriptoteket && git pull && docker compose -f compose.prod.yaml up -d --build"
ssh hemma "docker exec skriptoteket-web pdm run db-upgrade"
```

### Force Recreate (compose.yaml changes)

```bash
ssh hemma "cd ~/apps/skriptoteket && git pull && docker compose -f compose.prod.yaml up -d --force-recreate"
```

### Rollback

```bash
ssh hemma "cd ~/apps/skriptoteket && git log --oneline -10"
ssh hemma "cd ~/apps/skriptoteket && git checkout <commit-hash>"
ssh hemma "cd ~/apps/skriptoteket && docker compose -f compose.prod.yaml up -d --build"
```

### Full Database Reset (DESTRUCTIVE)

```bash
ssh hemma "cd ~/apps/skriptoteket && docker compose down --volumes --remove-orphans"
ssh hemma "cd ~/apps/skriptoteket && docker compose -f compose.prod.yaml up -d"
sleep 5
ssh hemma "docker exec skriptoteket-web pdm run db-upgrade"
ssh hemma "docker exec -it -e PYTHONPATH=/app/src skriptoteket-web pdm run python -m skriptoteket.cli bootstrap-superuser --email admin@hule.education"
```

---

## 5. Database Operations

### Connect to PostgreSQL

```bash
ssh hemma "docker exec -it skriptoteket-db-1 psql -U postgres -d skriptoteket"
```

### Backup

```bash
ssh hemma "docker exec skriptoteket-db-1 pg_dump -U postgres skriptoteket > ~/backups/skriptoteket-$(date +%Y%m%d).sql"
```

### Restore

```bash
ssh hemma "docker exec -i skriptoteket-db-1 psql -U postgres -d skriptoteket < ~/backups/skriptoteket-YYYYMMDD.sql"
```

### Useful Queries

```bash
# List users
ssh hemma "docker exec skriptoteket-db-1 psql -U postgres -d skriptoteket -c \"SELECT id, email, role, created_at FROM users ORDER BY created_at;\""

# List published tools
ssh hemma "docker exec skriptoteket-db-1 psql -U postgres -d skriptoteket -c \"SELECT slug, is_published FROM tools;\""

# Change user role
ssh hemma "docker exec skriptoteket-db-1 psql -U postgres -d skriptoteket -c \"UPDATE users SET role = 'admin' WHERE email = 'user@example.com';\""

# Delete user sessions (force re-login)
ssh hemma "docker exec skriptoteket-db-1 psql -U postgres -d skriptoteket -c \"DELETE FROM sessions WHERE user_id = (SELECT id FROM users WHERE email = 'user@example.com');\""
```

---

## 6. SSL/Certificate Management

### Check Expiry

```bash
ssh hemma "docker exec nginx-proxy cat /etc/nginx/certs/live/skriptoteket.hule.education/fullchain.pem | openssl x509 -noout -dates"
```

### Renew Certificate

```bash
ssh hemma "cd ~/infrastructure && docker compose run --rm certbot renew"
ssh hemma "docker exec nginx-proxy nginx -s reload"
```

---

## 7. DNS/DDNS (Namecheap)

### Check DDNS Status

```bash
ssh hemma "systemctl status ddclient"
```

### Force DDNS Update

```bash
ssh hemma "ddclient -force"
```

### Verify External IP

```bash
ssh hemma "curl -s ifconfig.me"
```

### Verify DNS Resolution

```bash
dig +short skriptoteket.hule.education @pdns1.registrar-servers.com
```

---

## 8. Log Viewing

```bash
# Web application
ssh hemma "docker logs -f skriptoteket_web"

# Nginx
ssh hemma "docker logs -f nginx-proxy"

# Database
ssh hemma "docker logs -f skriptoteket-db-1"
```

### Correlation ID Tracing

```bash
# Make request with correlation ID
CID="$(python -c 'import uuid; print(uuid.uuid4())')"
curl -i -H "X-Correlation-ID: ${CID}" https://skriptoteket.hule.education/login

# Search logs
ssh hemma "docker logs skriptoteket_web | rg '<correlation-id>'"
```

---

## 9. Troubleshooting Patterns

### 502 Bad Gateway

**Cause:** Web container not connected to `hule-network`

```bash
# Verify
ssh hemma "docker network inspect hule-network --format '{{json .Containers}}' | python3 -m json.tool | grep skriptoteket"

# Fix (temporary)
ssh hemma "docker network connect hule-network skriptoteket_web --alias skriptoteket-web"

# Fix (permanent)
# Redeploy with correct compose.prod.yaml
```

### 307 Redirect to HTTP

**Cause:** Missing proxy headers

**Fix:** Ensure `--proxy-headers --forwarded-allow-ips='*'` in serve command and nginx sets `X-Forwarded-Proto`

### 500 Internal Server Error

**Cause:** Database tables missing (after volume reset)

```bash
ssh hemma "docker logs skriptoteket-db-1 --tail 20"
ssh hemma "docker exec skriptoteket-web pdm run db-upgrade"
```

### CLI "No module named 'skriptoteket'"

**Cause:** PYTHONPATH not set

**Fix:** Always use `-e PYTHONPATH=/app/src`

### Container Won't Start

```bash
ssh hemma "docker logs skriptoteket_web 2>&1 | tail -50"
ssh hemma "lsof -i :8000"
```

### Disk Space

```bash
ssh hemma "df -h"
ssh hemma "docker system df"
ssh hemma "docker system prune -f"
```

---

## 10. Quick Status Checks

```bash
# All containers
ssh hemma "docker ps"

# Skriptoteket-specific
ssh hemma "docker ps | grep -E 'skriptoteket|nginx|postgres'"

# Health check
ssh hemma "curl -s http://localhost:8000/health | jq"
```

---

## 11. Architecture Decisions (from ADRs)

### Authentication (ADR-0006, ADR-0009)
- Local admin-provisioned accounts with server-side sessions in PostgreSQL
- No self-signup in v0.1
- User model includes `external_id` and `auth_provider` for future HuleEdu SSO

### Script Execution (ADR-0013, ADR-0016)
- Sibling container model via docker.sock mount
- Runner containers: non-root, capabilities dropped, pids-limit
- Concurrency controlled by `RUNNER_MAX_CONCURRENCY`

### Storage (ADR-0012)
- Source code in PostgreSQL
- Binary artifacts on filesystem at `ARTIFACTS_ROOT`
- Retention policy via `prune-artifacts` CLI command

### Observability (ADR-0018)
- Structlog with JSON output in production
- Correlation IDs via `X-Correlation-ID` header
- Required log fields: `timestamp`, `level`, `event`, `service.name`, `deployment.environment`

---

## 12. Skill Branch Structure Decision

Based on research, the following branch structure groups related operations naturally:

| Branch | Content |
|--------|---------|
| `deploy.md` | Standard deploy, migrations, force recreate, rollback |
| `database.md` | Connect, backup, restore, migrations, queries |
| `users.md` | Bootstrap superuser, provision user, role changes |
| `seed.md` | Script bank seeding, sync-code, sync-metadata |
| `cli.md` | General CLI pattern, PYTHONPATH, available commands |
| `security.md` | SSL certificates, expiry, renewal |
| `network.md` | Docker networks, 502 troubleshooting |
| `dns-provider.md` | Namecheap, ddclient, DNS verification |
| `server-os.md` | SSH access, disk space, docker system |
| `troubleshoot.md` | Error patterns (502, 307, 500), logs |

**Rationale:**
- Each branch is 50-100 lines (compact)
- Related operations grouped together
- No duplication (branches reference each other)
- All commands use SSH-first pattern
