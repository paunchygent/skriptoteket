---
type: reference
id: REF-SKRIPT-GENERAL-reference-home-server-architecture-overview
title: 'Reference: Home Server Architecture Overview'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: active
reference_kind: general
retired_ids:
- REF-home-server-architecture
summary: 'Reference: Home Server Architecture Overview'
---

## Overview
The source record did not define a separate section for this package heading.

## Facts And Semantics
### Source record
Context-only architecture overview for Hemma. Operational steps live in the runbooks.

Current edge behavior was re-verified on 2026-03-28:

- active proxy-routed services: Skriptoteket, Sir Convert-a-Lot, Projektveckor
- `skriptoteket.hule.education` remains the `DEFAULT_HOST`
- `hule.education`, `api.hule.education`, and `ws.hule.education` currently resolve to
  Hemma but fall through to the Skriptoteket default vhost because no dedicated HuleEdu
  container has claimed those hosts yet

```text
┌─────────────────────────────────────────────────────────────┐
│                        Internet                              │
└────────────────────────────┬────────────────────────────────┘
                             │ :80/:443 (HTTP/HTTPS)
┌────────────────────────────▼────────────────────────────────┐
│  nginx-proxy (nginxproxy/nginx-proxy:1.6)                    │
│  - Auto-discovers containers via VIRTUAL_HOST env var        │
│  - SSL termination (certs from acme-companion)               │
│  - Active routes: skriptoteket.hule.education → skriptoteket│
│                   convert.hule.education → Sir Convert      │
│                   projektveckor.hule.education → portal     │
│  - Default host: skriptoteket.hule.education               │
│  - Reserved but unresolved: hule.education, api/ws.hule... │
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
│ skriptoteket │      │ sir convert │         │projektveckor│
│     :8000    │      │    :8085    │         │    :8000    │
└─────────────┘      └─────────────┘         └─────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  shared-postgres (hule-network)                              │
│  - PostgreSQL 16 (shared across services)                   │
│  - Additional app containers can join the same bridge       │
└─────────────────────────────────────────────────────────────┘
```

## Decisions And Interpretation
The source record did not define a separate section for this package heading.
