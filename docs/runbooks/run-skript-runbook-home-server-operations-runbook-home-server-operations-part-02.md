---
type: runbook
id: RUN-SKRIPT-runbook-home-server-operations-PART-02
title: 'Runbook: Home Server Operations — part 02'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
root: RUN-SKRIPT-runbook-home-server-operations
part: 2
---

```bash
### Boot timeline
ssh hemma "journalctl --list-boots | tail -n 10"

### Current and previous boot logs
ssh hemma "journalctl -b 0 --no-pager"
ssh hemma "journalctl -b -1 --no-pager"
```

SMART monitoring:

- Service: `smartmontools.service`
- Config: `/etc/smartd.conf`

Cleanup (30-day retention):

- Script: `/usr/local/bin/cleanup-smart-logs.sh`
- Timer: `cleanup-smart-logs.timer`

### Repo + Compose Layout (Production)

- App repo: `~/apps/skriptoteket/`
- Production compose: `compose.prod.yaml` (uses `shared-postgres` on `hule-network`)
- Runtime services (production compose):
  - `web` (`skriptoteket-web`): FastAPI app
  - `worker` (`skriptoteket-worker`): Postgres execution queue worker loop (ADR-0062)
- Observability stack: `compose.observability.yaml`
- Development compose: `compose.yaml` (local postgres only)

**Critical**: Production uses `compose.prod.yaml`, NOT `compose.yaml`.

Recommended CLI tools + install steps: see [ref-home-server-cli-tools.md](../reference/ref-home-server-cli-tools.md).

### Command Patterns (Use These)

```bash
### 1) Compose commands (from repo root)
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.prod.yaml <command>"

### 2) Run CLI inside web container (compose)
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.prod.yaml exec -T -e PYTHONPATH=/app/src web pdm run python -m skriptoteket.cli <command>"

### 3) Direct docker exec (used by systemd timers)
ssh hemma "/snap/bin/docker exec -e PYTHONPATH=/app/src skriptoteket-web pdm run python -m skriptoteket.cli <command>"
```

Architecture overview diagram: see [ref-home-server-architecture.md](../reference/ref-home-server-architecture.md).

### nginx-proxy (service routing + hardening)

Details for adding new services and edge hardening live in
[ref-home-server-nginx-proxy.md](../reference/ref-home-server-nginx-proxy.md).

### Daily Ops

### Quick Status Check

```bash
### All containers
ssh hemma "sudo docker ps"

### Skriptoteket + core services
ssh hemma "sudo docker ps | grep -E 'skriptoteket|nginx|postgres'"

### Skriptoteket (compose services)
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.prod.yaml ps"
```

### View Logs

```bash
### Web application logs
ssh hemma "sudo docker logs -f skriptoteket-web"

### Worker logs (execution queue)
ssh hemma "sudo docker logs -f skriptoteket-worker"

### Nginx access logs
ssh hemma "sudo docker logs -f nginx-proxy"

### Database logs (check for query errors)
ssh hemma "sudo docker logs -f shared-postgres"
```

Structured logs + correlation IDs: see [runbook-observability-logging.md](runbook-observability-logging.md).

### Worker Healthcheck

The execution worker has a dependency healthcheck (DB + Docker socket + artifacts volume).

```bash
ssh hemma "sudo docker exec -e PYTHONPATH=/app/src skriptoteket-worker pdm run python -m skriptoteket.cli healthcheck-execution-worker"
```

### Restart Services

```bash
### Restart Skriptoteket (preserves network connections)
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.prod.yaml restart"

### Restart only the worker (execution queue)
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.prod.yaml restart worker"

### Restart observability stack
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.observability.yaml restart"

### nginx-proxy auto-reloads when containers change (no manual reload needed)
```

Note: `docker compose restart` does **not** re-read `.env`. For env var changes use a recreate:

```bash
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.prod.yaml up -d --no-deps --force-recreate web"
```

Important: updating the env file is not enough on its own. `compose.prod.yaml` must also pass the variable through to
the target service. Conversion Hub, for example, requires `SIR_CONVERT_A_LOT_V2_BASE_URL` and
`SIR_CONVERT_A_LOT_V2_API_KEY` to be wired into both the `web` and `worker` service environments.

If the change affects worker configuration, recreate worker too:

```bash
ssh hemma "cd ~/apps/skriptoteket && sudo docker compose -f compose.prod.yaml up -d --no-deps --force-recreate worker"
```

### Disk Space / Session Cleanup

Session files are stored in `ARTIFACTS_ROOT/sessions/` (prod: `/app/.artifacts/sessions/`). An hourly systemd timer
runs TTL cleanup automatically.

```bash
### Check timer status
ssh hemma "sudo systemctl list-timers | grep skriptoteket"

### View cleanup logs
ssh hemma "sudo journalctl -u skriptoteket-session-files-cleanup.service -n 50 --no-pager"

### Manual trigger (if needed)
ssh hemma "sudo systemctl start skriptoteket-session-files-cleanup.service"
```

Manual cleanup commands:

```bash
### TTL-based cleanup (same as timer runs)
ssh hemma "/snap/bin/docker exec -e PYTHONPATH=/app/src skriptoteket-web pdm run python -m skriptoteket.cli cleanup-session-files"

### DANGER: Delete ALL session files (requires --yes)
ssh hemma "/snap/bin/docker exec -e PYTHONPATH=/app/src skriptoteket-web pdm run python -m skriptoteket.cli clear-all-session-files --yes"
```

### Platform-only LLM debug captures (Option A)

When enabled, Skriptoteket persists **sensitive** debug captures for edit-ops generation and preview failures under the
artifacts volume.

- Config: `LLM_CAPTURE_ON_ERROR_ENABLED=true` (default: `false`)
- Capture id: the request correlation id (`X-Correlation-ID` / `correlation_id`)
- Location (prod): `/app/.artifacts/llm-captures/<kind>/<capture_id>/capture.json`
- Security: captures may include tool code and raw model output; access is platform-only (filesystem/SSH).

List recent captures:

```bash
ssh hemma "sudo docker exec skriptoteket-web ls -1 /app/.artifacts/llm-captures 2>/dev/null || true"
```

Open a specific capture (replace `<CID>`):

```bash
ssh hemma \"sudo docker exec -T skriptoteket-web sh -lc 'cat /app/.artifacts/llm-captures/chat_ops_response/<CID>/capture.json | jq .'\"
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

### Deploy

### Production Env Checklist

Before deploying, confirm the production env file includes the keys that `compose.prod.yaml` forwards into the
containers.

- `SKRIPTOTEKET_DB_PASSWORD`
- `SECRET_KEY`
- SMTP / email keys as needed
- LLM provider keys as needed
- `SIR_CONVERT_A_LOT_V2_BASE_URL`
- `SIR_CONVERT_A_LOT_V2_API_KEY`
- `SIR_CONVERT_A_LOT_V2_CALLBACK_BASE_URL`
- `BOOTSTRAP_SUPERUSER_EMAIL`
- `ALLOWED_HOSTS`
- `TRUST_PROXY_HEADERS`
- `TRUSTED_PROXY_CIDRS`
- `HEALTHZ_DETAILED_RESPONSE`
- `METRICS_IDENTITY_GAUGES_ENABLED`

Hemma reference values for Conversion Hub:

- `SIR_CONVERT_A_LOT_V2_BASE_URL=https://convert.hule.education`
- `SIR_CONVERT_A_LOT_V2_API_KEY=<same secret used by Sir Convert-a-Lot v2>`
- `SIR_CONVERT_A_LOT_V2_CALLBACK_BASE_URL=https://skriptoteket.hule.education`

Why the public URL: Sir Convert-a-Lot is published on Hemma as `127.0.0.1:28085` on the host. That loopback-only
binding is not reachable from inside `skriptoteket-web` via `host.docker.internal:28085`, so the curated app must use
the public domain (or another container-reachable address).

Local-dev policy:

- Default local Skriptoteket development to the same public Sir Convert domain,
  `https://convert.hule.education`.
- Do not run a host-local Sir Convert `uvicorn` process on the laptop as the
  normal path.
- If a local converter lane is explicitly needed for debugging, it must be a
  separate CPU-only Docker dev profile that runs on the MacBook without ROCm.

Validation:

```bash
ssh hemma "sudo docker exec skriptoteket-web env | grep '^SIR_CONVERT_A_LOT_V2_'"
ssh hemma "sudo docker exec skriptoteket-worker env | grep '^SIR_CONVERT_A_LOT_V2_'"
ssh hemma "sudo docker exec skriptoteket-web getent hosts host.docker.internal"
ssh hemma "sudo docker exec skriptoteket-web env | grep -E '^(ALLOWED_HOSTS|TRUST_PROXY_HEADERS|TRUSTED_PROXY_CIDRS|HEALTHZ_DETAILED_RESPONSE|METRICS_IDENTITY_GAUGES_ENABLED)='"
ssh hemma "sudo docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' nginx-proxy"
```

Security-specific notes:

- `TRUSTED_PROXY_CIDRS` must be the exact current `nginx-proxy` IP/CIDR on `hule-network`, not a broad private-range fallback.
- Keep `skriptoteket_web` out of production `ALLOWED_HOSTS`; that host is for containerized dev only.
- Reserved HuleEdu hosts (`hule.education`, `api.hule.education`, `ws.hule.education`) are HuleEdu-owned runtime surfaces and must never fall through to Skriptoteket or the nginx-proxy default host.

### Hemma Reboot and Auth-Edge Readiness

Docker restart policy is not the Hemma boot-order contract. After HuleEdu
`TASK-0509`, the expected recovery shape is:

- Tier 0 edge/shared services (`nginx-proxy`, `acme-companion`, `shared-postgres`,
  `hemma-reserved-default-host`) may auto-recover through `restart: unless-stopped`.
- Runtime lanes, including `skriptoteket-web` and `skriptoteket-worker`, are
  normalized to `restart=no` so staged startup is not bypassed after reboot.
- HuleEdu host-wide startup restores Skriptoteket and then retains
  `api.hule.education` TLS/SNI, Gateway health, auth ceremony, and protected API
  proof.

Keep the readiness states separate:

- `https://skriptoteket.hule.education/healthz` proves Skriptoteket self-health
  only.
- Public Klassrumskartan app/share routes are direct Skriptoteket public
  surfaces and must not require a live HuleEdu browser session.
- Protected Skriptoteket APIs are certified only through
  `https://api.hule.education/api/...`; a green app-host health check is not
  auth readiness.

Run HuleEdu-owned post-reboot proof from the HuleEdu repo with its wrapper
surface:

```bash
pdm run run-local-pdm hemma-normalize-hostwide-restart-policy --verify
pdm run run-local-pdm hemma-start-hostwide
pdm run run-local-pdm hemma-skriptoteket-protected-api-proof
```

If these commands fail, treat the incident as HuleEdu auth-edge/provider
readiness until the Gateway, TLS/SNI, and protected-edge proof are healthy.
Do not replace that with a Skriptoteket direct protected-API shortcut.

### Canonical Deploy + Readiness Gate

The canonical local operator entrypoint is:

```bash
pdm run hemma-deploy
```

That command launches the checked-in on-host script
`scripts/hemma_deploy_and_verify_seating_export.sh` on Hemma as a detached
remote process. It prints:

- the remote PID
- the authoritative remote raw-log path
- the remote PID-file path
- the suggested `pdm run hemma-deploy-monitor -- <remote-log-path>` follow
  command

The detached launcher exists only to hand off cleanly. The actual deploy logic
remains in the on-host script, which is intentionally fail-closed. It:

- fast-forwards a clean Hemma checkout to the latest `origin/main`
- builds/redeploys Skriptoteket with `compose.prod.yaml`
- runs `pdm run db-upgrade` inside `skriptoteket-web`
- runs the mandatory local seating-export smoke and fails if the export does not reach immediate
  local terminal success with a Vault-backed download
- stores the smoke JSON output under `.artifacts/pr-0146-seat-export-cutover-<timestamp>/` as
  operator evidence

If you want a readable live monitor after launch, use:

```bash
pdm run hemma-deploy-monitor
```

or, for a specific log path printed by `pdm run hemma-deploy`:

```bash
pdm run hemma-deploy-monitor -- /home/paunchygent/apps/skriptoteket/.artifacts/hemma-deploy-YYYYMMDD-HHMMSS.log
```

The monitor is best-effort only. It replays the existing milestone/failure
lines from the authoritative raw remote log, then follows new output and
filters it to the existing `==>` milestone lines plus obvious failure patterns.
It is not a second source of deploy truth.

### Direct on-host fallback / debugging

If the local launcher path is unavailable or if you need direct break-glass
debugging on Hemma, run the on-host script directly:
