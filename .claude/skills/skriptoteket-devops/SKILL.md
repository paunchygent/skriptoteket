---
name: skriptoteket-devops
description: DevOps and server management for Skriptoteket on home server (hemma.hule.education). Branched skill covering deploy, database, users, CLI, security, network, DNS, and troubleshooting.
---

# Skriptoteket DevOps

Compact skill for managing Skriptoteket on home server.

Source of truth for ops in this repo:

- Home server ops: `docs/runbooks/runbook-home-server.md`
- Observability ops: `docs/runbooks/runbook-observability.md`

## When to Use

Activate when the user:
- Needs to deploy changes to home server
- Wants to manage database (backup/restore/migrations)
- Creates or manages users (bootstrap, provision)
- Troubleshoots errors (502, 307, 500)
- Works with SSL/certificates
- Has DNS/DDNS issues
- Needs to run CLI commands in container
- Wants to seed or sync the script bank

---

## Critical Configuration (Copy-Paste Ready)

### SSH Access (Passwordless)

```bash
ssh hemma              # Via hemma.hule.education (dynamic DNS)
ssh hemma-local        # Via 192.168.0.9 (local network, faster)
```

### Production Deployment

```bash
# ALWAYS use compose.prod.yaml for production
ssh hemma "cd ~/apps/skriptoteket && git pull && docker compose -f compose.prod.yaml up -d --build"

# With migrations
ssh hemma "cd ~/apps/skriptoteket && git pull && docker compose -f compose.prod.yaml up -d --build"
ssh hemma "docker exec skriptoteket-web pdm run db-upgrade"
```

Note: On `hemma`, systemd units may need absolute docker path (`/snap/bin/docker`) due to PATH differences.

### Container Names

| Environment | Web Container | DB Container |
|-------------|---------------|--------------|
| Production | `skriptoteket-web` | `shared-postgres` (external) |
| Development | `skriptoteket_web` | `skriptoteket-db-1` |

### Database Connection

```bash
# Production DB (shared-postgres on hule-network)
DATABASE_URL=postgresql+asyncpg://skriptoteket:${SKRIPTOTEKET_DB_PASSWORD}@shared-postgres:5432/skriptoteket

# Dev DB (local container)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/skriptoteket

# Connect to prod DB via psql
ssh hemma "docker exec -it shared-postgres psql -U skriptoteket -d skriptoteket"

# Connect to dev DB
ssh hemma "docker exec -it skriptoteket-db-1 psql -U postgres -d skriptoteket"
```

### CLI Command Pattern (ALWAYS USE)

```bash
# The -e PYTHONPATH=/app/src is REQUIRED for all CLI commands
docker exec -e PYTHONPATH=/app/src skriptoteket-web pdm run <command>

# Non-interactive (scripts/CI): add -T
docker exec -T -e PYTHONPATH=/app/src skriptoteket-web pdm run <command>

# Interactive (prompts): add -it
docker exec -it -e PYTHONPATH=/app/src skriptoteket-web pdm run <command>
```

See also: `docs/runbooks/runbook-home-server.md` (systemd timer patterns use `/snap/bin/docker exec ...`).

### Admin Credentials (Script Bank Seeding)

```bash
# Default admin for seeding (set in .env on server)
SKRIPTOTEKET_SCRIPT_BANK_ACTOR_EMAIL=admin@hule.education
SKRIPTOTEKET_SCRIPT_BANK_ACTOR_PASSWORD=<from server .env>

# Seed command
ssh hemma "cd ~/apps/skriptoteket && docker compose exec -T -e PYTHONPATH=/app/src web pdm run python -m skriptoteket.cli seed-script-bank --actor-email admin@hule.education --actor-password 'PASSWORD'"
```

### Network Configuration

| Network | Purpose | Containers |
|---------|---------|------------|
| `hule-network` | Inter-service (nginx, shared-postgres) | nginx-proxy, skriptoteket-web, shared-postgres |
| `skriptoteket_default` | Compose internal (dev only) | skriptoteket_web, skriptoteket-db-1 |

**Critical:** Production web container must be on `hule-network` for nginx to reach it.

### File Paths on Server

```
~/apps/skriptoteket/           # App repo (git pull here)
~/apps/skriptoteket/.env       # Production secrets (never commit)
~/infrastructure/              # nginx-proxy, certbot
~/backups/                     # Database backups
```

---

## Most Used Commands

### Deploy

```bash
# Standard deploy
ssh hemma "cd ~/apps/skriptoteket && git pull && docker compose -f compose.prod.yaml up -d --build"

# With migrations
ssh hemma "docker exec skriptoteket-web pdm run db-upgrade"

# Force recreate (config changes)
ssh hemma "cd ~/apps/skriptoteket && docker compose -f compose.prod.yaml up -d --force-recreate"
```

### Database

```bash
# Backup
ssh hemma "docker exec shared-postgres pg_dump -U skriptoteket skriptoteket > ~/backups/skriptoteket-\$(date +%Y%m%d).sql"

# Migrations
ssh hemma "docker exec skriptoteket-web pdm run db-upgrade"
```

### Cleanup timers (systemd)

We enforce TTL-based cleanup using CLI commands + systemd timers (not cron). Examples:

- Sandbox snapshots cleanup: `cleanup-sandbox-snapshots`
- Login events cleanup (retention): `cleanup-login-events`

Exact unit definitions and schedules: `docs/runbooks/runbook-home-server.md`.

### Users

```bash
# Bootstrap superuser (first time)
ssh hemma "docker exec -it -e PYTHONPATH=/app/src skriptoteket-web pdm run python -m skriptoteket.cli bootstrap-superuser --email admin@hule.education"

# Provision user
ssh hemma "docker exec -T -e PYTHONPATH=/app/src skriptoteket-web pdm run python -m skriptoteket.cli provision-user --actor-email admin@hule.education --actor-password 'ADMIN_PASS' --email user@example.com --password 'USER_PASS' --role contributor"
```

### Logs

```bash
ssh hemma "docker logs -f skriptoteket-web"
ssh hemma "docker logs -f nginx-proxy"
```

### Status

```bash
ssh hemma "docker ps | grep -E 'skriptoteket|nginx|postgres'"
```

---

## Branch Routing

| Task | Branch |
|------|--------|
| Deploy, rebuild, rollback | `branches/deploy.md` |
| PostgreSQL backup/restore | `branches/database.md` |
| Superuser, provision users | `branches/users.md` |
| Script bank seeding | `branches/seed.md` |
| CLI commands in container | `branches/cli.md` |
| SSL certificates, nginx | `branches/security.md` |
| Docker networks, 502 errors | `branches/network.md` |
| DNS, DDNS, Namecheap | `branches/dns-provider.md` |
| Ubuntu, disk, docker system | `branches/server-os.md` |
| All troubleshooting patterns | `branches/troubleshoot.md` |

---

## Quick Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| 502 Bad Gateway | Web not on hule-network | `docker network connect hule-network skriptoteket-web` |
| 307 to HTTP | Missing proxy headers | Check `--proxy-headers` in serve command |
| 500 on all routes | Missing migrations | `docker exec skriptoteket-web pdm run db-upgrade` |
| "No module skriptoteket" | Missing PYTHONPATH | Add `-e PYTHONPATH=/app/src` |

---

## Research Documentation

Full research: `docs/reference/reports/ref-devops-skill-research.md`

## Maintenance note

This skill includes deeper branches under `.claude/skills/skriptoteket-devops/branches/`.
Keep those branch docs aligned with the runbooks above when ops patterns change.
