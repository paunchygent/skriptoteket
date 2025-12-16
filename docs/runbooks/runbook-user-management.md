---
type: runbook
id: RUN-user-management
title: "Runbook: User Management (Local Auth)"
status: active
owners: "system-admin"
created: 2025-12-16
system: "skriptoteket-identity"
---

## When to use this runbook

Use this runbook when you need to:
- Bootstrap a new deployment with the first Superuser.
- Create new user accounts manually (since self-signup is disabled).
- Grant roles to users.

**Context:** This applies to the MVP configuration using "Admin-provisioned local accounts".

## Prerequisites

- Access to the server where Docker Compose is running.
- `docker` and `docker compose` permissions.

## Procedures

### 1. Bootstrap the First Admin (Superuser)

Run this only once when setting up a fresh database. It creates a user with the `SUPERUSER` role.

```bash
# Replace 'skriptoteket-web' with your actual container name if different
docker compose exec -it skriptoteket-web python -m skriptoteket.cli bootstrap-superuser \
  --email "admin@example.com"
```

*You will be prompted to enter and confirm a secure password.*

### 2. Provision Additional Users

Use an existing admin/superuser account to create new users.

**Syntax:**
```bash
docker compose exec -it skriptoteket-web python -m skriptoteket.cli provision-user \
  --actor-email "<YOUR_ADMIN_EMAIL>" \
  --email "<NEW_USER_EMAIL>" \
  --role "<ROLE>"
```

**Roles:**
- `user`: Standard access (default).
- `admin`: Can manage tools and basic settings.
- `superuser`: Full system access.

**Example:**
```bash
docker compose exec -it skriptoteket-web python -m skriptoteket.cli provision-user \
  --actor-email "admin@example.com" \
  --email "johndoe@example.com" \
  --role "user"
```

*Prompts:*
1. **Actor Password:** The password for `<YOUR_ADMIN_EMAIL>` (to authorize the request).
2. **New User Password:** Set the initial password for the new user.

## Troubleshooting

**"User already exists"**
- The email is already taken. Use a different email or check the database.

**"Insufficient permissions"**
- Ensure the `--actor-email` belongs to a user with `ADMIN` or `SUPERUSER` role.
- Ensure the actor's password is correct.

**"Invalid admin credentials"**
- Double-check the password for the `--actor-email` account.

