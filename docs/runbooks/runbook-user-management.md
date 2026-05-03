---
type: runbook
id: RUN-user-management
title: "Runbook: User and Local Role Management"
status: active
owners: "system-admin"
created: 2025-12-16
updated: 2026-04-13
system: "skriptoteket-identity"
---

## When to use this runbook

Use this runbook when you need to:

- Bootstrap a new deployment with the first Superuser.
- Inspect or repair Skriptoteket-local users, identity projections, and roles.
- Grant or revoke app-local roles.

**Context:** Browser login, shared session, CSRF, registration, password reset, and email
verification are HuleEdu/Hule Education-owned ceremonies. Skriptoteket keeps local users,
identity projections, profiles, and RBAC roles. Do not recreate app-local browser sessions or
change browser credentials directly in this repo.

## Prerequisites

- SSH access to the server
- Production stack running (`~/apps/skriptoteket`, `compose.prod.yaml`, service `web`)

## Role Hierarchy

| Role | Permissions |
|------|-------------|
| `user` | Browse katalog, run tools |
| `contributor` | Above + submit suggestions |
| `admin` | Above + manage tools, review suggestions, publish |
| `superuser` | Full system access |

## Procedures

### 1. Bootstrap the First Admin (Superuser)

Run this only once when setting up a fresh database.

```bash
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.prod.yaml exec -T -e PYTHONPATH=/app/src web pdm run python -m skriptoteket.cli bootstrap-superuser --email 'admin@example.com' --password 'SECURE_PASSWORD'"
```

**Interactive mode** (prompts for password):
```bash
ssh hemma
cd ~/apps/skriptoteket
sudo docker compose -f compose.prod.yaml exec -e PYTHONPATH=/app/src web pdm run python -m skriptoteket.cli bootstrap-superuser --email 'admin@example.com'
```

### 2. Provision Additional Local Users

Use an existing admin/superuser account to create local app users only when an operational repair
or bootstrap workflow explicitly requires it. Normal browser onboarding should use the HuleEdu
`app=skriptoteket` ceremony and the realm-aware projection flow.

```bash
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.prod.yaml exec -T -e PYTHONPATH=/app/src web pdm run python -m skriptoteket.cli provision-user --actor-email 'admin@example.com' --actor-password 'ADMIN_PASSWORD' --email 'newuser@example.com' --password 'USER_PASSWORD' --role user"
```

**Available roles:** `user`, `contributor`, `admin`, `superuser`

**Important:** This does not mint a HuleEdu browser session and must not be treated as a browser
credential ceremony.

**Interactive mode:**
```bash
ssh hemma
cd ~/apps/skriptoteket
sudo docker compose -f compose.prod.yaml exec -e PYTHONPATH=/app/src web pdm run python -m skriptoteket.cli provision-user --actor-email 'admin@example.com' --email 'newuser@example.com' --role user
```

### 3. Browser Credential Lifecycle

Do not change browser passwords in the Skriptoteket database. Password reset, registration, and
email verification are HuleEdu Gateway/Identity lifecycle ceremonies for `app=skriptoteket` and the
selected product identity realm.

If a user cannot log in, triage the HuleEdu ceremony and identity lifecycle first, then confirm that
Skriptoteket has the expected local identity projection for the signed realm subject.

### 4. Consume HuleEdu Subject Export

Use this for approved sanitized HuleEdu subject exports that seed or repair local
Skriptoteket projections and roles. The current launch input is the `TASK-0326`
proof export. The consumer validates `schema_version=skriptoteket-proof-subject-export-v1`,
`active_app=skriptoteket`, `active_product_identity_realm=skriptoteket_standalone`,
verified email, explicit `stable_account_key`, and the local `skriptoteket_role_hint`
matrix before writing anything.

The command keys projections by `(active_product_identity_realm, realm_subject_id)`.
`huleedu_subject_id` is diagnostic only and must never be used as a projection key.

Accepted input is either the HuleEdu provider envelope with `status=ok`, no
`errors`, and an `export` object, or the fully versioned export object itself.
Do not pass bare account arrays or unversioned `{"accounts": [...]}` payloads;
the consumer rejects them instead of synthesizing schema/app/realm values.

Local dry-run against the retained sanitized fixture:

```bash
pdm run consume-huleedu-subject-export \
  --export-json tests/fixtures/identity/huleedu_subject_export_v1.json \
  --output-json .artifacts/skriptoteket-auth-bootstrap/local-consume-dry-run.json \
  --dry-run
```

Dry-run summaries report planned actions with `would_create_users`,
`would_create_projections`, and `would_update_users`. Concrete `created_*` and
`updated_*` counters remain actual write counters and should stay `0` in
dry-run artifacts.

Local apply:

```bash
pdm run consume-huleedu-subject-export \
  --export-json tests/fixtures/identity/huleedu_subject_export_v1.json \
  --output-json .artifacts/skriptoteket-auth-bootstrap/local-consume-apply.json \
  --apply
```

Local shared-auth bootstrap preflight:

```bash
pdm run auth-edge-bootstrap-preflight \
  --export-json /Users/olofs_mba/Documents/Repos/huleedu/.artifacts/skriptoteket-auth-bootstrap/local-verify-export.json \
  --output-json .artifacts/skriptoteket-auth-bootstrap/preflight.json
```

For the supported local shared-auth lane, HuleEdu owns the browser credential
seed and Skriptoteket owns projection/RBAC. The durable local bootstrap
superuser is `superuser@local.dev` with `BOOTSTRAP_SUPERUSER_PASSWORD`, and the
HuleEdu local export should include deterministic `@local.dev` proof accounts
for `user`, `contributor`, `admin`, and `superuser`. If the preflight reports
`bootstrap_identity_conflict`, the local Skriptoteket DB still contains a
legacy password-owner user for the bootstrap email; reset the local dev DB or
run an explicit governed migration before applying the HuleEdu export.

Production handoff from HuleEdu should copy only the sanitized export JSON into the
Skriptoteket artifact volume, then run a dry-run first:

```bash
ssh hemma
cd ~/apps/skriptoteket
sudo docker compose -f compose.prod.yaml cp \
  .artifacts/skriptoteket-auth-bootstrap/hemma-verify-export.json \
  web:/app/.artifacts/skriptoteket-auth-bootstrap/subject-export.json
sudo docker compose -f compose.prod.yaml exec -T -e PYTHONPATH=/app/src web \
  pdm run python -m skriptoteket.cli consume-huleedu-subject-export \
  --export-json /app/.artifacts/skriptoteket-auth-bootstrap/subject-export.json \
  --output-json /app/.artifacts/skriptoteket-auth-bootstrap/skriptoteket-consume-dry-run.json \
  --dry-run
```

Apply only after the dry-run output is reviewed:

```bash
sudo docker compose -f compose.prod.yaml exec -T -e PYTHONPATH=/app/src web \
  pdm run python -m skriptoteket.cli consume-huleedu-subject-export \
  --export-json /app/.artifacts/skriptoteket-auth-bootstrap/subject-export.json \
  --output-json /app/.artifacts/skriptoteket-auth-bootstrap/skriptoteket-consume-apply.json \
  --apply
```

Retain only sanitized command output. Do not paste credentials, cookies, reset links,
verification links, token-bearing URLs, or raw signed identity payloads into docs.

### 5. List All Users

```bash
ssh hemma "sudo docker exec shared-postgres psql -U postgres -d skriptoteket -c \"SELECT id, email, role, created_at FROM users ORDER BY created_at;\""
```

### 6. List Identity Projections

```bash
ssh hemma "sudo docker exec shared-postgres psql -U postgres -d skriptoteket -c \"SELECT user_id, product_identity_realm, realm_subject_id, created_at FROM identity_projections ORDER BY created_at DESC LIMIT 50;\""
```

### 7. Change User Role

```bash
ssh hemma "sudo docker exec shared-postgres psql -U postgres -d skriptoteket -c \"UPDATE users SET role = 'admin' WHERE email = 'user@example.com';\""
```

### 8. Deactivate or Delete User

Prefer the superuser admin deactivation path for normal account lifecycle work:
`POST /api/v1/admin/users/{user_id}/deactivate`. This revokes owned
Klassrumskartan public share artifacts before marking the account inactive.

Raw SQL deletion is only for deliberate operator repair after related lifecycle
cleanup has been handled:

```bash
ssh hemma "sudo docker exec shared-postgres psql -U postgres -d skriptoteket -c \"DELETE FROM users WHERE email = 'user@example.com';\""
```

**Warning:** This may fail if the user has related records such as identity projections, tool
versions, runs, favorites, profiles, or share artifacts. Prefer deliberate migration/repair
scripts for anything larger than a one-off operator correction.

## Troubleshooting

### "User already exists"

The email is already taken. Check existing users:
```bash
ssh hemma "sudo docker exec shared-postgres psql -U postgres -d skriptoteket -c \"SELECT email FROM users;\""
```

### "Insufficient permissions"

The actor must have `ADMIN` or `SUPERUSER` role to provision users.

### "Invalid admin credentials"

The legacy local CLI actor credential may not reflect the browser HuleEdu credential. Prefer
projection/role inspection and avoid treating local password hashes as the user-facing login
authority.

### "No module named 'skriptoteket'"

Missing PYTHONPATH. Always use:
```bash
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.prod.yaml exec -T -e PYTHONPATH=/app/src web pdm run python -m skriptoteket.cli ..."
```

### Browser Session Issues

Skriptoteket no longer owns browser sessions. Logout, expiry, and session invalidation belong to the
HuleEdu shared browser-session authority.
