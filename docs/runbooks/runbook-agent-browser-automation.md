---
type: runbook
id: RUN-agent-browser-automation
title: "Runbook: Agent browser automation (MCP Chrome + Playwright)"
status: active
owners: "agents"
created: 2026-03-26
updated: 2026-03-31
system: "skriptoteket-dev"
---

This runbook defines the browser-launch contract for agent-driven browser work in Skriptoteket.
It exists because Chrome-backed MCP/browser sessions can fail when multiple launches try to reuse
the same browser profile or when automation targets a regular human browsing profile.

## Contract

### 1. Default lane selection

- Use repo Playwright scripts for repeatable Skriptoteket proofs, smoke checks, screenshots, and
  authenticated UI validation.
- Use MCP Chrome/browser tools for lightweight interactive inspection, DOM/network debugging, and
  one-off manual exploration that benefits from a live browser session.
- Use attach mode instead of relaunching when the task explicitly depends on an already-open Chrome
  session or its existing signed-in state.

### 2. Launch isolation rules

- Every automated Chrome launch MUST use an isolated automation profile.
- Never point automation at the user's normal Chrome `User Data` directory.
- Never share one fixed `user-data-dir` across concurrent agent/browser sessions.
- The safe default is a unique temporary profile per session, then cleanup on close.
- Pin Playwright MCP output files to a stable writable directory outside the repo, for example
  `/Users/olofs_mba/.codex/playwright-mcp`.
- Do not rely on the MCP server's current working directory for page snapshots, console logs, or related output files.
  If cwd drifts to `/`, the server can fail with `ENOENT: no such file or directory, mkdir '/.playwright-mcp'`.

### 3. Attach mode rules

- If the goal is to inspect or reuse an already-open Chrome session, attach to that browser via
  Chrome DevTools MCP / CDP instead of launching a second Chrome instance against the same profile.
- Attach mode is for session reuse and debugging, not for default repeatable test automation.

### 4. Repo fallback rules

- If MCP Chrome is blocked by a profile/session collision, do not fall back blindly.
- For proof-only repo checks, switch to the repo's normal Playwright lane and say so explicitly.
- Prefer an existing repo Playwright script under `scripts/` before inventing a one-off script.
- If a one-off proof script is needed, keep it bounded to the current check and write artifacts
  under `.artifacts/`.

## Decision guide

| Task shape | Lane |
|---|---|
| Repeatable Skriptoteket UI proof or regression check | Repo Playwright |
| Quick DOM/layout/network inspection in an isolated browser | MCP Chrome with isolated profile |
| Reuse the user's existing Chrome state, cookies, or manual setup | Attach mode via Chrome DevTools MCP / CDP |
| MCP Chrome blocked but the task is still only a repo proof | Repo Playwright fallback |

## Failure signatures

Treat these as profile/session-collision signals first:

- MCP/browser launch works sometimes but fails when another Chrome-backed agent session is active.
- Process inspection shows Chrome launched with a shared automation profile path such as a fixed
  `.../mcp-chrome`.
- A second browser launch stalls, exits immediately, or behaves as if another session already owns
  the profile directory.

## Recovery sequence

1. Check whether another agent/browser session already owns the automation profile.
2. If the task needs isolated automation, relaunch with a unique per-session profile.
3. If the task needs the user's live Chrome state, switch to attach mode instead of relaunching.
4. If the task is only a repo proof, use the repo Playwright lane and keep the scope explicit.

## Repo notes

- Existing Skriptoteket Playwright scripts already avoid depending on a shared Chrome profile and
  are the preferred proof lane for this repo.
- See `.codex/rules/075-browser-automation.md` for repo Playwright patterns and
  `docs/runbooks/runbook-testing.md` for the main testing entry points.

## External references

- Playwright `BrowserType.launch_persistent_context`: warns that browsers do not allow multiple
  instances with the same `user_data_dir`, and warns against automating Chrome's default profile:
  <https://playwright.dev/python/docs/api/class-browsertype>
- Chrome remote debugging change, published 2025-03-17: separate user data directories are required
  for automated tooling against Chrome 136+:
  <https://developer.chrome.com/blog/remote-debugging-port>
- Chrome DevTools MCP guidance: use auto-connect/attach when the task is to debug an existing
  browser session rather than start a new isolated one:
  <https://developer.chrome.com/blog/chrome-devtools-mcp-debug-your-browser-session>
