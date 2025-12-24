---
type: runbook
id: RUN-user-management
title: "Runbook: User Management (Local Auth)"
status: active
owners: "system-admin"
created: 2025-12-16
updated: 2025-12-16
system: "skriptoteket-identity"
---

## When to use this runbook

Use this runbook when you need to:

- Bootstrap a new deployment with the first Superuser.
- Create new user accounts manually (since self-signup is disabled).
- Change a user's password.
- Grant roles to users.

**Context:** This applies to the MVP configuration using "Admin-provisioned local accounts".

## Prerequisites

- SSH access to the server
- Docker running with the web container (`skriptoteket_web`)

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
ssh hemma "cd ~/apps/skriptoteket && docker compose exec -T -e PYTHONPATH=/app/src web pdm run python -m skriptoteket.cli bootstrap-superuser --email 'admin@example.com' --password 'SECURE_PASSWORD'"
```

**Interactive mode** (prompts for password):
```bash
ssh hemma
cd ~/apps/skriptoteket
docker compose exec -e PYTHONPATH=/app/src web pdm run python -m skriptoteket.cli bootstrap-superuser --email 'admin@example.com'
```

### 2. Provision Additional Users

Use an existing admin/superuser account to create new users.

```bash
ssh hemma "cd ~/apps/skriptoteket && docker compose exec -T -e PYTHONPATH=/app/src web pdm run python -m skriptoteket.cli provision-user --actor-email 'admin@example.com' --actor-password 'ADMIN_PASSWORD' --email 'newuser@example.com' --password 'USER_PASSWORD' --role user"
```

**Available roles:** `user`, `contributor`, `admin`, `superuser`

**Interactive mode:**
```bash
ssh hemma
cd ~/apps/skriptoteket
docker compose exec -e PYTHONPATH=/app/src web pdm run python -m skriptoteket.cli provision-user --actor-email 'admin@example.com' --email 'newuser@example.com' --role user
```

### 3. Change User Password

There is no CLI command for password changes. Use direct database update with a new Argon2 hash.

**Step 1: Generate new password and hash**
```bash
ssh hemma "cd ~/apps/skriptoteket && docker compose exec -T -e PYTHONPATH=/app/src web pdm run python -c \"
from skriptoteket.infrastructure.security.password_hasher import Argon2PasswordHasher
import secrets
import string

chars = string.ascii_letters + string.digits + '!@#'
password = ''.join(secrets.choice(chars) for _ in range(16))

hasher = Argon2PasswordHasher()
hash = hasher.hash(password=password)

print(f'NEW_PASSWORD={password}')
print(f'HASH={hash}')
\""
```

**Step 2: Update database** (replace the hash and email)
```bash
ssh hemma "docker exec skriptoteket-db-1 psql -U postgres -d skriptoteket -c \"UPDATE users SET password_hash = 'THE_HASH_FROM_STEP_1' WHERE email = 'user@example.com';\""
```

**Note:** The hash contains `$` characters that need escaping in shell. Use single quotes and escape `$` as `\$` if needed.

### 4. List All Users

```bash
ssh hemma "docker exec skriptoteket-db-1 psql -U postgres -d skriptoteket -c \"SELECT id, email, role, created_at FROM users ORDER BY created_at;\""
```

### 5. Change User Role

```bash
ssh hemma "docker exec skriptoteket-db-1 psql -U postgres -d skriptoteket -c \"UPDATE users SET role = 'admin' WHERE email = 'user@example.com';\""
```

### 6. Delete User

```bash
ssh hemma "docker exec skriptoteket-db-1 psql -U postgres -d skriptoteket -c \"DELETE FROM users WHERE email = 'user@example.com';\""
```

**Warning:** This may fail if the user has related records (sessions, tool versions, etc.). You may need to delete related records first or use cascading deletes.

## Troubleshooting

### "User already exists"

The email is already taken. Check existing users:
```bash
ssh hemma "docker exec skriptoteket-db-1 psql -U postgres -d skriptoteket -c \"SELECT email FROM users;\""
```

### "Insufficient permissions"

The actor must have `ADMIN` or `SUPERUSER` role to provision users.

### "Invalid admin credentials"

Double-check the password for the actor account.

### "No module named 'skriptoteket'"

Missing PYTHONPATH. Always use:
```bash
docker compose exec -T -e PYTHONPATH=/app/src web pdm run python -m skriptoteket.cli ...
```

### Session Issues After Password Change

User sessions remain valid after password change. To force re-login, delete sessions:
```bash
ssh hemma "docker exec skriptoteket-db-1 psql -U postgres -d skriptoteket -c \"DELETE FROM sessions WHERE user_id = (SELECT id FROM users WHERE email = 'user@example.com');\""
```
