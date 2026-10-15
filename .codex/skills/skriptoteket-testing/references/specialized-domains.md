# Specialized Test Domains

Use this reference when the test area has a narrower repo contract than general
pytest or Vitest.

## Worker And Runtime

- Read `docs/decisions/adr-skript-0062-execution-queue-and-worker-loop-postgres.md`.
- Use backend protocol/DI seams for worker dependencies.
- Test enqueue/dequeue, retry, terminal state, idempotency, and correlation
  behavior without hiding state transitions in broad mocks.

## Observability

- Use `observability-stack`.
- Assert structured log fields, correlation IDs, metric names/labels, and trace
  boundaries where behavior depends on them.
- Do not leak PII or secrets into proof artifacts.

## PDF And Export Behavior

- Use `docs/runbooks/run-skript-runbook-testing-pytest-vitest-playwright-runbook-testing-pytest-vitest-playwright.md` for local PDF renderer caveats.
- For WeasyPrint `HTML(string=...)`, prove `base_url` and relative asset
  resolution instead of papering over missing images.
- Klassrumskartan-owned PDF rendering stays local to Skriptoteket; Sir Convert
  remains for general conversion/import workflows.

## Curated Apps

- Read `repo-code-map` and the app-owned reference/backlog
  docs before adding tests.
- Test the app contract at its natural boundary: domain projection, API
  contract, or SPA interaction.
- Use the shared staging-walk skill for staging and browser proof on Hemma.
