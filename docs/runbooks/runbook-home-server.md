---
type: runbook
id: RUN-home-server
title: "Runbook: Home Server Operations"
status: active
owners: "olof"
created: 2025-12-16
updated: 2026-01-02
system: "hemma.hule.education"
---

Operations guide for the home server hosting Skriptoteket and future HuleEdu services.

## Setup

### Server Access (SSH)

```bash
# Remote admin access (VPN-gated; Tailscale)
ssh hemma           # paunchygent (non-root default)
ssh hemma-root      # root (use only with explicit approval)

# Local network break-glass (LAN)
ssh hemma-local
ssh hemma-local-root
```

Notes:

- SSH is intentionally **not exposed on the public internet** (no router port-forward for `22/tcp`).
- Default user is non-root (`paunchygent`); use `ssh hemma-root` only with explicit approval.
- UFW allows SSH only:
  - On `tailscale0` (VPN), and
  - From the LAN break-glass subnet `192.168.0.0/24`.
- If `ssh hemma` still points at `hemma.hule.education`, update your `~/.ssh/config` so `ssh hemma` uses MagicDNS:

```text
Host hemma
  HostName hemma.tail730aa2.ts.net
  User paunchygent
  IdentityFile ~/.ssh/hemma-paunchygent_ed25519

Host hemma-root
  HostName hemma.tail730aa2.ts.net
  User root

Host hemma-local
  HostName 192.168.0.9
  User paunchygent
  IdentityFile ~/.ssh/hemma-paunchygent_ed25519

Host hemma-local-root
  HostName 192.168.0.9
  User root
```

### SSH Hardening + Fail2ban

Security hardening (sshd settings, Fail2ban jails, nginx-proxy probe jail) is documented in
[ref-home-server-security-hardening.md](../reference/ref-home-server-security-hardening.md).

### SSH/Network Watchdog (Active Remediation)

Runs every 2 minutes and remediates SSH/network drift. It restarts `systemd-networkd`,
`systemd-resolved`, and `tailscaled` if route/ping checks fail, and reboots after 3
consecutive failures.

Script: `/usr/local/bin/ssh-watchdog.sh`

```bash
sudo systemctl status ssh-watchdog.timer --no-pager
sudo journalctl -t ssh-watchdog --since "1 hour ago"
sudo systemctl disable --now ssh-watchdog.timer
```

### Heartbeat Log (Hang Correlation)

Logs a simple heartbeat every minute to make hang windows obvious.

```bash
sudo systemctl status heartbeat-log.timer --no-pager
sudo journalctl -t heartbeat --since "2 hours ago"
```

### Current Network + DDNS Settings (as of 2026-01-02)

```text
# Network (ethernet only; Wi‑Fi disabled)
/etc/cloud/cloud.cfg.d/99-disable-network-config.cfg
  network: {config: disabled}

/etc/netplan/01-netcfg.yaml
  enp7s0: dhcp4=true, dhcp6=false, optional=true

/etc/netplan/50-cloud-init.yaml.disabled
/etc/netplan/50-cloud-init.yaml.bak

systemctl status wpa_supplicant@wlp5s0.service -> inactive (disabled)
```

```text
# DDNS (Namecheap)
systemctl status ddclient -> active
/etc/ddclient.conf
  protocol=namecheap
  server=dynamicdns.park-your-domain.com
  login=hule.education
  host=hemma
```

### Host Logs + Disk Health (hemma)

Log paths (root):

- `/root/logs/incident-YYYYMMDD-HHMMSS-HHMMSS.log` (incident windows)
- `/root/logs/smart/` (SMART snapshots)

SMART monitoring:

- Service: `smartmontools.service`
- Config: `/etc/smartd.conf`

Cleanup (30-day retention):

- Script: `/usr/local/bin/cleanup-smart-logs.sh`
- Timer: `cleanup-smart-logs.timer`

### Repo + Compose Layout (Production)

- App repo: `~/apps/skriptoteket/`
- Production compose: `compose.prod.yaml` (uses `shared-postgres` on `hule-network`)
- Observability stack: `compose.observability.yaml`
- Development compose: `compose.yaml` (local postgres only)

**Critical**: Production uses `compose.prod.yaml`, NOT `compose.yaml`.

Recommended CLI tools + install steps: see [ref-home-server-cli-tools.md](../reference/ref-home-server-cli-tools.md).

### Command Patterns (Use These)

```bash
# 1) Compose commands (from repo root)
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.prod.yaml <command>"

# 2) Run CLI inside web container (compose)
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.prod.yaml exec -T -e PYTHONPATH=/app/src web pdm run python -m skriptoteket.cli <command>"

# 3) Direct docker exec (used by systemd timers)
ssh hemma "/snap/bin/docker exec -e PYTHONPATH=/app/src skriptoteket-web pdm run python -m skriptoteket.cli <command>"
```

Architecture overview diagram: see [ref-home-server-architecture.md](../reference/ref-home-server-architecture.md).

### nginx-proxy (service routing + hardening)

Details for adding new services and edge hardening live in
[ref-home-server-nginx-proxy.md](../reference/ref-home-server-nginx-proxy.md).

## Daily Ops

### Quick Status Check

```bash
# All containers
ssh hemma "sudo docker ps"

# Skriptoteket + core services
ssh hemma "sudo docker ps | grep -E 'skriptoteket|nginx|postgres'"
```


### View Logs

```bash
# Web application logs
ssh hemma "sudo docker logs -f skriptoteket-web"

# Nginx access logs
ssh hemma "sudo docker logs -f nginx-proxy"

# Database logs (check for query errors)
ssh hemma "sudo docker logs -f shared-postgres"
```

Structured logs + correlation IDs: see [runbook-observability-logging.md](runbook-observability-logging.md).

### Restart Services

```bash
# Restart Skriptoteket (preserves network connections)
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.prod.yaml restart"

# Restart observability stack
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.observability.yaml restart"

# nginx-proxy auto-reloads when containers change (no manual reload needed)
```

Note: `docker compose restart` does **not** re-read `.env`. For env var changes use a recreate:

```bash
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.prod.yaml up -d --no-deps --force-recreate web"
```

### Disk Space / Session Cleanup

Session files are stored in `ARTIFACTS_ROOT/sessions/` (prod: `/app/.artifacts/sessions/`). An hourly systemd timer
runs TTL cleanup automatically.

```bash
# Check timer status
ssh hemma "sudo systemctl list-timers | grep skriptoteket"

# View cleanup logs
ssh hemma "sudo journalctl -u skriptoteket-session-files-cleanup.service -n 50 --no-pager"

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

Unit file definitions are in [ref-home-server-cleanup-timers.md](../reference/ref-home-server-cleanup-timers.md) (or inspect on host with
`sudo systemctl cat skriptoteket-sandbox-snapshots-cleanup.service`).

Enable and verify:

```bash
ssh hemma "sudo systemctl daemon-reload"
ssh hemma "sudo systemctl enable --now skriptoteket-sandbox-snapshots-cleanup.timer"
ssh hemma "sudo systemctl list-timers | grep skriptoteket-sandbox-snapshots"
ssh hemma "sudo journalctl -u skriptoteket-sandbox-snapshots-cleanup.service -n 50 --no-pager"
```

Live note (hemma): timer is enabled and runs hourly; see `systemctl status skriptoteket-sandbox-snapshots-cleanup.timer`.

Manual trigger:

```bash
ssh hemma "sudo systemctl start skriptoteket-sandbox-snapshots-cleanup.service"
```

### Login Events Cleanup (DB)

Login event audit rows are retained for 90 days. Cleanup is scheduled server-side via systemd.

Unit file definitions are in [ref-home-server-cleanup-timers.md](../reference/ref-home-server-cleanup-timers.md) (or inspect on host with
`sudo systemctl cat skriptoteket-login-events-cleanup.service`).

Enable and verify:

```bash
ssh hemma "sudo systemctl daemon-reload"
ssh hemma "sudo systemctl enable --now skriptoteket-login-events-cleanup.timer"
ssh hemma "sudo systemctl list-timers | grep skriptoteket-login-events"
ssh hemma "sudo journalctl -u skriptoteket-login-events-cleanup.service -n 50 --no-pager"
```

Manual trigger:

```bash
ssh hemma "sudo systemctl start skriptoteket-login-events-cleanup.service"
```

### SSL Certificate

Check expiry:

```bash
ssh hemma "sudo docker exec nginx-proxy cat /etc/nginx/certs/live/skriptoteket.hule.education/fullchain.pem | openssl x509 -noout -dates"
```

Renew:

```bash
ssh hemma "cd ~/infrastructure && sudo docker compose run --rm certbot renew"
ssh hemma "sudo docker exec nginx-proxy nginx -s reload"
```

## Deploy

### Standard Deploy (Code Changes)

```bash
ssh hemma "cd ~/apps/skriptoteket && git pull && sudo docker compose -f compose.prod.yaml up -d --build"
```

If migrations are needed:

```bash
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.prod.yaml exec web pdm run db-upgrade"
```

### Deploy with Force Recreate

Use when `compose.prod.yaml` changes (networks, volumes, environment).

```bash
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.prod.yaml up -d --force-recreate"
```

### Rollback

```bash
# Check available commits
ssh hemma "cd ~/apps/skriptoteket && git log --oneline -10"

# Checkout previous version
ssh hemma "cd ~/apps/skriptoteket && git checkout <commit-hash>"

# Rebuild and restart
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.prod.yaml up -d --build"
```

## Data

Production uses `shared-postgres` (external container on `hule-network`).

### Connect to Database

```bash
ssh hemma "sudo docker exec -it shared-postgres psql -U postgres -d skriptoteket"
```

### Backup Database

```bash
ssh hemma "sudo docker exec shared-postgres pg_dump -U postgres skriptoteket > ~/backups/skriptoteket-\$(date +%Y%m%d).sql"
```

### Restore Database

```bash
ssh hemma "sudo docker exec -i shared-postgres psql -U postgres -d skriptoteket < ~/backups/skriptoteket-YYYYMMDD.sql"
```

### Run Migrations

```bash
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.prod.yaml exec web pdm run db-upgrade"
```

### Full Database Reset (DANGER)

This destroys all data. Only use for fresh installations. `shared-postgres` is external and not managed by this compose.

```bash
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.prod.yaml down"

# Connect to shared-postgres and drop/recreate database
ssh hemma "sudo docker exec -it shared-postgres psql -U postgres -c 'DROP DATABASE IF EXISTS skriptoteket;'"
ssh hemma "sudo docker exec -it shared-postgres psql -U postgres -c 'CREATE DATABASE skriptoteket;'"

# Restart and run migrations
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.prod.yaml up -d"
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.prod.yaml exec web pdm run db-upgrade"
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.prod.yaml exec -T -e PYTHONPATH=/app/src web pdm run python -m skriptoteket.cli bootstrap-superuser --email admin@hule.education --password 'CHANGE_THIS_PASSWORD'"
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.prod.yaml exec -T -e PYTHONPATH=/app/src web pdm run python -m skriptoteket.cli seed-script-bank --actor-email admin@hule.education --actor-password 'CHANGE_THIS_PASSWORD'"
```

### User Management

See [runbook-user-management.md](runbook-user-management.md) for details.

```bash
# Bootstrap superuser (first-time setup only)
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.prod.yaml exec -T -e PYTHONPATH=/app/src web pdm run python -m skriptoteket.cli bootstrap-superuser --email 'admin@example.com' --password 'SECURE_PASSWORD'"

# Provision additional user
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.prod.yaml exec -T -e PYTHONPATH=/app/src web pdm run python -m skriptoteket.cli provision-user --actor-email 'admin@example.com' --actor-password 'ADMIN_PASSWORD' --email 'user@example.com' --password 'USER_PASSWORD' --role user"
```

### Script Bank Seeding

See [runbook-script-bank-seeding-home-server.md](runbook-script-bank-seeding-home-server.md).

```bash
# Seed all scripts from repository
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.prod.yaml exec -T -e PYTHONPATH=/app/src web pdm run python -m skriptoteket.cli seed-script-bank --actor-email admin@hule.education --actor-password 'PASSWORD'"

# Sync code changes from repo to existing tools
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.prod.yaml exec -T -e PYTHONPATH=/app/src web pdm run python -m skriptoteket.cli seed-script-bank --actor-email admin@hule.education --actor-password 'PASSWORD' --sync-code"
```

## Observability

Observability operations are documented in the dedicated runbooks:

- Overview + access: `docs/runbooks/runbook-observability.md`
- Logs: `docs/runbooks/runbook-observability-logging.md`
- Metrics: `docs/runbooks/runbook-observability-metrics.md`
- Tracing: `docs/runbooks/runbook-observability-tracing.md`

## Troubleshooting

### SSH Unreachable After Reboot

**Symptom**: `ssh hemma` times out even though the server is powered on.

**Common cause**: Network instability or DHCP churn (Wi‑Fi flapping / multiple default routes).

**Fix**:
```bash
# Server should use ethernet only; Wi‑Fi disabled via netplan override.
# Confirm on the server:
ssh hemma "ip -4 addr show enp7s0"
ssh hemma "ip route | head -n 5"

# If needed, check watchdog + heartbeat logs for evidence:
ssh hemma "sudo journalctl -t ssh-watchdog --since '2 hours ago'"
ssh hemma "sudo journalctl -t heartbeat --since '2 hours ago'"

# Incident log captures (if taken):
ssh hemma "sudo ls -1 /root/logs/incident-*.log | tail -n 5"
```

### 502 Bad Gateway

**Symptom**: nginx returns 502 after container restart.

**Cause**: Web container not connected to `hule-network`.

**Fix**:
```bash
# Verify network membership
ssh hemma "sudo docker network inspect hule-network --format '{{json .Containers}}' | python3 -m json.tool | grep skriptoteket"

# If missing, reconnect manually (temporary fix)
ssh hemma "sudo docker network connect hule-network skriptoteket-web"

# Permanent fix: redeploy with compose.prod.yaml
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.prod.yaml up -d --force-recreate"
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
ssh hemma "sudo docker logs skriptoteket-web --tail 50"
```

**Fix**:
```bash
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.prod.yaml exec web pdm run db-upgrade"
```

### CLI Commands Fail with "No module named 'skriptoteket'"

**Cause**: PYTHONPATH not set for PEP 582 mode.

**Fix**: Always include `-e PYTHONPATH=/app/src` when running CLI commands:
```bash
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.prod.yaml exec -T -e PYTHONPATH=/app/src web pdm run python -m skriptoteket.cli <command>"
```

### Container Won't Start

```bash
# Check logs for errors
ssh hemma "sudo docker logs skriptoteket-web 2>&1 | tail -50"

# Check if port is in use
ssh hemma "lsof -i :8000"
```

### DNS Not Resolving

```bash
# Check DDNS status
ssh hemma "sudo systemctl status ddclient"

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
ssh hemma "sudo docker system df"

# Clean up unused Docker resources
ssh hemma "sudo docker system prune -f"

# Prune old artifact directories
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.prod.yaml exec -T -e PYTHONPATH=/app/src web pdm run python -m skriptoteket.cli prune-artifacts"
```
