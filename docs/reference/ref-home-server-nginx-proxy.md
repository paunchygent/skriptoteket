---
type: reference
id: REF-home-server-nginx-proxy
title: "Reference: Home Server nginx-proxy"
status: active
owners: "olof"
created: 2026-01-02
updated: 2026-01-02
topic: "nginx-proxy routing and edge hardening"
---

Details for adding services behind nginx-proxy and maintaining edge hardening.

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
