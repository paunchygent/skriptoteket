---
type: runbook
id: RUN-user-management
title: "Runbook: User and Local Role Management"
status: active
owners: "system-admin"
created: 2025-12-16
updated: 2026-04-12
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

### 4. List All Users

```bash
ssh hemma "sudo docker exec shared-postgres psql -U postgres -d skriptoteket -c \"SELECT id, email, role, created_at FROM users ORDER BY created_at;\""
```

### 5. List Identity Projections

```bash
ssh hemma "sudo docker exec shared-postgres psql -U postgres -d skriptoteket -c \"SELECT user_id, product_identity_realm, realm_subject_id, created_at FROM identity_projections ORDER BY created_at DESC LIMIT 50;\""
```

### 6. Change User Role

```bash
ssh hemma "sudo docker exec shared-postgres psql -U postgres -d skriptoteket -c \"UPDATE users SET role = 'admin' WHERE email = 'user@example.com';\""
```

### 7. Delete User

```bash
ssh hemma "sudo docker exec shared-postgres psql -U postgres -d skriptoteket -c \"DELETE FROM users WHERE email = 'user@example.com';\""
```

**Warning:** This may fail if the user has related records such as identity projections, tool
versions, runs, favorites, or profiles. Prefer deliberate migration/repair scripts for anything
larger than a one-off operator correction.

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
