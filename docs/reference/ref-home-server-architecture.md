---
type: reference
id: REF-home-server-architecture
title: "Reference: Home Server Architecture Overview"
status: active
owners: "olof"
created: 2026-01-02
updated: 2026-01-02
topic: "Home server network and service topology"
---

Context-only architecture overview for Hemma. Operational steps live in the runbooks.

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
