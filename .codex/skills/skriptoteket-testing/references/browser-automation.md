# Browser Walk Proof

Use this reference for browser-visible behavior, screenshots, and authenticated
UI proof in Skriptoteket.

## Read First

- `.codex/rules/075-browser-automation.md`
- `docs/runbooks/run-skript-runbook-agent-browser-automation-mcp-chrome-playwright-runbook-agent-browser-automation-mcp-chrome-playwright.md`
- `docs/runbooks/run-skript-skriptoteket-staging-on-hemma-skriptoteket-staging-on-hemma.md`
  for integrated proof on Hemma staging
- `local-devops` plus its Skriptoteket reference
- For protected shared-auth proof on the local stack, HuleEdu's local
  auth-integration lane from the `local-devops` HuleEdu reference

## Lane Rules

- Prove UI and route behavior with an agent-driven click-through walk of the
  real application in a real browser session: the Claude built-in browser
  pane, the user's Chrome through Claude in Chrome, or the Codex internal
  browser. Never use Playwright, Playwright MCP, or repo Playwright scripts.
- Integrated proof walks Hemma staging at `http://127.0.0.1:15173` through the
  Mac tunnel, per the staging runbook.
- Protected Skriptoteket SPA/API proof must enter through HuleEdu Gateway and
  the browser-session ceremony. Do not use product-backend credential POSTs,
  local cookie shortcuts, or old `/login` flows.
- For any protected shared-auth or backend-dev proof that exercises the
  HuleEdu Gateway `/api` proxy, Skriptoteket backend must be the Docker
  `skriptoteket_web` service on `hule-network` with the `skriptoteket-web`
  alias. Do not run host Uvicorn for this lane: Gateway containers cannot use
  that process as `skriptoteket-web`, so app continuation will fail before the
  UI proof reaches the requested route.
- Public routes can be walked directly only when the route is genuinely public
  and the proof does not claim protected-auth coverage.
- General Vite/Vitest frontend testing belongs to `integrated-frontend-stack`;
  the browser walk is the separate live-proof layer.

## Before Starting

Inspect current services and occupied ports before starting or replacing a local
stack. Reuse the running lane only when it matches the proof. Do not stop
long-running services unless the user asked or the current wrong lane blocks the
requested proof.

## Proof Output

Capture screenshots and accessibility-tree or DOM reads from the walk. For UI
or route changes, record the origin, commit, steps walked, viewport widths, and
evidence locations in `handoff.md`.
