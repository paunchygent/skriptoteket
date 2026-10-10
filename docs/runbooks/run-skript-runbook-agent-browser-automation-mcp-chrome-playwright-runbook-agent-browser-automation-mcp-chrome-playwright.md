---
type: runbook
id: RUN-SKRIPT-runbook-agent-browser-automation-mcp-chrome-playwright
title: 'Runbook: Agent browser walk proof'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: active
retired_ids:
- RUN-agent-browser-automation
summary: 'Runbook: Agent browser walk proof'
system: skriptoteket-dev
---

## Trigger

This runbook defines how agents prove Skriptoteket UI and route behavior: an
agent-driven click-through walk of the real application in a real browser
session. Agents never use Playwright. It also defines the browser-launch rules,
because Chrome-backed browser sessions can fail when multiple launches reuse the
same browser profile or when automation targets a regular human browsing
profile.

## Preconditions

No separate preconditions is stated in the source.

## Steps

No separate steps is stated in the source.

## Expected Results

No separate expected results is stated in the source.

## Stop Conditions


Treat these as profile/session-collision signals first:

- MCP/browser launch works sometimes but fails when another Chrome-backed agent session is active.
- Process inspection shows Chrome launched with a shared automation profile path such as a fixed
  `.../mcp-chrome`.
- A second browser launch stalls, exits immediately, or behaves as if another session already owns
  the profile directory.

## Rollback

No separate rollback is stated in the source.

### Source: Contract


### 1. Default lane selection

- Prove UI and route behavior with an agent-driven click-through walk in a real
  browser session: the Claude built-in browser pane, the user's Chrome through
  Claude in Chrome, or the Codex internal browser.
- Never use Playwright: no repo Playwright scripts, no Playwright MCP, and no
  Playwright fallback.
- Walk integrated proof on Hemma staging at `http://127.0.0.1:15173` through
  the Mac tunnel, per
  `docs/runbooks/run-skript-skriptoteket-staging-on-hemma-skriptoteket-staging-on-hemma.md`.
- Enter protected routes through the HuleEdu browser-session ceremony
  (`/auth/login`, HuleEdu sign-in, `/auth/callback`). Never post credentials to
  the product backend or inject session cookies.
- Capture screenshots and accessibility-tree or DOM reads as evidence, and
  record the origin, steps, viewport widths, and evidence in `handoff.md`.
- Use attach mode (Claude in Chrome or Chrome DevTools MCP) when the task
  depends on an already-open Chrome session or its existing signed-in state.

### 2. Launch isolation rules

- Every automated Chrome launch MUST use an isolated automation profile.
- Never point automation at the user's normal Chrome `User Data` directory.
- Never share one fixed `user-data-dir` across concurrent agent/browser sessions.
- The safe default is a unique temporary profile per session, then cleanup on close.

### 3. Attach mode rules

- If the goal is to inspect or reuse an already-open Chrome session, attach to that browser via
  Chrome DevTools MCP / CDP instead of launching a second Chrome instance against the same profile.
- Attach mode is for session reuse and debugging of the user's existing state.

### 4. Blocked browser session

- If a browser session is blocked by a profile/session collision, follow the
  recovery sequence below and walk again in a repaired or different real
  browser session.
- If no real browser session can reach the target, stop and report the
  blocker. Do not substitute Playwright, scripts, or API calls and call that
  browser proof.

### Source: Decision guide


| Task shape | Lane |
|---|---|
| UI or route proof for a change | Click-through walk in a real browser session |
| Integrated proof after merge to `main` | Walk on Hemma staging `http://127.0.0.1:15173` |
| UI design, layout, or affordance review | Walk in the Claude built-in browser pane or Codex internal browser |
| Reuse the user's existing Chrome state, cookies, or manual setup | Attach mode via Claude in Chrome or Chrome DevTools MCP |
| Browser session blocked | Recover the session; otherwise report the blocker |

### Source: Internal Browser UI Inspection For Upload-Gated Apps


The Codex internal browser is the preferred live surface when the work is an
interactive UI-design inspection in the current Codex app session. It gives the
agent and product owner the same visible app state, but it cannot be treated as
a generic replacement for every browser automation capability.

For upload-gated flows such as authenticated Exam Converter, do not add
throwaway query hooks, temporary component mutation, browser-local fixtures, or
session-cookie shortcuts just to reach post-upload UI. The durable solution is
a governed dev/test-only fixture or seed-state lane that renders the real app
components after the normal HuleEdu browser-session ceremony.

Procedure for future Exam Converter UI layout work:

1. Start the Skriptoteket dev stack with the repo script and start the HuleEdu
   auth-integration provider lane when authenticated entry is needed.
2. Sign in through the HuleEdu browser-session ceremony in the internal
   browser. Do not derive proof from direct backend credential posts.
3. Navigate to the approved dev/test fixture state for the UI slice under
   review.
4. Inspect at the canonical desktop and compact workspace widths required by
   the approved slice. Record the exact viewport widths in handoff.
5. Capture screenshot or DOM evidence from the internal browser and pair it
   with the focused Vitest/typecheck/lint/build commands for closeout.

Until `PR-0327` implements the Exam Converter fixture lane, upload-dependent
post-conversion states must be treated as blocked for internal-browser-only
proof. Use existing tests or retained runtime evidence for code confidence, but
do not present that as live visual proof of the post-upload UI state.

### Source: Recovery sequence


1. Check whether another agent/browser session already owns the automation profile.
2. If the task needs isolated automation, relaunch with a unique per-session profile.
3. If the task needs the user's live Chrome state, switch to attach mode instead of relaunching.
4. If no real browser session can reach the target, stop and report the blocker.

### Source: Repo notes


- Existing Skriptoteket Playwright scripts under `scripts/` are history, not a
  proof lane. Do not run them as proof and do not add new ones.
- See `.codex/rules/075-browser-automation.md` for the walk rules and
  `docs/runbooks/run-skript-runbook-testing-pytest-vitest-playwright-runbook-testing-pytest-vitest-playwright.md`
  for the main testing entry points.

### Source: External references


- Chrome remote debugging change, published 2025-03-17: separate user data directories are required
  for automated tooling against Chrome 136+:
  <https://developer.chrome.com/blog/remote-debugging-port>
- Chrome DevTools MCP guidance: use auto-connect/attach when the task is to debug an existing
  browser session rather than start a new isolated one:
  <https://developer.chrome.com/blog/chrome-devtools-mcp-debug-your-browser-session>
