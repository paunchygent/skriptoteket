---
type: pr
id: PR-0269
title: "ST-35-04 search console and launch SEO operations"
status: done
owners: "agents"
created: 2026-04-15
updated: 2026-04-15
stories:
  - "ST-35-04"
tags: ["seo", "operations", "runbook"]
acceptance_criteria:
  - "Given launch search setup is account-bound, when this slice closes, then the repo records the exact human operator access still required for Google Search Console and Bing Webmaster Tools."
  - "Given search submission is not the same as indexing, when this slice closes, then the runbook distinguishes crawlable/submitted, eligible for indexing, and already indexed states."
  - "Given launch regressions are often operational, when this slice closes, then the runbook covers DNS, TLS, redirects, robots, sitemap, sample URL inspection, and post-deploy revalidation."
  - "Given retained evidence may expose account-sensitive data, when this slice closes, then the approved redacted evidence template is documented."
---

## Problem

The technical crawl lane is now implemented, but Google Search Console and Bing Webmaster Tools
ownership, sitemap submission, and URL inspection require account-owning operator access that an
agent cannot safely fake or retain.

## Goal

Provide a repeatable launch SEO operations runbook and close the agent-owned preparation work while
recording the account-bound human action that still blocks full `ST-35-04` completion.

## Non-goals

- Do not retain raw Search Console or Bing verification tokens.
- Do not commit account emails, console screenshots, cookies, session URLs, or API keys.
- Do not claim that submitted URLs are already indexed.
- Do not add IndexNow implementation in this slice.

## Implementation plan

- Add the launch SEO/search operations runbook.
- Include official-source-backed Google and Bing workflow notes.
- Add a redacted evidence template for operator proof.
- Update `ST-35-04`, `EPIC-35`, the docs index, and the current handoff.

## Test plan

- `pdm run docs-validate`
- `git diff --check`

## Rollback plan

Revert this PR doc and runbook/index/story/epic/handoff updates. This does not affect runtime
search behavior shipped in `PR-0267` and `PR-0268`.

## Implementation Summary (as of 2026-04-15)

- Added `RUN-launch-seo-search-operations`.
- Recorded that `ST-35-04` is blocked on an account-owning product owner or deployment operator
  verifying Google Search Console and Bing Webmaster Tools, submitting the sitemap, and retaining
  only redacted evidence.
