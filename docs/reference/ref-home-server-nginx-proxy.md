---
type: reference
id: REF-home-server-nginx-proxy
title: "Reference: Home Server nginx-proxy"
status: active
owners: "olof"
created: 2026-01-02
updated: 2026-03-30
topic: "nginx-proxy routing and edge hardening"
---

Details for adding services behind nginx-proxy and maintaining edge hardening.

## Current edge reality (verified 2026-03-30)

Hemma's shared edge stack is:

- `nginxproxy/nginx-proxy:1.6` (`nginx-proxy`)
- `nginxproxy/acme-companion:2.4` (`acme-companion`)
- `DEFAULT_HOST=skriptoteket.hule.education`

Known active routed hosts on the shared proxy:

- `skriptoteket.hule.education`
- `convert.hule.education`
- `projektveckor.hule.education`

Reserved HuleEdu hostnames currently resolve to Hemma and are claimed by an explicit
placeholder service:

- `hule.education`
- `api.hule.education`
- `ws.hule.education`

Current placeholder behavior:

- service: `huleedu-reserved-host-placeholder`
- compose overlay: `~/infrastructure/docker-compose.huleedu-placeholder.yml`
- image: `hashicorp/http-echo:1.0.0`
- response body: `HuleEdu reserved host placeholder`

Skriptoteket-specific edge hardening now also blocks public `/metrics` at nginx while
allowing internal Prometheus scrapes to continue directly against `skriptoteket-web:8000`.

## Add a New Service to nginx-proxy

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

For the reserved HuleEdu apex/API/WebSocket hosts, the same rule applies: the eventual
gateway or a temporary placeholder must claim the host with `VIRTUAL_HOST` (and usually
`LETSENCRYPT_HOST`) on `hule-network`. DNS plus pre-provisioned cert intent is not
enough on its own.

## Reserved HuleEdu hostnames

Long-term intent:

- `hule.education` = HuleEdu entrypoint
- `api.hule.education` = HuleEdu API gateway
- `ws.hule.education` = HuleEdu WebSocket service

Current reality:

- they resolve publicly to Hemma
- they are registered by the temporary placeholder service on `hule-network`
- they no longer inherit the Skriptoteket default cert/backend

Verification:

```bash
echo | openssl s_client -connect hule.education:443 -servername hule.education 2>/dev/null \
  | openssl x509 -noout -subject -ext subjectAltName

echo | openssl s_client -connect api.hule.education:443 -servername api.hule.education 2>/dev/null \
  | openssl x509 -noout -subject -ext subjectAltName

echo | openssl s_client -connect ws.hule.education:443 -servername ws.hule.education 2>/dev/null \
  | openssl x509 -noout -subject -ext subjectAltName

ssh hemma "sudo docker exec nginx-proxy sed -n '1,260p' /etc/nginx/conf.d/default.conf"
```

If you need to recreate the temporary ownership pattern before the real HuleEdu gateway ships,
add a trivial placeholder service that registers `hule.education`, `api.hule.education`, and
`ws.hule.education` on `hule-network`. Keep the response temporary and obviously non-product.

Minimal pattern:

```yaml
services:
  huleedu-reserved-host-placeholder:
    image: hashicorp/http-echo:1.0.0
    command: ["-text=HuleEdu reserved host placeholder"]
    restart: unless-stopped
    expose:
      - "5678"
    environment:
      VIRTUAL_HOST: hule.education,api.hule.education,ws.hule.education
      VIRTUAL_PORT: "5678"
      LETSENCRYPT_HOST: hule.education,api.hule.education,ws.hule.education
    networks:
      - default
```

## Skriptoteket public metrics block

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

## nginx-proxy edge hardening (drop probes / unknown hosts)

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
