---
type: reference
id: REF-home-server-nginx-proxy
title: "Reference: Home Server nginx-proxy"
status: active
owners: "olof"
created: 2026-01-02
updated: 2026-03-28
topic: "nginx-proxy routing and edge hardening"
---

Details for adding services behind nginx-proxy and maintaining edge hardening.

## Current edge reality (verified 2026-03-28)

Hemma's shared edge stack is:

- `nginxproxy/nginx-proxy:1.6` (`nginx-proxy`)
- `nginxproxy/acme-companion:2.4` (`acme-companion`)
- `DEFAULT_HOST=skriptoteket.hule.education`

Known active routed hosts on the shared proxy:

- `skriptoteket.hule.education`
- `convert.hule.education`
- `projektveckor.hule.education`

Reserved HuleEdu hostnames currently resolve to Hemma but do **not** have dedicated
`server_name` blocks yet:

- `hule.education`
- `api.hule.education`
- `ws.hule.education`

Because `DEFAULT_HOST` still points at Skriptoteket, those unresolved hosts fall through
to the Skriptoteket default vhost and currently present the
`skriptoteket.hule.education` certificate.

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
- they are not registered in `nginx-proxy`
- they therefore inherit the Skriptoteket default cert/backend today

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

If you need the apex host to stop presenting the Skriptoteket certificate before the real
gateway ships, add a trivial placeholder service that registers `hule.education` on
`hule-network`. Keep the response temporary (`302`/`307`), not permanent (`301`), so the
future gateway cutover is not sticky in browsers and caches.

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
