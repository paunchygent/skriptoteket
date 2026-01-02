---
type: runbook
id: RUN-home-server
title: "Runbook: Home Server Operations"
status: active
owners: "olof"
created: 2025-12-16
updated: 2026-01-01
system: "hemma.hule.education"
---

Operations guide for the home server hosting Skriptoteket and future HuleEdu services.

## Setup

### Server Access (SSH)

```bash
# Remote admin access (VPN-gated; Tailscale)
ssh hemma

# Local network break-glass (LAN)
ssh hemma-local
```

Notes:

- SSH is intentionally **not exposed on the public internet** (no router port-forward for `22/tcp`).
- UFW allows SSH only:
  - On `tailscale0` (VPN), and
  - From the LAN break-glass subnet `192.168.0.0/24`.
- If `ssh hemma` still points at `hemma.hule.education`, update your `~/.ssh/config` so `ssh hemma` uses MagicDNS:

```text
Host hemma
  HostName hemma.tail730aa2.ts.net
  User root

Host hemma-local
  HostName 192.168.0.9
  User root
```

### SSH Hardening (Checklist)

```bash
sudo nano /etc/ssh/sshd_config.d/99-hardening.conf
```

```text
PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
PermitRootLogin prohibit-password
AllowUsers root paunchygent
```

```bash
sudo sshd -t
sudo systemctl reload ssh
sudo install -d -m 700 /root/.ssh
sudo tee -a /root/.ssh/authorized_keys
sudo chmod 600 /root/.ssh/authorized_keys
```

### Fail2ban (Checklist)

```bash
sudo apt install fail2ban
sudo nano /etc/fail2ban/jail.d/sshd.local
```

```text
[sshd]
enabled = true
backend = systemd
maxretry = 5
findtime = 10m
bantime = 1h
```

```bash
sudo systemctl enable --now fail2ban
sudo fail2ban-client status sshd
sudo fail2ban-client get sshd banip
sudo fail2ban-client set sshd unbanip <ip>
```

#### Recidive jail (3 strikes → permaban)

This enforces a "repeat offenders get permabanned" policy based on Fail2ban's own log (including rotated logs).

```bash
sudo nano /etc/fail2ban/jail.d/recidive.local
```

```text
[recidive]
enabled = true
logpath = /var/log/fail2ban.log*
banaction = nftables[type=allports]

# 3 strikes within 7 days => permaban
findtime = 7d
maxretry = 3
bantime = -1
```

```bash
sudo systemctl restart fail2ban
sudo fail2ban-client status recidive
```

#### nginx-proxy probe jail (HTTP scanners)

Ban repeat HTTP scanners hitting `nginx-proxy` (e.g. paths dropped with `444`, repeated `401/403` auth probes).

Files (hemma):

- Filter: `/etc/fail2ban/filter.d/nginx-proxy-probe.conf`
- Jail: `/etc/fail2ban/jail.d/nginx-proxy-probe.local`

Key settings:

- `backend = polling` (avoid `systemd` backend without precise `journalmatch`)
- `logpath = /var/snap/docker/common/var-lib-docker/containers/*/*-json.log` (snap docker)
- `usedns = no` (logs include both vhost and client IP; only ban client IP)
- `banaction = nftables[type=allports]` (cuts off multi-port probing)

Restart and verify:

```bash
sudo systemctl restart fail2ban
sudo fail2ban-client status nginx-proxy-probe
sudo fail2ban-client get nginx-proxy-probe logpath
sudo fail2ban-client get nginx-proxy-probe banip
sudo fail2ban-client set nginx-proxy-probe unbanip <ip>
```

### SSH/Network Watchdog (Logs Only)

Runs every 2 minutes and logs if SSH or network health degrades (no changes applied).

```bash
sudo systemctl status ssh-watchdog.timer --no-pager
journalctl -t ssh-watchdog --since "1 hour ago"
sudo systemctl disable --now ssh-watchdog.timer
```

### Current Network + DDNS Settings (as of 2026-01-01)

```text
# Network (ethernet only; Wi‑Fi disabled)
/etc/cloud/cloud.cfg.d/99-disable-network-config.cfg
  network: {config: disabled}

/etc/netplan/01-netcfg.yaml
  enp7s0: dhcp4=true, dhcp6=false, optional=true

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

### Repo + Compose Layout (Production)

- App repo: `~/apps/skriptoteket/`
- Production compose: `compose.prod.yaml` (uses `shared-postgres` on `hule-network`)
- Observability stack: `compose.observability.yaml`
- Development compose: `compose.yaml` (local postgres only)

**Critical**: Production uses `compose.prod.yaml`, NOT `compose.yaml`.

### Recommended CLI Tools (hemma)

```bash
# Core helpers
ssh hemma "sudo apt-get update && sudo apt-get install -y ripgrep fd-find bat fzf jq tree"

# Make the commands match common expectations (Ubuntu names them batcat/fdfind)
ssh hemma "sudo ln -sf /usr/bin/batcat /usr/local/bin/bat && sudo ln -sf /usr/bin/fdfind /usr/local/bin/fd"

# Install mikefarah/yq v4 (apt 'yq' is not v4)
ssh hemma "sudo curl -fsSL https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64 -o /usr/local/bin/yq && sudo chmod +x /usr/local/bin/yq"
```

Notes:

- `ripgrep` provides `rg`
- `fd-find` provides `fdfind` (symlinked to `fd`)
- `bat` provides `batcat` (symlinked to `bat`)
- `yq` is installed to `/usr/local/bin/yq` so it wins over `/usr/bin/yq`

### Command Patterns (Use These)

```bash
# 1) Compose commands (from repo root)
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.prod.yaml <command>"

# 2) Run CLI inside web container (compose)
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.prod.yaml exec -T -e PYTHONPATH=/app/src web pdm run python -m skriptoteket.cli <command>"

# 3) Direct docker exec (used by systemd timers)
ssh hemma "/snap/bin/docker exec -e PYTHONPATH=/app/src skriptoteket-web pdm run python -m skriptoteket.cli <command>"
```

### Architecture Overview

```text
┌─────────────────────────────────────────────────────────────┐
│                        Internet                              │
└────────────────────────────┬────────────────────────────────┘
                             │ :80/:443 (HTTP/HTTPS)
┌────────────────────────────▼────────────────────────────────┐
│  nginx-proxy (nginxproxy/nginx-proxy:1.6)                    │
│  - Auto-discovers containers via VIRTUAL_HOST env var        │
│  - SSL termination (certs from acme-companion)               │
│  - Routes: skriptoteket.hule.education → skriptoteket-web   │
│            grafana.hemma.hule.education → grafana           │
│            prometheus.hemma.hule.education → prometheus     │
├──────────────────────────────────────────────────────────────┤
│  acme-companion (nginxproxy/acme-companion:2.4)              │
│  - Auto-generates Let's Encrypt certificates                 │
│  - Listens for LETSENCRYPT_HOST env vars on containers       │
│  - Auto-renews before expiry                                 │
└────────────────────────────┬────────────────────────────────┘
                             │
    ┌────────────────────────┼────────────────────────┐
    │                        │                        │
    ▼                        ▼                        ▼
┌─────────────┐      ┌─────────────┐         ┌─────────────┐
│ skriptoteket │      │   grafana   │         │ prometheus  │
│     :8000    │      │    :3000    │         │    :9090    │
└─────────────┘      └─────────────┘         └─────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  shared-postgres (hule-network)                              │
│  - PostgreSQL 16 (shared across services)                   │
│  - Data in persistent volume                                │
└─────────────────────────────────────────────────────────────┘
```

### Add a New Service to nginx-proxy

Add these env vars to the service and expose its internal port:

```yaml
environment:
  - VIRTUAL_HOST=myservice.hemma.hule.education
  - VIRTUAL_PORT=8080  # Internal port the service listens on
  - LETSENCRYPT_HOST=myservice.hemma.hule.education
expose:
  - "8080"
```

Then add a DNS A record for `myservice.hemma` pointing to `83.252.61.217` (or your current IP).
The acme-companion will automatically generate SSL certificates.

### nginx-proxy edge hardening (drop probes / unknown hosts)

We proactively drop common scanner traffic at the reverse proxy so the app layer never sees it.

Key settings/files:

- `DEFAULT_HOST=skriptoteket.hule.education` in `~/infrastructure/docker-compose.yml` (nginx-proxy) to avoid a generated `server_name _` that returns `503`.
- vhost snippets live in the nginx-proxy volume at `/etc/nginx/vhost.d/`:
  - `global-hardening.conf`: blocks common probes (e.g. `/.env`, `/.git`, `wp-*`, `*.php`, `cgi-bin`, WebDAV methods) with `444`.
  - `default`: includes `global-hardening.conf` (applies to all vhosts).
  - `skriptoteket.hule.education`: includes `global-hardening.conf` and drops unexpected `Host` headers on the default server.

Inspect/reload:

```bash
ssh hemma "sudo docker exec nginx-proxy ls -la /etc/nginx/vhost.d"
ssh hemma "sudo docker exec nginx-proxy sed -n '1,200p' /etc/nginx/vhost.d/global-hardening.conf"
ssh hemma "sudo docker exec nginx-proxy nginx -s reload"
```

### Infrastructure Layout

```text
~/apps/skriptoteket/           # Application repository
  compose.prod.yaml            # Production compose (uses shared-postgres)
  compose.yaml                 # Development compose (local postgres)
  compose.observability.yaml   # Observability stack (independent lifecycle)
  Dockerfile                   # Web app image
  Dockerfile.runner            # Script runner image
  .env                         # Local environment (never commit)

~/infrastructure/              # Shared infrastructure (nginx-proxy + acme-companion + postgres)
  docker-compose.yml           # nginx-proxy, acme-companion, shared-postgres
  .env                         # POSTGRES_ADMIN_PASSWORD, LETSENCRYPT_EMAIL
  postgres/
    init/                      # DB init scripts (create databases/users)
```

### Infrastructure Compose Services

| Service | Image | Purpose |
|---------|-------|---------|
| `nginx-proxy` | `nginxproxy/nginx-proxy:1.6` | Auto-configuring reverse proxy |
| `acme-companion` | `nginxproxy/acme-companion:2.4` | Auto SSL certificate management |
| `shared-postgres` | `postgres:16-alpine` | Shared PostgreSQL for all services |

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

**Tip**: Skriptoteket logs are structured (JSON in production) and support `X-Correlation-ID` for cross-request
debugging. See [runbook-observability.md](runbook-observability.md).

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
ssh hemma "systemctl list-timers | grep skriptoteket"

# View cleanup logs
ssh hemma "journalctl -u skriptoteket-session-files-cleanup.service -n 50 --no-pager"

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

Unit files:

```ini
# /etc/systemd/system/skriptoteket-sandbox-snapshots-cleanup.service
[Unit]
Description=Skriptoteket sandbox snapshot cleanup
Requires=snap.docker.dockerd.service
After=snap.docker.dockerd.service

[Service]
Type=oneshot
ExecStart=/snap/bin/docker exec -e PYTHONPATH=/app/src skriptoteket-web pdm run python -m skriptoteket.cli cleanup-sandbox-snapshots
```

```ini
# /etc/systemd/system/skriptoteket-sandbox-snapshots-cleanup.timer
[Unit]
Description=Run sandbox snapshot cleanup hourly

[Timer]
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and verify:

```bash
ssh hemma "sudo systemctl daemon-reload"
ssh hemma "sudo systemctl enable --now skriptoteket-sandbox-snapshots-cleanup.timer"
ssh hemma "systemctl list-timers | grep skriptoteket-sandbox-snapshots"
ssh hemma "journalctl -u skriptoteket-sandbox-snapshots-cleanup.service -n 50 --no-pager"
```

Live note (hemma): timer is enabled and runs hourly; see `systemctl status skriptoteket-sandbox-snapshots-cleanup.timer`.

Manual trigger:

```bash
ssh hemma "sudo systemctl start skriptoteket-sandbox-snapshots-cleanup.service"
```

### Login Events Cleanup (DB)

Login event audit rows are retained for 90 days. Cleanup is scheduled server-side via systemd.

Unit files:

```ini
# /etc/systemd/system/skriptoteket-login-events-cleanup.service
[Unit]
Description=Skriptoteket login events cleanup
Requires=snap.docker.dockerd.service
After=snap.docker.dockerd.service

[Service]
Type=oneshot
ExecStart=/snap/bin/docker exec -e PYTHONPATH=/app/src skriptoteket-web pdm run python -m skriptoteket.cli cleanup-login-events
```

```ini
# /etc/systemd/system/skriptoteket-login-events-cleanup.timer
[Unit]
Description=Run login events cleanup daily

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and verify:

```bash
ssh hemma "sudo systemctl daemon-reload"
ssh hemma "sudo systemctl enable --now skriptoteket-login-events-cleanup.timer"
ssh hemma "systemctl list-timers | grep skriptoteket-login-events"
ssh hemma "journalctl -u skriptoteket-login-events-cleanup.service -n 50 --no-pager"
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

The observability stack runs independently via `compose.observability.yaml`.

### Start/Stop

```bash
# Start observability stack
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.observability.yaml up -d"

# Stop observability stack
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.observability.yaml down"

# Restart (e.g., after config changes)
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.observability.yaml restart"
```

### Components

| Service | Port | URL | Purpose |
|---------|------|-----|---------|
| Grafana | 3000 | https://grafana.hemma.hule.education | Dashboards |
| Prometheus | 9090 | https://prometheus.hemma.hule.education | Metrics |
| Jaeger | 16686 | https://jaeger.hemma.hule.education | Tracing |
| Loki | 3100 | - | Log aggregation |
| Promtail | - | - | Log collection |

Prometheus and Jaeger are protected by basic auth; see `docs/runbooks/runbook-observability.md` for access notes.

### View Observability Logs

```bash
ssh hemma "sudo docker logs -f grafana"
ssh hemma "sudo docker logs -f prometheus"
ssh hemma "sudo docker logs -f jaeger"
ssh hemma "sudo docker logs -f loki"
```

### Metrics

```bash
# Via metrics endpoint
ssh hemma "curl -s https://skriptoteket.hule.education/metrics | grep skriptoteket_session_files"

# Example output:
# skriptoteket_session_files_bytes_total 12345.0
# skriptoteket_session_files_count 42.0
```

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

# If needed, check watchdog logs for evidence:
ssh hemma "journalctl -t ssh-watchdog --since '2 hours ago'"
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
ssh hemma "systemctl status ddclient"

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
