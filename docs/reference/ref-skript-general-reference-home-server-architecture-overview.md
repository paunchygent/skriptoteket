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

Historical edge observation (2026-03-28; Sir retirement supersedes it below):

- proxy-routed services at that time: Skriptoteket, Sir Convert-a-Lot and Projektveckor
- `skriptoteket.hule.education` was the `DEFAULT_HOST`

The 2026-05-02 nginx-proxy reference records `hule.education`,
`api.hule.education`, and `ws.hule.education` as claimed by HuleEdu runtime
services on `hule-network`; under that reference they must not inherit the
Skriptoteket default vhost. No new host proof was collected for this overview.

Sir Convert-a-Lot public host retired (2026-10-15, source-based):

- The user retired `convert.hule.education` on 2026-10-15. The source
  retirement is Sir `fix/retire-convert-public-edge` commit `904d0e3f` with
  accepted `ADR-SIRCON-0014`.
- Sir Convert-a-Lot's supported service lane is private:
  `sir_convert_a_lot_prod:8085` on `hule-network`
  (`http://sir_convert_a_lot_prod:8085`). Sir production remains offline by
  user decision, and Namecheap CNAME deletion stays with the user.

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
│                   projektveckor.hule.education → portal     │
│  - Default host: skriptoteket.hule.education               │
│  - HuleEdu-owned (2026-05-02): hule.education, api/ws.hule... │
├──────────────────────────────────────────────────────────────┤
│  acme-companion (nginxproxy/acme-companion:2.4)              │
│  - Auto-generates Let's Encrypt certificates                 │
│  - Listens for LETSENCRYPT_HOST env vars on containers       │
│  - Auto-renews before expiry                                 │
└────────────────────────────┬────────────────────────────────┘
                             │
    ┌────────────────────────┐
    │                        │
    ▼                        ▼
┌─────────────┐      ┌─────────────┐
│ skriptoteket │      │projektveckor│
│     :8000    │      │    :8000    │
└─────────────┘      └─────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  hule-network private services                               │
│  - shared-postgres: PostgreSQL 16 (shared across services)  │
│  - sir_convert_a_lot_prod:8085: private Sir Convert-a-Lot   │
│    (public convert.hule.education retired 2026-10-15)       │
└─────────────────────────────────────────────────────────────┘
```

## Decisions And Interpretation

The source record did not define a separate section for this package heading.
