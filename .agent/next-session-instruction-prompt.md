# Next Session Instruction Prompt

Role: You are the lead developer and architect of Skriptoteket.

Session scope: pick up from `main` and implement ST-03-03 “Admins publish/depublish scripts” end-to-end (domain →
application → infra → web), building on the completed ST-03-01 + ST-03-02 suggestion workflow.

Before touching code (REQUIRED):

- From repo root, read `AGENTS.md`.
- Read rules:
  - `.agent/rules/000-rule-index.md`
  - `.agent/rules/010-foundational-principles.md`
  - `.agent/rules/020-monolith-architecture.md`
  - `.agent/rules/042-async-di-patterns.md`
  - `.agent/rules/053-sqlalchemy-patterns.md`
  - `.agent/rules/070-testing-standards.md`
  - `.agent/rules/060-docker-and-compose.md`
- Read story + epic:
  - `docs/backlog/stories/story-03-03-publish-and-depublish-scripts.md`
  - `docs/backlog/epics/epic-03-script-governance-workflow.md`
- Also read current session context: `.agent/handoff.md`.

Constraints:

- Do not touch identity or Docker unless you are fixing a clear regression.
- Protocol-first DI, UoW-owned transactions, domain raises `DomainError` only, web layer maps errors to HTTP.
- Session rule (REQUIRED): for any UI/route change, do a live functional check and record exact steps in `.agent/handoff.md`.

Existing entry points (reuse patterns; don’t invent new abstractions):

- Suggestions review creates draft tools + links:
  - Domain suggestions lifecycle: `src/skriptoteket/domain/suggestions/models.py`
  - Decision handler: `src/skriptoteket/application/suggestions/handlers/decide_suggestion.py`
  - DB: `migrations/versions/0004_suggestion_review_decisions.py`
- Tool visibility is currently controlled by `tools.is_published`:
  - DB model: `src/skriptoteket/infrastructure/db/models/tool.py`
  - Tool browse query filters to published: `src/skriptoteket/infrastructure/repositories/tool_repository.py`

Recommended steps for ST-03-03:

1. Docs: set ST-03-03 → `in_progress` (keep EPIC-03 `active`).
2. Domain (pure): introduce a minimal publish/depublish model/invariants (e.g., cannot “publish” twice).
3. Application: admin-only handler(s) to publish/depublish a tool (toggle `is_published`), recording rationale/history
   if required by acceptance criteria.
4. Infrastructure: repository method(s) to update publish state; ensure UoW owns commit/rollback.
5. Web: minimal admin UI to publish/depublish tools (likely starting from tools created via accepted suggestions).
6. Tests: protocol-mocked unit tests for the new handlers (no DB tests unless you add migrations).
7. Live check (REQUIRED): run the app and verify the publish/depublish flow works; record exact steps in `.agent/handoff.md`.
8. End-of-session: update docs + `.agent/handoff.md`, and generate the next “next session” prompt for your successor.

