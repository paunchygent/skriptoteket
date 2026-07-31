---
type: runbook
id: RUN-SKRIPT-runbook-home-server-operations-PART-03
title: 'Runbook: Home Server Operations — part 03'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
root: RUN-SKRIPT-runbook-home-server-operations
part: 3
---

```bash
ssh hemma /bin/bash -s <<'EOF'
set -euo pipefail
cd /home/paunchygent/apps/skriptoteket
./scripts/hemma_deploy_and_verify_seating_export.sh
EOF
```

### Manual Deploy Steps (fallback / debugging)

```bash
### Build runner image (required for tool/editor sandbox runs)
ssh hemma "cd ~/apps/skriptoteket && git pull && sudo docker compose -f compose.prod.yaml --profile build-only build runner"

### Deploy web + worker (app + queue consumer)
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.prod.yaml up -d --build"
```

If you only changed Conversion Hub env vars, recreating `web` is sufficient:

```bash
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.prod.yaml up -d --no-deps --force-recreate web"
```

If you need to run the production export verification steps manually after a deploy:

```bash
ssh hemma "sudo docker exec -e PYTHONPATH=/app/src -e BOOTSTRAP_SUPERUSER_EMAIL='<email>' -e BOOTSTRAP_SUPERUSER_PASSWORD='<password>' skriptoteket-web pdm run python -m skriptoteket.cli smoke-seating-export-readiness > /tmp/skriptoteket-seat-export-smoke.json"
```

The cutover contract is now local: no Sir Convert webhook inventory or reconciliation step is part of the
supported seating export deploy gate anymore.

If migrations are needed:

```bash
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.prod.yaml exec web pdm run db-upgrade"
```

### Security hardening verification (required when edge/runtime policy changes)

Run this when a deploy touches host validation, proxy trust, observability, or nginx routing:

```bash
ssh hemma /bin/bash -s <<'EOF'
set -euo pipefail
sudo docker exec skriptoteket-web curl -sS http://127.0.0.1:8000/healthz
printf '\n---\n'
sudo docker exec skriptoteket-web /bin/sh -lc "curl -sS http://127.0.0.1:8000/metrics | rg 'skriptoteket_users_by_role|skriptoteket_active_sessions' || true"
EOF

curl -sS -D - -o /dev/null https://skriptoteket.hule.education/docs
curl -sS -D - -o /dev/null https://skriptoteket.hule.education/openapi.json
curl -sS -D - -o /dev/null https://skriptoteket.hule.education/metrics
curl -sS https://skriptoteket.hule.education/healthz
echo | openssl s_client -connect hule.education:443 -servername hule.education 2>/dev/null \
  | openssl x509 -noout -subject -ext subjectAltName
echo | openssl s_client -connect api.hule.education:443 -servername api.hule.education 2>/dev/null \
  | openssl x509 -noout -subject -ext subjectAltName
echo | openssl s_client -connect ws.hule.education:443 -servername ws.hule.education 2>/dev/null \
  | openssl x509 -noout -subject -ext subjectAltName
```

Expected results:

- public `/docs` and `/openapi.json` return `404`
- public `/metrics` returns `403`
- public `/healthz` returns the minimal healthy payload
- in-container `/metrics` does not emit `skriptoteket_active_sessions` or `skriptoteket_users_by_role`
- HuleEdu hosts serve their own certificates and do not inherit the
  Skriptoteket/default-host certificate or backend

### Deploy with Force Recreate

Use when `compose.prod.yaml` changes (networks, volumes, environment).

```bash
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.prod.yaml up -d --force-recreate"
```

### Rollback

```bash
### Check available commits
ssh hemma "cd ~/apps/skriptoteket && git log --oneline -10"

### Checkout previous version
ssh hemma "cd ~/apps/skriptoteket && git checkout <commit-hash>"

### Rebuild and restart
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.prod.yaml up -d --build"
```

### Data

Production uses `shared-postgres` (external container on `hule-network`).

### Connect to Database

```bash
ssh hemma "sudo docker exec -it shared-postgres psql -U postgres -d skriptoteket"
```

### Backup Database

```bash
ssh hemma "cd /home/paunchygent/apps/huleedu && pdm run run-local-pdm shared-postgres-backup run --execute"
```

Production backup payloads for `shared-postgres` belong under
`/srv/storage/hemma/shared-postgres/backups/`, not under `~/backups`. Use the
HuleEdu governed `shared-postgres-backup verify --latest` and
`shared-postgres-backup restore-test --latest` commands for manifest and
disposable restore proof.

### Restore Database

Production restores are incident operations. Do not pipe ad hoc SQL from
home-directory backups into `shared-postgres`; open an incident task, select a
verified manifest under `/srv/storage/hemma/shared-postgres/backups/`, and
record the restore plan before touching production data.

### Run Migrations

```bash
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.prod.yaml exec web pdm run db-upgrade"
```

### Full Database Reset (DANGER)

This destroys all data. Only use for fresh installations. `shared-postgres` is external and not managed by this compose.

```bash
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.prod.yaml down"

### Connect to shared-postgres and drop/recreate database
ssh hemma "sudo docker exec -it shared-postgres psql -U postgres -c 'DROP DATABASE IF EXISTS skriptoteket;'"
ssh hemma "sudo docker exec -it shared-postgres psql -U postgres -c 'CREATE DATABASE skriptoteket;'"

### Restart and run migrations
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.prod.yaml up -d"
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.prod.yaml exec web pdm run db-upgrade"
```

Then follow:

- [runbook-user-management.md](runbook-user-management.md) (bootstrap superuser / provision)
- [runbook-script-bank-seeding-home-server.md](runbook-script-bank-seeding-home-server.md) (seed script bank)

### User Management

See [runbook-user-management.md](runbook-user-management.md) for details.

### Script Bank Seeding

See [runbook-script-bank-seeding-home-server.md](runbook-script-bank-seeding-home-server.md).

### Observability

Observability operations are documented in the dedicated runbooks:

- Overview + access: `docs/runbooks/runbook-observability.md`
- Logs: `docs/runbooks/runbook-observability-logging.md`
- Metrics: `docs/runbooks/runbook-observability-metrics.md`
- Tracing: `docs/runbooks/runbook-observability-tracing.md`

### Troubleshooting

### SSH Unreachable After Reboot

**Symptom**: `ssh hemma` times out even though the server is powered on.

**Common cause**: Network instability or DHCP churn (Wi‑Fi flapping / multiple default routes).

**Fix**:

```bash
### Server should use ethernet only; Wi‑Fi disabled via netplan override.
### Confirm on the server:
ssh hemma "ip -4 addr show enp7s0"
ssh hemma "ip route | head -n 5"

### If needed, check watchdog logs for evidence:
ssh hemma "sudo journalctl -t health-watchdog --since '2 hours ago'"
ssh hemma "sudo journalctl -t heartbeat --since '2 hours ago'"

### Incident log captures (if taken):
ssh hemma "sudo ls -1 /root/logs/incident-*.log | tail -n 5"
```

### Incident Log Capture (Periodic)

Skriptoteket runs a lightweight periodic capture to preserve the last few minutes of logs plus GPU state.

- Script: `/usr/local/bin/skriptoteket-incident-capture.sh`
- Logs: `/root/logs/incident-*.log`
- Systemd: `skriptoteket-incident-capture.service` + `skriptoteket-incident-capture.timer`
- Defaults: every 5 minutes, 10-minute window, 7-day retention
- Includes: system + kernel logs, llama/tabby service logs, GPU runtime state, `rocm-smi` power/temps/clocks, and
  `/sys/class/hwmon` snapshot (uses `sensors` if installed).
- Alert thresholds (override via env): `INCIDENT_GPU_EDGE_WARN_C`, `INCIDENT_GPU_JUNCTION_WARN_C`,
  `INCIDENT_GPU_MEM_WARN_C`, `INCIDENT_GPU_PPT_WARN_W`, `INCIDENT_CPU_TCTL_WARN_C`.

Check status:

```bash
ssh hemma "sudo systemctl status --no-pager skriptoteket-incident-capture.timer"
ssh hemma "sudo ls -1 /root/logs/incident-*.log | tail -n 5"
```

### Power Rail Logging (PSU / Super I/O)

Tracks PSU rail health via lm-sensors + the IT8665E Super I/O chip. This helps identify power
loss or rail droop when the host wedges without a clean reboot.

Components:

- Package: `lm-sensors`
- Driver: out-of-tree `it87` DKMS module (supports **IT8665E**)
  - Source: `/usr/src/it87` (repo: frankcrawford/it87)
  - Auto-load: `/etc/modules-load.d/it87.conf`
- Script: `/usr/local/bin/log-power-rails.sh`
- Systemd: `log-power-rails.service` + `log-power-rails.timer`

Logs:

- Snapshot logs: `/root/logs/power-rails/sensors-*.log` (30-day retention)
- Alerts: `/root/logs/power-rails/alerts.log` (append-only; only writes on threshold breach)

Alert thresholds (default):

- `3VSB`: 3.00–3.60 V
- `+3.3V`: 3.00–3.60 V
- `Vbat`: 2.70–3.40 V
- `+12V`: 11.40–12.60 V (computed from `in2` * 6)
- `+5V`: 4.75–5.25 V (computed from `in3` * 2.5)

Notes:

- The `+12V/+5V` mapping follows the ASUS PRIME B350 config in the it87 repo; verify against
  PRIME X370-PRO if the rails look off.
- Avoid `ignore_resource_conflict=1` unless required; it can destabilize the host.
- DKMS should rebuild on kernel updates. If sensors disappear, re-run:
  `ssh hemma "cd /usr/src/it87 && sudo ./dkms-install.sh"`

Quick checks:

```bash
ssh hemma "sudo systemctl status --no-pager log-power-rails.timer"
ssh hemma "sudo ls -t /root/logs/power-rails | head -n 5"
ssh hemma "sudo tail -n 20 /root/logs/power-rails/alerts.log"
```

### 502 Bad Gateway

**Symptom**: nginx returns 502 after container restart.

**Cause**: Web container not connected to `hule-network`.

**Fix**:

```bash
### Verify network membership
ssh hemma "sudo docker network inspect hule-network --format '{{json .Containers}}' | python3 -m json.tool | grep skriptoteket"

### If missing, reconnect manually (temporary fix)
ssh hemma "sudo docker network connect hule-network skriptoteket-web"

### Permanent fix: redeploy with compose.prod.yaml
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
### Check web container logs for "relation does not exist" errors
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
### Check logs for errors
ssh hemma "sudo docker logs skriptoteket-web 2>&1 | tail -50"

### Check if port is in use
ssh hemma "lsof -i :8000"
```

### DNS Not Resolving

```bash
### Check DDNS status
ssh hemma "sudo systemctl status ddclient"

### Force DDNS update
ssh hemma "ddclient -force"

### Check external IP
ssh hemma "curl -s ifconfig.me"

### Verify DNS at nameserver
dig +short skriptoteket.hule.education @pdns1.registrar-servers.com
```

### Disk Space

```bash
### Check disk usage
ssh hemma "df -h"

### Docker disk usage
ssh hemma "sudo docker system df"

### Clean up unused Docker resources
ssh hemma "sudo docker system prune -f"

### Prune old artifact directories
### (includes platform-only LLM captures under /app/.artifacts/llm-captures/)
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.prod.yaml exec -T -e PYTHONPATH=/app/src web pdm run python -m skriptoteket.cli prune-artifacts"
```

## Expected Results

The system reaches the source record's stated healthy or verified state, with command output or operator evidence retained.

## Stop Conditions

Stop on failed preconditions, unexpected state, missing authority, or any action outside the bounded procedure.

## Rollback

Use the source recovery or rollback boundary; escalate when the source does not define a safe reversal.
