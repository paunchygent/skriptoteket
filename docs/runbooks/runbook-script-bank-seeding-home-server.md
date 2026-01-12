---
type: runbook
id: RUN-script-bank-seeding-home-server
title: "Runbook: Script bank seeding (home server)"
status: active
owners: "olof"
created: 2025-12-16
updated: 2026-01-12
system: "hemma.hule.education"
---

Environment-specific runbook for seeding the script bank on the home server.

## Prerequisites

- Superuser account exists (see [runbook-user-management.md](runbook-user-management.md))
- Database migrations applied
- Web container running

## Credentials (server-side)

Store these on the server in `~/apps/skriptoteket/.env` (**never** in this repo):

- `SKRIPTOTEKET_SCRIPT_BANK_ACTOR_EMAIL`
- `SKRIPTOTEKET_SCRIPT_BANK_ACTOR_PASSWORD`

## Command Template (recommended: from local machine)

`sudo docker compose` reads `~/apps/skriptoteket/.env` for **variable substitution**, but it does **not**
automatically inject all `.env` vars into the running container. For CLI commands we therefore:

1. Source `.env` on the server (`set -a && source .env && set +a`)
2. Pass only the needed env vars through `docker compose exec -e ...`

Template:

```bash
ssh hemma 'cd ~/apps/skriptoteket \
  && set -a && source .env && set +a \
  && sudo docker compose -f compose.prod.yaml exec -T \
       -e PYTHONPATH=/app/src \
       -e SKRIPTOTEKET_SCRIPT_BANK_ACTOR_EMAIL \
       -e SKRIPTOTEKET_SCRIPT_BANK_ACTOR_PASSWORD \
       web pdm run python -m skriptoteket.cli seed-script-bank <FLAGS>'
```

Common flags:

- `--dry-run`
- `--slug <slug>`
- `--sync-metadata`
- `--sync-code`

## Examples

Dry-run:

```bash
ssh hemma 'cd ~/apps/skriptoteket \
  && set -a && source .env && set +a \
  && sudo docker compose -f compose.prod.yaml exec -T \
       -e PYTHONPATH=/app/src \
       -e SKRIPTOTEKET_SCRIPT_BANK_ACTOR_EMAIL \
       -e SKRIPTOTEKET_SCRIPT_BANK_ACTOR_PASSWORD \
       web pdm run python -m skriptoteket.cli seed-script-bank --dry-run'
```

Sync code changes from repo to existing tools:

```bash
ssh hemma 'cd ~/apps/skriptoteket \
  && set -a && source .env && set +a \
  && sudo docker compose -f compose.prod.yaml exec -T \
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
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.prod.yaml exec -T -e PYTHONPATH=/app/src web pdm run python -m skriptoteket.cli ..."
```

### "Insufficient permissions"

Actor must be admin or superuser role.

### "Unknown profession/category slug"

The script bank entry references a profession or category that doesn't exist in the database. Check migrations and seed data.

### Tool Not Visible in Katalog

Check if `--publish` flag is set (default: true). Also verify `is_published` flag on the tool:

```bash
ssh hemma "sudo docker exec -i shared-postgres psql -U skriptoteket -d skriptoteket -c \"SELECT slug, is_published FROM tools;\""
```
