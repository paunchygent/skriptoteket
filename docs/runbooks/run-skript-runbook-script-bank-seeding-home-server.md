---
type: runbook
id: RUN-SKRIPT-runbook-script-bank-seeding-home-server
title: 'Runbook: Script bank seeding (home server)'
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-07-31'
status: active
retired_ids:
  - RUN-script-bank-seeding-home-server
summary: 'Runbook: Script bank seeding (home server)'
system: hemma.hule.education
---

## Trigger

Environment-specific runbook for seeding the script bank on the home server.

### Prerequisites

- Superuser account exists (see [runbook-user-management.md](run-skript-runbook-user-and-local-role-management.md))
- Database migrations applied
- Web container running

### Credentials (server-side)

Superuser credentials come from the `skriptoteket-prod` agent-secrets set
(`BOOTSTRAP_SUPERUSER_EMAIL` / `BOOTSTRAP_SUPERUSER_PASSWORD`), injected by the
`hemma-seed-script-bank` pdm script — never stored in `.env`.

### Command Template (recommended: from local machine)

Run on Hemma in the production checkout `~/apps/skriptoteket`. The
`hemma-seed-script-bank` pdm script injects the `skriptoteket-prod` secret set
through `agent-secrets` and runs the seed module inside the `web` container via
`docker compose -f compose.prod.yaml exec`:

```bash
pdm run hemma-seed-script-bank -- <FLAGS>
```

Common flags:

- `--dry-run`
- `--slug <slug>`
- `--sync-metadata`
- `--sync-code`
- `--profile prod` (seedar endast curated verktyg)

### Examples

Dry-run:

```bash
pdm run hemma-seed-script-bank -- --dry-run --profile prod
```

Sync code changes from repo to existing tools:

```bash
pdm run hemma-seed-script-bank -- --sync-code --profile prod
```

### Verification

1. **Katalog**: Tool visible at `/browse` (if published)
2. **Admin Script Editor**: `/admin/tool-versions/{id}` shows correct ACTIVE version
3. **Tool Execution**: Run the tool with test data to verify functionality

### Troubleshooting

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

## Preconditions

No separate material is recorded in the source snapshot.

## Steps

Environment-specific runbook for seeding the script bank on the home server.

### Prerequisites

- Superuser account exists (see [runbook-user-management.md](run-skript-runbook-user-and-local-role-management.md))
- Database migrations applied
- Web container running

### Credentials (server-side)

Superuser credentials come from the `skriptoteket-prod` agent-secrets set
(`BOOTSTRAP_SUPERUSER_EMAIL` / `BOOTSTRAP_SUPERUSER_PASSWORD`), injected by the
`hemma-seed-script-bank` pdm script — never stored in `.env`.

### Command Template (recommended: from local machine)

Run on Hemma in the production checkout `~/apps/skriptoteket`. The
`hemma-seed-script-bank` pdm script injects the `skriptoteket-prod` secret set
through `agent-secrets` and runs the seed module inside the `web` container via
`docker compose -f compose.prod.yaml exec`:

```bash
pdm run hemma-seed-script-bank -- <FLAGS>
```

Common flags:

- `--dry-run`
- `--slug <slug>`
- `--sync-metadata`
- `--sync-code`
- `--profile prod` (seedar endast curated verktyg)

### Examples

Dry-run:

```bash
pdm run hemma-seed-script-bank -- --dry-run --profile prod
```

Sync code changes from repo to existing tools:

```bash
pdm run hemma-seed-script-bank -- --sync-code --profile prod
```

### Verification

1. **Katalog**: Tool visible at `/browse` (if published)
2. **Admin Script Editor**: `/admin/tool-versions/{id}` shows correct ACTIVE version
3. **Tool Execution**: Run the tool with test data to verify functionality

### Troubleshooting

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

## Expected Results

1. **Katalog**: Tool visible at `/browse` (if published)
2. **Admin Script Editor**: `/admin/tool-versions/{id}` shows correct ACTIVE version
3. **Tool Execution**: Run the tool with test data to verify functionality

## Stop Conditions

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

## Rollback

No separate material is recorded in the source snapshot.

### Source Record

Environment-specific runbook for seeding the script bank on the home server.

### Prerequisites

- Superuser account exists (see [runbook-user-management.md](run-skript-runbook-user-and-local-role-management.md))
- Database migrations applied
- Web container running

### Credentials (server-side)

Superuser credentials come from the `skriptoteket-prod` agent-secrets set
(`BOOTSTRAP_SUPERUSER_EMAIL` / `BOOTSTRAP_SUPERUSER_PASSWORD`), injected by the
`hemma-seed-script-bank` pdm script — never stored in `.env`.

### Command Template (recommended: from local machine)

Run on Hemma in the production checkout `~/apps/skriptoteket`. The
`hemma-seed-script-bank` pdm script injects the `skriptoteket-prod` secret set
through `agent-secrets` and runs the seed module inside the `web` container via
`docker compose -f compose.prod.yaml exec`:

```bash
pdm run hemma-seed-script-bank -- <FLAGS>
```

Common flags:

- `--dry-run`
- `--slug <slug>`
- `--sync-metadata`
- `--sync-code`
- `--profile prod` (seedar endast curated verktyg)

### Examples

Dry-run:

```bash
pdm run hemma-seed-script-bank -- --dry-run --profile prod
```

Sync code changes from repo to existing tools:

```bash
pdm run hemma-seed-script-bank -- --sync-code --profile prod
```

### Verification

1. **Katalog**: Tool visible at `/browse` (if published)
2. **Admin Script Editor**: `/admin/tool-versions/{id}` shows correct ACTIVE version
3. **Tool Execution**: Run the tool with test data to verify functionality

### Troubleshooting

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
