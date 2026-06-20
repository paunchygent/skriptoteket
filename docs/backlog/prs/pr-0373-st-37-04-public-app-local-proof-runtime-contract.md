---
type: pr
id: PR-0373
title: "ST-37-04 public app local proof runtime contract"
status: done
owners: "agents"
created: 2026-06-20
updated: 2026-06-20
stories:
  - "ST-37-04"
tags:
  - frontend
  - devops
  - docs
dependencies:
  - "PR-0366"
  - "PR-0371"
  - "PR-0372"
acceptance_criteria:
  - "Given host Vite is used for shared-auth browser proof, when public app routes are exercised, then the documented command sequence starts or reuses a Docker Skriptoteket backend before the browser proof."
  - "Given the Docker frontend is used, when Vite proxies public API traffic, then `/api/v1/public/...` explicitly targets `skriptoteket_web:8000`."
  - "Given a future maintainer edits local proxy defaults, when tests run, then a focused contract test fails if public API traffic can silently fall back to the HuleEdu Gateway or an absent backend lane."
  - "Given this slice closes, when the local public Exam Converter route is opened through Vite, then the route no longer fails because the backend proxy target is missing."
---

# PR-0373: ST-37-04 Public App Local Proof Runtime Contract

## Problem

The host Vite public-app proof lane can render the public landing while still
returning a Vite-level `500 Internal Server Error` for
`/api/v1/public/...` when the Skriptoteket backend is not running. This makes
public app browser proof look like an app regression even though the runtime
is missing the backend target required by the public API proxy.

## Goal

Make the local public-app proof lane explicit and durable: host Vite used with
the HuleEdu Gateway must have a Docker-backed Skriptoteket web service for
public API routes, and the Docker frontend must explicitly keep public API
traffic on the Skriptoteket backend instead of the HuleEdu Gateway.

## Non-goals

- No route, app id, registry, or teacher-facing copy change.
- No protected-auth ceremony change.
- No public Exam Converter API schema change.
- No Sir Convert, QTI, DOCX, or backend conversion behavior change.

## Acceptance Criteria

- Given host Vite is used for shared-auth browser proof, when public app routes
  are exercised, then the documented command sequence starts/reuses a Docker
  Skriptoteket backend before the browser proof.
- Given the Docker frontend is used, when Vite proxies public API traffic, then
  `/api/v1/public/...` explicitly targets `skriptoteket_web:8000`.
- Given a future maintainer edits local proxy defaults, when tests run, then a
  focused contract test fails if public API traffic can silently fall back to
  the HuleEdu Gateway or an absent backend lane.
- Given this slice closes, when the local public Exam Converter route is opened
  through Vite, then the route no longer fails because the backend proxy target
  is missing.

## Implementation Plan

1. [x] Add red-first contract coverage for the shared-auth host Vite command,
   Docker frontend public API proxy, and Docker web-only startup lane.
2. [x] Add a `dev-stack web-start` command for Docker `db` + `web` + migration
   startup without taking over port `5173`.
3. [x] Add a `fe-dev-shared-auth` command that pins host Vite to the local
   HuleEdu Gateway for protected `/api` traffic and to local Skriptoteket web
   for public `/api/v1/public` traffic.
4. [x] Make Docker frontend public API target explicit in compose env.
5. [x] Update docs/handoff with the canonical local public-app proof lane.

## Implementation Evidence

- `scripts/dev_stack.py` now exposes `pdm run dev-stack web-start`, which
  starts Docker `db` and `web` without taking ownership of Vite port `5173`,
  then applies migrations through the Docker web service.
- `pyproject.toml` now exposes `pdm run fe-dev-shared-auth`, which pins
  protected `/api` traffic to the local HuleEdu Gateway and public
  `/api/v1/public` traffic to the local Skriptoteket backend on
  `http://localhost:8000`.
- `compose.yaml` now makes `VITE_DEV_PUBLIC_API_PROXY_TARGET` explicit for the
  Docker frontend and keeps it on `http://skriptoteket_web:8000`.
- `.env.example`, `README.md`, and `docs/runbooks/runbook-testing.md` document
  the split host Vite shared-auth proof lane.

## Verification

- Red first:
  `pdm run test tests/unit/test_docker_dev_shared_auth_contract.py`
  failed with three expected contract failures: missing
  `VITE_DEV_PUBLIC_API_PROXY_TARGET` in Docker frontend env, missing
  `fe-dev-shared-auth`, and missing `dev-stack web-start`.
- Green:
  `pdm run test tests/unit/test_docker_dev_shared_auth_contract.py`
  passed with 6 tests.
- Runtime:
  `pdm run dev-stack web-start` started Docker `db` and `web` and applied
  migrations through the Docker web service.
- Health:
  `curl -sS -i http://127.0.0.1:8000/healthz`
  returned `200 OK` with healthy service, database, and SMTP checks.
- Public bootstrap:
  `curl -sS -i http://localhost:5173/api/v1/public/apps/documents.conversion_hub/exam-converter`
  returned `200 OK` through the Vite public API proxy.
- Browser:
  Node REPL Playwright with installed Chrome opened
  `http://localhost:5173/public/apps/documents.conversion_hub/exam-converter`
  and confirmed the page rendered `PROVHANTERING`, `Exam Converter`, and no
  `Internal Server Error`.
- Close-out:
  `pdm run lint`, `pdm run typecheck`, `pdm run fe-type-check`,
  `pdm run fe-lint`, `pdm run docs-validate`, `pdm run handoff-validate`, and
  `git diff --check` all passed.

## Test Plan

- Red first:
  `pdm run test tests/unit/test_docker_dev_shared_auth_contract.py`
- Green:
  `pdm run test tests/unit/test_docker_dev_shared_auth_contract.py`
- Live proof:
  `pdm run dev-stack web-start` plus host Vite at `http://localhost:5173/`,
  then browser/curl proof for
  `/public/apps/documents.conversion_hub/exam-converter`.
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Rollback Plan

Restore the previous command/config surface and use the full Docker dev stack
for public-app local proof until a replacement host Vite lane is defined.
