---
type: runbook
id: RUN-script-bank-seeding-home-server
title: "Runbook: Script bank seeding (home server)"
status: active
owners: "olof"
created: 2025-12-16
updated: 2025-12-16
system: "hemma.hule.education"
---

Environment-specific runbook for seeding the script bank on the home server.

## Prerequisites

- Superuser account exists (see [runbook-home-server.md](runbook-home-server.md) for bootstrap)
- Database migrations applied
- Web container running

## Quick Seeding

```bash
# From local machine (recommended, non-interactive)
#
# 1) Store credentials on the server in ~/apps/skriptoteket/.env (NOT in this repo):
#    SKRIPTOTEKET_SCRIPT_BANK_ACTOR_EMAIL=...
#    SKRIPTOTEKET_SCRIPT_BANK_ACTOR_PASSWORD=...
#
# 2) Source .env on the server, then pass vars into the container exec environment:
ssh hemma 'cd ~/apps/skriptoteket \
  && set -a && source .env && set +a \
  && docker compose -f compose.prod.yaml exec -T \
       -e PYTHONPATH=/app/src \
       -e SKRIPTOTEKET_SCRIPT_BANK_ACTOR_EMAIL \
       -e SKRIPTOTEKET_SCRIPT_BANK_ACTOR_PASSWORD \
       web pdm run python -m skriptoteket.cli seed-script-bank'
```

**Why this looks “verbose”**:

- `docker compose` reads `~/apps/skriptoteket/.env` for **variable substitution**, but it does **not** automatically
  inject all `.env` variables into the running container.
- `docker compose exec -e ...` injects env vars for that one CLI execution.
- `-T` is required for non-interactive execution (no TTY prompts).
- `PYTHONPATH=/app/src` is required so `python -m skriptoteket.cli ...` can import the app package.

## Interactive Mode (on server)

```bash
ssh hemma
cd ~/apps/skriptoteket

# Interactive prompts for credentials
docker compose -f compose.prod.yaml exec -e PYTHONPATH=/app/src web pdm run python -m skriptoteket.cli seed-script-bank
```

## Dry Run First

Always dry-run before making changes:

```bash
ssh hemma 'cd ~/apps/skriptoteket \
  && set -a && source .env && set +a \
  && docker compose -f compose.prod.yaml exec -T \
       -e PYTHONPATH=/app/src \
       -e SKRIPTOTEKET_SCRIPT_BANK_ACTOR_EMAIL \
       -e SKRIPTOTEKET_SCRIPT_BANK_ACTOR_PASSWORD \
       web pdm run python -m skriptoteket.cli seed-script-bank --dry-run'
```

## Common Operations

### Seed All Scripts

```bash
ssh hemma 'cd ~/apps/skriptoteket \
  && set -a && source .env && set +a \
  && docker compose -f compose.prod.yaml exec -T \
       -e PYTHONPATH=/app/src \
       -e SKRIPTOTEKET_SCRIPT_BANK_ACTOR_EMAIL \
       -e SKRIPTOTEKET_SCRIPT_BANK_ACTOR_PASSWORD \
       web pdm run python -m skriptoteket.cli seed-script-bank'
```

### Seed Single Tool

```bash
ssh hemma 'cd ~/apps/skriptoteket \
  && set -a && source .env && set +a \
  && docker compose -f compose.prod.yaml exec -T \
       -e PYTHONPATH=/app/src \
       -e SKRIPTOTEKET_SCRIPT_BANK_ACTOR_EMAIL \
       -e SKRIPTOTEKET_SCRIPT_BANK_ACTOR_PASSWORD \
       web pdm run python -m skriptoteket.cli seed-script-bank --slug ist-vh-mejl-bcc'
```

### Sync Metadata Only

Update title/summary for existing tools to match repository:

```bash
ssh hemma 'cd ~/apps/skriptoteket \
  && set -a && source .env && set +a \
  && docker compose -f compose.prod.yaml exec -T \
       -e PYTHONPATH=/app/src \
       -e SKRIPTOTEKET_SCRIPT_BANK_ACTOR_EMAIL \
       -e SKRIPTOTEKET_SCRIPT_BANK_ACTOR_PASSWORD \
       web pdm run python -m skriptoteket.cli seed-script-bank --sync-metadata'
```

### Sync Code Changes

Create and publish new version if repository script differs from ACTIVE version:

```bash
ssh hemma 'cd ~/apps/skriptoteket \
  && set -a && source .env && set +a \
  && docker compose -f compose.prod.yaml exec -T \
       -e PYTHONPATH=/app/src \
       -e SKRIPTOTEKET_SCRIPT_BANK_ACTOR_EMAIL \
       -e SKRIPTOTEKET_SCRIPT_BANK_ACTOR_PASSWORD \
       web pdm run python -m skriptoteket.cli seed-script-bank --sync-code'
```

### Full Sync (Metadata + Code)

```bash
ssh hemma 'cd ~/apps/skriptoteket \
  && set -a && source .env && set +a \
  && docker compose -f compose.prod.yaml exec -T \
       -e PYTHONPATH=/app/src \
       -e SKRIPTOTEKET_SCRIPT_BANK_ACTOR_EMAIL \
       -e SKRIPTOTEKET_SCRIPT_BANK_ACTOR_PASSWORD \
       web pdm run python -m skriptoteket.cli seed-script-bank --sync-metadata --sync-code'
```

## After Deploy Workflow

After deploying new code that includes script bank changes:

```bash
# 1. Deploy
ssh hemma "cd ~/apps/skriptoteket && git pull && docker compose -f compose.prod.yaml up -d --build"

# 2. Wait for container to be healthy
sleep 5

# 3. Sync code from repository
ssh hemma 'cd ~/apps/skriptoteket \
  && set -a && source .env && set +a \
  && docker compose -f compose.prod.yaml exec -T \
       -e PYTHONPATH=/app/src \
       -e SKRIPTOTEKET_SCRIPT_BANK_ACTOR_EMAIL \
       -e SKRIPTOTEKET_SCRIPT_BANK_ACTOR_PASSWORD \
       web pdm run python -m skriptoteket.cli seed-script-bank --sync-code'
```

## Verification

1. **Katalog**: Tool visible at `/browse` (if published)
2. **Admin Script Editor**: `/admin/tool-versions/{id}` shows correct ACTIVE version
3. **Tool Execution**: Run the tool with test data to verify functionality

## Troubleshooting

### "No module named 'skriptoteket'"

Missing PYTHONPATH. Use:

```bash
docker compose exec -T -e PYTHONPATH=/app/src web pdm run python -m skriptoteket.cli ...
```

### "Insufficient permissions"

Actor must be admin or superuser role.

### "Unknown profession/category slug"

The script bank entry references a profession or category that doesn't exist in the database. Check migrations and seed data.

### Tool Not Visible in Katalog

Check if `--publish` flag is set (default: true). Also verify `is_published` flag on the tool:

```bash
ssh hemma "docker exec -i shared-postgres psql -U skriptoteket -d skriptoteket -c \"SELECT slug, is_published FROM tools;\""
```

```text
    177
    118 -| Email                             | Role        | Password             |
    119 -|-----------------------------------|-------------|----------------------|
    120 -| `admin@hule.education`            | superuser   | AEM2ia1KnbeVd@XY     |
    121 -| `test.user@hule.education`        | user        | TestUser2025!        |
    122 -| `test.contributor@hule.education` | contributor | TestContributor2025! |
```
