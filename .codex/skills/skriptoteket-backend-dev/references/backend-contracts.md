# Backend Contracts

Load this reference for HTTP boundaries, dependency injection, persistence,
curated-app APIs, editor AI, or execution-queue changes.

## HTTP And Browser Trust

- The app serves JSON `/api/v1/*` APIs and the Vue/Vite SPA, not SSR/HTMX pages.
  Register `web/routes/spa_fallback.py` last in `web/router.py`; it must not
  intercept API, static, or observability routes.
- Router modules under `web/api/v1/` and `web/routes/` must not use
  `from __future__ import annotations`; OpenAPI contract tests cover this
  typing boundary (`tests/unit/web/test_openapi_contracts.py`).
- For endpoints returning different Starlette response classes, annotate with
  `Response`, not a response-class union; set `response_class` when needed.
- HTTP handlers use `skriptoteket.web.dishka_dependencies.FromDishka`, which
  resolves through FastAPI dependencies and `request.state.dishka_container`.
  Do not use `@inject` or import `FromDishka` from
  `dishka.integrations.fastapi` in router modules.
- Protected browser app endpoints use `require_app_user_api` or its role
  wrappers in `web/auth/huleedu_app_projection.py`. Mutations trust signed
  HuleEdu Gateway context; do not add local session CSRF dependencies.
- Websockets resolve services with `resolve_from_websocket` from
  `web/dishka_dependencies.py`.
- `web/error_mapping.py` owns DomainError-to-HTTP mapping;
  `web/middleware/error_handler.py` returns JSON with
  `error: {code, message, details}` and `correlation_id`. Domain/application
  code must not raise `HTTPException`. Do not add HTML UI error pages; the
  SPA fallback alone may return minimal missing-route/build HTML.
- OpenAPI owns the frontend contract. After API model/route changes run
  `pdm run openapi-export-v1` and `pdm run fe-gen-api-types`.

## Dependency Injection And Persistence

- Depend on domain-organized `typing.Protocol` interfaces under `protocols/`.
  `di/__init__.py` assembles providers; infrastructure providers live in
  `di/infrastructure/`.
- Construct `Settings()` once in the app factory and pass it to
  `create_container(settings)`; do not introduce cached global settings.
- APP scope owns settings, engine, sessionmaker, and application singletons.
  REQUEST scope owns one AsyncSession, UoW, repositories, and handlers.
- `di/infrastructure/db.py` rolls back an open transaction when the request
  session tears down. Application handlers define transaction boundaries with
  `async with uow:`. Repositories may flush/refresh, never commit/rollback.
- ORM models live in `infrastructure/db/models/`; repositories live in
  `infrastructure/repositories/`. Use select/execute and eager loading where
  needed to prevent N+1 queries and detached relationship access.
- Domain code has no framework, Docker, network, or environment dependency;
  application handlers orchestrate protocols and cross-entity rules without
  FastAPI coupling. Workers reuse these layers rather than ad-hoc DB access.
- Use async I/O and boundary timeouts for external calls; translate failures
  into DomainError in the owning layer. Bound concurrency explicitly.

## Curated Apps

- Curated apps are shipped application modules, not generic script-tool
  wrappers. Each owns its domain language, UX, validation, typed view models,
  and app-specific endpoints end-to-end.
- For `ui_mode=bespoke_required`, keep tool/run execution internal. Clients
  must not orchestrate `start_action`, `state_rev`, or `latest_run_id` as the
  primary app contract. Runner/storage/vault/DB reuse is an implementation
  detail. The frontend contract lives in the shared
  `integrated-frontend-stack` Skriptoteket reference; presentation belongs to
  `huleedu-ui-design`.

## Editor AI

- Logs are metadata-only: never write prompts or tool code to stdout/stderr
  or databases. Error captures default off; enabled captures under
  `ARTIFACTS_ROOT/llm-captures/` are sensitive.
- Remote editor providers require `AI_REMOTE_PROVIDERS_ENABLED` and explicit
  `profile.allow_remote_fallback` consent; null denies fallback.
- Chat Completions structured output uses `response_format`; Responses uses
  `text.format`. Validate the selected payload shape before sending it.
- Focus unit proof under `tests/unit/infrastructure/llm/`; use `staging-walk`
  for real editor-flow proof. Read the affected producer's runbooks, not copied
  request examples:
  `docs/runbooks/run-skript-runbook-editor-ai-pipeline-completion-chat-edit-ops-runbook-editor-ai-pipeline-completion-chat-edit-ops.md`
  and
  `docs/runbooks/run-skript-runbook-openai-responses-api-prompt-caching-runbook-openai-responses-api-prompt-caching.md`.

## Execution Queue

- When queueing is enabled, HTTP enqueues and returns promptly. Workers claim,
  execute, and finalize jobs/artifacts. Queueing is the production default.
- Claims use `FOR UPDATE SKIP LOCKED`, finite leases, and heartbeats. The stale
  lease reaper makes abandoned jobs adoptable; adopt-first and idempotency
  checks must prevent duplicate execution after crashes/restarts.
- Synchronous execution is explicit via `RUNNER_QUEUE_ENABLED=false` and
  retains the cap-and-reject behavior. Read ADR-SKRIPT-0062 before changing
  queue semantics; entrypoints are `workers/execution_queue_worker.py`,
  `protocols/execution_queue.py`, and the tool-run/job repositories.

## Python Conventions

- Keep files, including tests, below the 400–500-line ceiling; decompose
  functions over 50 lines and classes over 200 lines.
- Ruff owns formatting: 100-character lines, double quotes, four-space
  indentation, multiline trailing commas. Use repository command wrappers.
- Use typed Pydantic boundary models and field validators for validation;
  enable `from_attributes` when models consume ORM objects.
- Type public functions; use modern unions/collections, absolute imports,
  stdlib/third-party/local groups, and explicit imports. Protocol names end in
  `Protocol`; modules/functions/variables use snake_case, classes PascalCase,
  constants UPPER_SNAKE_CASE, private names an underscore prefix.
- Public APIs and complex private functions use Google-style docstrings;
  comments explain reasons. Keep pure computation synchronous.
- Follow established patterns without temporary workarounds; propose a missing
  pattern before implementation.
- Catch specific exceptions; handle or re-raise them with exception chaining.
  Do not swallow failures,
  use unexplained type ignores, mutable default arguments, magic numbers, or
  global mutable state. Introduce new abstractions only for current needs and
  propose a missing architectural pattern before implementing it.
