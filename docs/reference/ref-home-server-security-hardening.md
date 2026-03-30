---
type: reference
id: REF-home-server-security-hardening
title: "Reference: Home Server Security Hardening"
status: active
owners: "olof"
created: 2026-01-02
updated: 2026-03-30
topic: "SSH + Fail2ban hardening for Hemma"
---

Security hardening details for the home server. Use this for audits or when applying changes.

## Skriptoteket edge/runtime hardening (verified 2026-03-30)

Current production policy for `skriptoteket.hule.education`:

- `/docs` and `/openapi.json` stay disabled in production
- public `/healthz` stays available but only returns the minimal safe payload
- public `/metrics` is blocked at nginx; internal metrics remain available to Prometheus on `hule-network`
- `skriptoteket_active_sessions` and `skriptoteket_users_by_role` stay disabled in production metrics
- forwarded headers are trusted only from the exact current `nginx-proxy` CIDR
- reserved HuleEdu hosts must be owned by the explicit placeholder or the real gateway, never by Skriptoteket fallthrough

Required app env baseline on Hemma:

```dotenv
ALLOWED_HOSTS=localhost,127.0.0.1,::1,skriptoteket.hule.education
TRUST_PROXY_HEADERS=true
TRUSTED_PROXY_CIDRS=<exact-nginx-proxy-cidr>
HEALTHZ_DETAILED_RESPONSE=false
METRICS_IDENTITY_GAUGES_ENABLED=false
```

Do not use a broad fallback for `TRUSTED_PROXY_CIDRS`; rediscover the current proxy IP when
`nginx-proxy` or `hule-network` changes:

```bash
ssh hemma "sudo docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' nginx-proxy"
```

## Production verification checklist (Skriptoteket)

Use both the public edge and the in-container view after deploy:

```bash
ssh hemma /bin/bash -s <<'EOF'
set -euo pipefail
sudo docker exec skriptoteket-web curl -sS http://127.0.0.1:8000/healthz
printf '\n---\n'
sudo docker exec skriptoteket-web /bin/sh -lc "curl -sS http://127.0.0.1:8000/metrics | rg 'skriptoteket_(active_sessions|users_by_role)' || true"
EOF

curl -sS -D - -o /dev/null https://skriptoteket.hule.education/docs
curl -sS -D - -o /dev/null https://skriptoteket.hule.education/openapi.json
curl -sS -D - -o /dev/null https://skriptoteket.hule.education/metrics
curl -sS https://skriptoteket.hule.education/healthz
curl -k -sS https://hule.education
curl -k -sS https://api.hule.education
curl -k -sS https://ws.hule.education
```

Expected results:

- in-container `/healthz` is healthy
- in-container `/metrics` does not emit `skriptoteket_active_sessions` or `skriptoteket_users_by_role`
- public `/docs` and `/openapi.json` return `404`
- public `/metrics` returns `403`
- public `/healthz` returns `{"status":"healthy","message":"Service is healthy"}`
- reserved hosts return the temporary placeholder until the real HuleEdu edge services ship

## SSH Hardening (Checklist)

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

## Fail2ban (Checklist)

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

### Recidive jail (3 strikes → permaban)

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

### nginx-proxy probe jail (HTTP scanners)

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
