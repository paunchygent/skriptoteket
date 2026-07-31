---
type: reference
id: REF-SKRIPT-GENERAL-reference-home-server-nginx-proxy
title: 'Reference: Home Server nginx-proxy'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: active
reference_kind: general
retired_ids:
- REF-home-server-nginx-proxy
summary: 'Reference: Home Server nginx-proxy'
---

## Overview

### Source: Source introduction

Details for adding services behind nginx-proxy and maintaining edge hardening.

## Facts And Semantics

### Source: Current edge reality (verified 2026-05-02)

Hemma's shared edge stack is:

- `nginxproxy/nginx-proxy:1.6` (`nginx-proxy`)
- `nginxproxy/acme-companion:2.4` (`acme-companion`)
- `DEFAULT_HOST=skriptoteket.hule.education`

Known active routed hosts on the shared proxy:

- `skriptoteket.hule.education`
- `convert.hule.education`
- `projektveckor.hule.education`
- `hule.education`
- `api.hule.education`
- `ws.hule.education`

The HuleEdu hostnames are claimed by HuleEdu runtime services.

Fallback/default host behavior:

- service: `hemma-reserved-default-host`
- image: `nginx:1.27-alpine`
- response body/header: `hemma-reserved-default-host`
- restart policy: `unless-stopped`

Skriptoteket-specific edge hardening now also blocks public `/metrics` at nginx while
allowing internal Prometheus scrapes to continue directly against `skriptoteket-web:8000`.

### Source: Add a New Service to nginx-proxy

Add these env vars to the service and expose its internal port:

```yaml
environment:
  - VIRTUAL_HOST=myservice.hemma.hule.education
  - VIRTUAL_PORT=8080  # Internal port the service listens on
  - LETSENCRYPT_HOST=myservice.hemma.hule.education
expose:
  - "8080"
```

Then add a DNS A record for `myservice.hemma` pointing to your public IP.
The acme-companion will automatically generate SSL certificates.

For the reserved HuleEdu apex/API/WebSocket hosts, the same rule applies: the
HuleEdu runtime service must claim the host with `VIRTUAL_HOST` (and usually
`LETSENCRYPT_HOST`) on `hule-network`. DNS plus pre-provisioned cert intent is
not enough on its own, and the retired placeholder should not be recreated as
the normal recovery path.

### Source: Reserved HuleEdu hostnames

Long-term intent:

- `hule.education` = HuleEdu entrypoint
- `api.hule.education` = HuleEdu API gateway
- `ws.hule.education` = HuleEdu WebSocket service

Current reality:

- they resolve publicly to Hemma
- they are registered by HuleEdu runtime services on `hule-network`
- `api.hule.education` serves a certificate for `api.hule.education`
- they must not inherit the Skriptoteket default cert/backend

Verification:

```bash
echo | openssl s_client -connect hule.education:443 -servername hule.education 2>/dev/null \
  | openssl x509 -noout -subject -ext subjectAltName

echo | openssl s_client -connect api.hule.education:443 -servername api.hule.education 2>/dev/null \
  | openssl x509 -noout -subject -ext subjectAltName

echo | openssl s_client -connect ws.hule.education:443 -servername ws.hule.education 2>/dev/null \
  | openssl x509 -noout -subject -ext subjectAltName

### From the HuleEdu repo:
pdm run run-local-pdm run-hemma -- sudo docker exec nginx-proxy sed -n '1,260p' /etc/nginx/conf.d/default.conf
```

If the HuleEdu runtime edge is down, run the HuleEdu host-wide startup and
readiness proof surfaces from the HuleEdu repo instead of recreating the
retired placeholder:

```bash
### From the HuleEdu repo:
pdm run run-local-pdm hemma-normalize-hostwide-restart-policy --verify
pdm run run-local-pdm hemma-start-hostwide
pdm run run-local-pdm hemma-skriptoteket-protected-api-proof
```

### Source: Skriptoteket public metrics block

Public `/metrics` should stay operator-only. On Hemma, the current pattern is a dedicated
vhost snippet for `skriptoteket.hule.education`:

```nginx
location = /metrics {
    return 403;
}
```

Deploy/update the snippet inside `nginx-proxy`:

```bash
ssh hemma "sudo docker exec nginx-proxy sh -lc 'cat >/etc/nginx/vhost.d/skriptoteket.hule.education <<\"EOF\"
location = /metrics {
    return 403;
}
EOF
nginx -s reload'"
```

Important: this edge block is safe because Prometheus scrapes `skriptoteket-web:8000`
directly on `hule-network`, not through the public vhost.

### Source: nginx-proxy edge hardening (drop probes / unknown hosts)

We proactively drop common scanner traffic at the reverse proxy so the app layer never sees it.

Key settings/files:

- `DEFAULT_HOST=skriptoteket.hule.education` in `~/infrastructure/docker-compose.yml` (nginx-proxy)
  to avoid a generated `server_name _` that returns `503`.
- vhost snippets live in the nginx-proxy volume at `/etc/nginx/vhost.d/`:
  - `global-hardening.conf`: blocks common probes (e.g. `/.env`, `/.git`, `wp-*`, `*.php`, `cgi-bin`, WebDAV methods)
    with `444`.
  - `default`: includes `global-hardening.conf` (applies to all vhosts).

Inspect current config:

```bash
ssh hemma "sudo docker exec nginx-proxy ls -la /etc/nginx/vhost.d"
ssh hemma "sudo docker exec nginx-proxy sed -n '1,200p' /etc/nginx/vhost.d/global-hardening.conf"
```

Reload after changes:

```bash
ssh hemma "sudo docker exec nginx-proxy nginx -s reload"
```

## Decisions And Interpretation

No separate source material was recorded for this section.
