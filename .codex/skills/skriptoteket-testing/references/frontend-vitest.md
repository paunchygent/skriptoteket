# Frontend Vitest

Use this reference for ordinary Skriptoteket Vue/Vite unit and component tests.
This is not the browser-automation lane.

## Read First

- `integrated-frontend-stack` skill
- `integrated-frontend-stack/references/skriptoteket.md`
- `integrated-frontend-stack/references/testing.md`
- `integrated-frontend-stack/references/state-and-api.md` when stores,
  schemas, or API clients are involved
- `docs/runbooks/runbook-testing.md`

## Rules

- Use Vitest, jsdom, and `@vue/test-utils` for component wiring.
- Prefer public outcomes: visible text, roles, controls, emitted effects, route
  behavior, state transitions, and recovery paths.
- Keep API client boundaries mocked through module exports and assert endpoint,
  parameters, schema parsing, and user-facing outcomes.
- Avoid snapshot-heavy tests for dynamic UI.
- Layout, responsive behavior, auth ceremonies, and screenshots require browser
  proof through the browser automation lane.

## Commands

- Focused: `pdm run fe-test -- --run <app-local-spec-path>`
- Suite: `pdm run fe-test`
- Type/lint gates: `pdm run fe-type-check`, `pdm run fe-lint`
- Build gate for shipped UI surfaces: `pdm run fe-build`
