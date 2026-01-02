---
type: story
id: ST-09-04
title: "Production perimeter hardening v2 (bots + VPN gating plan)"
epic: EPIC-09
status: ready
owners: "agents"
created: 2026-01-01
dependencies: ["ADR-0053"]
ui_impact: "None (ops/security only)"
data_impact: "None"
acceptance_criteria:
  - "Given the current production security posture, when reading the story, then it clearly summarizes what is already implemented and how to verify it (commands + files)."
  - "Given repeat web scanners probing common paths and methods, when they exceed the ban threshold, then Fail2ban temporarily bans them via nftables and recidive can escalate repeat offenders."
  - "Given Loki contains nginx-proxy access logs, when querying, then operators can identify top offenders by vhost/client_ip/method/status without high-cardinality labels."
  - "Given A/B decisions (VPN gating SSH and/or observability), when reading ADR-0053 + the research doc, then the tradeoffs and migration steps are clear enough to decide."
---

## Context

`hemma.hule.education` is continuously probed by bots (SSH brute-force, HTTP path probes like `/.env`, `.git`, `wp-*`,
`cgi-bin`, WebDAV methods). We want defense-in-depth:

- Drop cheap probes at the reverse proxy (reduce app noise, reduce CPU/mem, avoid noisy 503s).
- Ban repeat offenders automatically.
- Make bot traffic visible and queryable.
- Decide whether to reduce exposure further via VPN gating (SSH and/or observability domains).

## Current state (already implemented)

- **Fail2ban (SSH + recidive)**:
  - `sshd` jail enabled.
  - `recidive` jail enabled: 3 strikes within 7 days → permaban (reads `/var/log/fail2ban.log*`).
- **Fail2ban (nginx-proxy probes)**:
  - `nginx-proxy-probe` jail enabled: bans repeat `444` drops and repeat `401/403` auth probes via nftables
    all-ports bans.
  - Config: `/etc/fail2ban/filter.d/nginx-proxy-probe.conf`, `/etc/fail2ban/jail.d/nginx-proxy-probe.local`.
- **nginx-proxy edge hardening**:
  - `/etc/nginx/vhost.d/global-hardening.conf` drops common probes + scanner methods with `444`.
  - `DEFAULT_HOST=skriptoteket.hule.education` set in `~/infrastructure/docker-compose.yml` to avoid a generated
    `server_name _` default that returns `503`.
- **Observability for bot traffic (Loki)**:
  - Promtail parses nginx-proxy access logs into Loki labels: `vhost`, `client_ip`, `method`, `status`
    (`observability/promtail/promtail-config.yaml`).
  - Grafana dashboard is provisioned: `observability/grafana/provisioning/dashboards/skriptoteket-nginx-proxy-security.json`.
- **Readiness strictness**:
  - `HEALTHZ_SMTP_CHECK_ENABLED=true` in production so `/healthz` becomes `503` when SMTP is down (intended strict
    readiness).

## Scope (this story)

1. Document the above posture + verification commands.
2. Implement C: ban repeat HTTP offenders + add Grafana visibility.
3. Produce decision scaffolding for A/B:
   - ADR describing what is decided vs open (VPN gating).
   - Research doc that compares Tailscale/WireGuard and “public vs VPN” observability access patterns.

Out of scope: actually migrating SSH and/or observability to VPN-only (that becomes follow-up implementation work
after the ADR is accepted).

## Implementation notes (C: bots)

### 1) Fail2ban jail for nginx-proxy scanners

Add a Fail2ban jail that bans IPs producing repeated `444` (dropped probes) and repeated auth failures (`401/403`).

Notes:

- Docker on `hemma` is snap-managed; container json logs are under:
  `/var/snap/docker/common/var-lib-docker/containers/*/*-json.log`
- Fail2ban must use `backend = polling` (avoid the `systemd` backend without precise `journalmatch`).
- `usedns = no` so the jail always bans the client IP, not the vhost/domain token in the access log line.
- The jail must ignore RFC1918 ranges so internal calls (e.g., `172.18.0.1`) never trigger bans.

### 2) Grafana dashboard (Loki)

Add a provisioned Grafana dashboard for nginx-proxy security/bot analysis using Loki labels:

- Top `client_ip` by request count
- Top `vhost`
- Status breakdown (`444`, `401`, `200`, etc.)
- Probe pattern counters (query-time filters: `/.env`, `\\.git`, `wp-`, `\\.php`, `cgi-bin`, `PROPFIND`)

## Decision points (A/B: VPN gating)

- **A) SSH behind VPN**: Stop exposing port `22` publicly and require VPN (WireGuard/Tailscale) for SSH access.
  - Goal: remove almost all SSH bot traffic.
  - Must preserve: SSH key-based access from MacBook + phone, plus the ability for this agent workflow to SSH
    without needing local console access.
- **B) Observability behind VPN**: Keep Grafana/Prometheus/Jaeger reachable remotely, but consider VPN gating instead
  of public exposure (even with auth).
  - Goal: reduce probing + brute-force traffic on observability domains.

## Verification

```bash
# Fail2ban
ssh hemma "sudo fail2ban-client status"
ssh hemma "sudo fail2ban-client status recidive"
ssh hemma "sudo fail2ban-client status nginx-proxy-probe"
ssh hemma "sudo fail2ban-client get nginx-proxy-probe logpath"

# nginx-proxy logs (spot-check for 444)
ssh hemma "sudo docker logs --since 10m nginx-proxy | rg -n '\" (401|444) ' | tail -n 20"

# Loki labels exist
ssh hemma "curl -s http://127.0.0.1:3100/loki/api/v1/labels | jq '.data' | rg -n 'client_ip|vhost|method|status'"

# Grafana dashboard file is mounted
ssh hemma "sudo docker exec grafana ls -1 /etc/grafana/provisioning/dashboards | rg -n 'skriptoteket-nginx-proxy-security'"
```
