# Specialized Test Domains

Use this reference when the test area has a narrower repo contract than general
pytest or Vitest.

## Worker And Runtime

- Read `.codex/rules/062-execution-queue-worker-loop.md`.
- Use backend protocol/DI seams for worker dependencies.
- Test enqueue/dequeue, retry, terminal state, idempotency, and correlation
  behavior without hiding state transitions in broad mocks.

## Observability

- Use `observability-stack` plus `.codex/rules/090-observability-index.md`.
- Assert structured log fields, correlation IDs, metric names/labels, and trace
  boundaries where behavior depends on them.
- Do not leak PII or secrets into proof artifacts.

## PDF And Export Behavior

- Use `docs/runbooks/runbook-testing.md` for local PDF renderer caveats.
- For WeasyPrint `HTML(string=...)`, prove `base_url` and relative asset
  resolution instead of papering over missing images.
- Klassrumskartan-owned PDF rendering stays local to Skriptoteket; Sir Convert
  remains for general conversion/import workflows.

## Curated Apps

- Read `.codex/rules/025-curated-apps.md` and the app-owned reference/backlog
  docs before adding tests.
- Test the app contract at its natural boundary: domain projection, API
  contract, SPA interaction, or retained browser proof.
