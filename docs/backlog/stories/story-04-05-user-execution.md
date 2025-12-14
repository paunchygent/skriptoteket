---
type: story
id: ST-04-05
title: "User execution of active tools"
status: ready
owners: "agents"
created: 2025-12-14
epic: "EPIC-04"
acceptance_criteria:
  - "Given I am a logged-in User, when I visit the tool run page, I see the upload form."
  - "Given I upload a file and run, then the ACTIVE version executes in PRODUCTION context."
  - "Given the run completes, then I see the HTML result rendered nicely."
  - "Given the run fails, I see a friendly error message (not raw stack traces)."
  - "Given I try to run a tool that is not published, then I get a 404."
  - "Given I have run a tool, when I visit /my-runs/{run_id}, then I can view that past result."
---

## Context

This story delivers the value to the end-users: the ability to actually use the tools created by admins.

## Scope

- **Web Routes:**
  - `GET /tools/{slug}/run` - Show run form.
  - `POST /tools/{slug}/run` - Execute tool.
  - `GET /my-runs/{run_id}` - View result/history.
- **Application:**
  - `RunActiveToolHandler`: Resolves active version, triggers runner with `production` context.
- **Views:**
  - `templates/tools/run.html`: User-facing run page.
  - `templates/tools/result.html`: Result display.

## Differences from Sandbox

- **Context:** `RunContext.PRODUCTION`
- **Networking:** v0.2 defaults to disabled (`--network none`). Per-tool network is deferred until a policy/config model exists.
- **Secrets:** v0.2 injects no production secrets. Per-tool secrets injection is deferred until explicitly modeled.
- **Logs:** Runs may store stdout/stderr for admin debugging, but end-users do not see them. Users see only `html_output` and a friendly `error_summary`.
