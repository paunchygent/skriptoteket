# Browser Automation

Use this reference for browser-visible behavior, screenshots, Playwright proof,
and authenticated UI validation in Skriptoteket.

## Read First

- `playwright-testing` skill
- `.codex/rules/075-browser-automation.md`
- `docs/runbooks/runbook-agent-browser-automation.md`
- `docs/runbooks/runbook-testing.md`
- `local-devops` plus its Skriptoteket reference
- For protected shared-auth proof, HuleEdu's local auth-integration lane from
  the `local-devops` HuleEdu reference

## Lane Rules

- Use repo Playwright scripts for repeatable proof and retained artifacts.
- Use Codex browser/MCP only for small interactive inspection and visual
  iteration, then clean up the browser session per the browser runbook.
- Protected Skriptoteket SPA/API proof must enter through HuleEdu Gateway and
  the browser-session ceremony. Do not use product-backend credential POSTs,
  local cookie shortcuts, or old `/login` flows.
- Public routes can be checked directly only when the route is genuinely public
  and the proof does not claim protected-auth coverage.
- General Vite/Vitest frontend testing belongs to `integrated-frontend-stack`;
  browser automation is the separate live-proof layer.

## Before Starting

Inspect current services and occupied ports before starting or replacing a local
stack. Reuse the running lane only when it matches the proof. Do not stop
long-running services unless the user asked or the current wrong lane blocks the
requested proof.

## Proof Output

Retained scripts write artifacts under `.artifacts/<script-name>/`. For UI or
route changes, record the exact live proof in `.codex/handoff.md`.
