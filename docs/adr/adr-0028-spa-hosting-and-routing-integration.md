---
type: adr
id: ADR-0028
title: "SPA hosting and routing integration in FastAPI"
status: accepted
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-21
links: ["ADR-0027", "PRD-spa-frontend-v0.1"]
---

## Context

A full SPA must be:

- served reliably in production with cacheable, hashed assets
- routable via history mode (deep links work on refresh)
- simple to develop locally without complex CORS and multi-origin session issues

## Decision

### 1) Serve the SPA from the same FastAPI origin

- FastAPI serves the built SPA assets under its existing `/static` mount.
- The SPA `index.html` is served for all non-API routes (history fallback).
- `/api/*` remains backend-owned and is excluded from SPA fallback routing.

### 2) Use hashed build outputs + manifest-driven asset linking

- Production builds output hashed JS/CSS and a manifest file.
- Backend uses the manifest to render correct asset URLs (no hardcoded filenames).

### 3) Development workflow supports fast iteration

Development supports either:

- Vite dev server with proxying to FastAPI (preferred), or
- watch builds to `/static` for simplified integration.

## Consequences

- Same-origin hosting avoids CORS and cross-site cookie edge cases.
- The backend becomes responsible for correct “history fallback” routing behavior.
- Manifest integration becomes part of the deployment contract.
