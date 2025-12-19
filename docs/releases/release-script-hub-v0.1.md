---
type: release
id: REL-script-hub-v0.1
title: "Script Hub v0.1 release notes (MVP)"
status: draft
owners: "agents"
created: 2025-12-19
product: "script-hub"
version: "0.1"
links: ["PRD-script-hub-v0.1"]
---

## Summary

v0.1 is the MVP release of Skriptoteket / Script Hub: a teacher-first, server-rendered platform where authenticated
users can browse and run published tools via an upload → run → view result flow, with role-based governance for how
tools are created, reviewed, and published.

This document is `draft` until the release is cut and a `released:` date is recorded.

## Highlights (target scope)

- Server-rendered browse/run UX (teacher-first, low-JS).
- Local accounts + role-based access control: user → contributor → admin → superuser.
- Suggestion/governance workflow for proposing and publishing tools.
- Runner contract v1 (result.json + artifacts rules) with sandboxed HTML output.

## Not included (explicitly post-v0.1)

- Multi-turn interactive tools (typed outputs/actions/state contract v2).
- Curated apps (owner-authored richer “apps”).
- Embedded SPA islands for editor/runtime surfaces.

## Compatibility / upgrade notes

- DB schema is managed via Alembic migrations; upgrade with `pdm run db-upgrade`.
- Tool execution requires a local `ARTIFACTS_ROOT` when developing locally (see `AGENTS.md`).

## Known issues / limitations

- Mobile/touch UX improvements are planned separately (responsive adaptation stories).
- HTML tool output is sandboxed and cannot execute scripts; richer interactivity requires the v0.2 UI contract.

