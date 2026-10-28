---
type: task
id: TASK-SKRIPT-09-07-01
title: ST-09-07 public-edge app/runtime hardening
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-07-31'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: orchestrator
  decided_at: '2026-10-28'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: 'Criterion 3 landed in 6f824a74f and docs 8f1b07d02 (merged 1f3f84f9f): production settings refuse localhost, 127.0.0.1 and ::1 in ALLOWED_HOSTS, naming the entry; the production default is skriptoteket.hule.education; the production web healthcheck and the deploy readiness gate send Host: skriptoteket.hule.education. Fail-first 7 tests failed before, 45 passed after; lint and typecheck clean (retained evidence prod-allowed-hosts-2/). The earlier criteria were found holding on main by the 2026-10-28 audit (REP-0055). Live check on Hemma staging at d0064b1ce, 2026-10-28: web and worker healthy; Host localhost and 127.0.0.1 get 200 and evil.example gets 400 in staging; in the same image with ENVIRONMENT=production, ALLOWED_HOSTS=localhost,skriptoteket.hule.education fails with the named-entry error and skriptoteket.hule.education alone loads. Production deploy needs the production .env ALLOWED_HOSTS changed first (handoff user gate).'
story: ST-SKRIPT-09-07
task_kind: story
acceptance_criteria:
  - Production config defaults keep docs/OpenAPI disabled, health payloads minimal, and identity metrics off unless explicitly re-enabled.
  - Trusted client IP extraction only considers forwarded headers from explicitly trusted proxies.
  - Production host validation rejects test/dev-only hosts, while Docker-based local development still works through the frontend dev server.
  - Focused automated tests and a live local functional check cover the hardened production behavior and the repaired local login path.
backlog_document_profile: contract-derived
---

## Implementation Contract

Decision 2026-10-28 (TASK-SKRIPT-REP-0055 D5): production startup refuses `ALLOWED_HOSTS` entries `localhost`, `127.0.0.1` and `::1`. The code landed in 6f824a74f (merged 1f3f84f9f).

## Context

### Problem

Repo-side public-edge hardening was incomplete after the initial patch landed.
Production still needed app/runtime behavior that failed closed for observability
detail, trusted host handling, and login-event client IP extraction, without
breaking Docker-based local development.

### Goal

Ship the application/runtime hardening slice that closes the confirmed
repo-owned drill findings and preserves local developer workflows.

### Non-goals

- Changing Hemma nginx-proxy routing, DNS, or reserved-host ownership
- Adding edge authentication/VPN controls for `/metrics`
- Deploying the patch to Hemma in this PR slice

### Implementation plan

1. Tighten `src/skriptoteket/config.py` production defaults for:
   - `ALLOWED_HOSTS`
   - `TRUST_PROXY_HEADERS`
   - `TRUSTED_PROXY_CIDRS`
   - `HEALTHZ_DETAILED_RESPONSE`
   - `METRICS_IDENTITY_GAUGES_ENABLED`
2. Keep Docker-based local dev working with an explicit non-production host
   allowance for `skriptoteket_web`.
3. Narrow `src/skriptoteket/web/request_metadata.py` so caller-controlled
   forwarding headers are ignored unless the direct peer is inside the trusted
   proxy set.
4. Keep `/healthz` public-safe and `/metrics` identity-safe through the existing
   observability route/config seam.
5. Cover the slice with focused unit tests plus a live local login proof through
   `http://127.0.0.1:5173`.

### Test plan

- `pdm run pytest tests/unit/test_config.py tests/unit/web/test_request_metadata.py tests/unit/web/test_observability_routes.py tests/unit/web/test_api_v1_auth_and_csrf_routes.py tests/unit/web/test_app_security_hardening.py -q`
- `pdm run ruff check src/skriptoteket/config.py src/skriptoteket/web/request_metadata.py src/skriptoteket/web/api/v1/auth.py src/skriptoteket/observability/health.py src/skriptoteket/observability/metrics.py src/skriptoteket/web/routes/observability.py tests/unit/test_config.py tests/unit/web/test_request_metadata.py tests/unit/web/test_observability_routes.py tests/unit/web/test_app_security_hardening.py`
- `docker compose -f compose.prod.yaml config >/dev/null`
- Live functional check:
  - `curl -sS -o /tmp/skriptoteket-login-wrong.out -w '%{http_code}\n' -H 'Content-Type: application/json' -d '{"email":"superuser@local.dev","password":"wrong-password"}' http://127.0.0.1:5173/api/v1/auth/login`
  - bootstrap-superuser login through `http://127.0.0.1:5173/api/v1/auth/login`
  - frontend-container request with `Host: skriptoteket_web:8000`

### Rollback plan

- Revert the config/request-metadata/observability changes and the focused
  tests.
- If local Docker dev regresses again, remove only the non-production host
  allowance after replacing the frontend proxy topology with a documented
  alternative.

## Decision And Assumption Ledger

The source material below remains authoritative for this section.

## Story Contract Slice

The source material below remains authoritative for this section.

## Contract Inputs

The source material below remains authoritative for this section.

## Core Vertical And Performance

The source record did not define a separate section for this package heading.

## Plan

The source material below remains authoritative for this section.

## Implementation Steps

The source material below remains authoritative for this section.

## Proof

Verification expectations remain in the retained source material below.

## Validation

Verification expectations remain in the retained source material below.

## Stop Conditions

The source boundaries and recovery limits remain preserved below.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                 |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | Production startup refuses `ALLOWED_HOSTS` entries `localhost`, `127.0.0.1` and `::1` (user decision 2026-10-28, TASK-SKRIPT-REP-0055 D5); this task stays open until the code lands. |

## Lessons Learned

The source material below remains authoritative for this section.

## Notes

The source material below remains authoritative for this section.

## Plan Document Review

The source material below remains authoritative for this section.

## Implementation Review

The source material below remains authoritative for this section.
