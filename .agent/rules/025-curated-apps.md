---
id: "025-curated-apps"
type: "standards"
created: 2026-01-27
scope: "all"
---

# 025: Curated Apps (First‑Class Application Modules)

Curated apps are **part of the Skriptoteket application**. They are not “tools” and must not be implemented as thin
wrappers around generic tool/run UI contracts.

## 1. Definition (REQUIRED)

- **REQUIRED**: A curated app is a first‑class application module (compiled/shipped source code).
- **REQUIRED**: A curated app owns its **domain language**, **UX**, **validation**, and **API contract** end‑to‑end.
- **REQUIRED**: A curated app may reuse shared infrastructure (runner, storage, vault, DB, etc.) **only as an internal
  implementation detail**.

## 2. UI Contract Usage (MUST / FORBIDDEN)

- **MUST**: If an app is `ui_mode=bespoke_required`, the SPA must render a bespoke view (or fail closed with a clear
  “bespoke view missing” message).
- **FORBIDDEN**: Falling back to the generic UI‑contract flows (v2/v3 tool-run/action forms) for
  `ui_mode=bespoke_required`.
- **MAY**: If an app is `ui_mode=generic_ok`, it may use generic UI contract rendering (typically for demos or
  transitional apps).

## 3. Backend Contract (REQUIRED)

- **REQUIRED**: Curated apps MUST expose **app-specific endpoints** and **typed view models** (e.g.
  `/api/v1/apps/{app_id}/...`) for core user flows.
- **FORBIDDEN**: Exposing generic tool/run mechanics as the primary curated‑app contract (e.g. requiring clients to
  orchestrate `start_action`, `state_rev`, `latest_run_id`, etc.) when `ui_mode=bespoke_required`.
- **MAY**: Use internal “tool/run” execution to implement features (PDF export, long-running compute), but keep those
  details server-side and return an app-level response contract.

## 4. Frontend UX (REQUIRED)

- **REQUIRED**: Curated apps MUST present a cohesive, app-specific UX that does not look like the generic tool
  pipeline.
- **REQUIRED**: Curated apps MUST follow the HuleEdu design system rules in `.agent/rules/045-huleedu-design-system.md`
  (tokens-first styling + SPA primitives).
- **FORBIDDEN**: Leaking platform internals (run IDs/status pills, generic “artifacts panels”, UI contract field labels)
  into the primary UX for `ui_mode=bespoke_required`, unless explicitly required by product design for that app.
