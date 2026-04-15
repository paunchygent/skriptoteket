---
type: story
id: ST-35-04
title: "Search Console, Bing, and launch-day SEO operations"
status: blocked
owners: "product-owner, deployment-operator, agents"
created: 2026-04-08
updated: 2026-04-15
epic: "EPIC-35"
dependencies:
  - "ST-35-01"
  - "ST-35-02"
  - "ST-35-03"
  - "REF-launch-seo-and-search-indexing-readiness-2026-04-08"
acceptance_criteria:
  - "Given launch readiness needs operator proof rather than guesswork, when this story ships, then Google Search Console and Bing Webmaster Tools are configured by an account-owning operator for the chosen canonical host, or the story records a blocked state with the missing access named explicitly."
  - "Given indexing cannot be guaranteed instantly, when this story ships, then the success criteria distinguish clearly between `crawlable and submitted`, `eligible for indexing`, and `already indexed`."
  - "Given launch regressions will often be operational, when this story ships, then the operator checklist covers DNS, TLS validity, redirect checks, robots, sitemap, sample URL inspection, and post-deploy revalidation."
  - "Given the canonical host may change later, when this story ships, then the rerun steps for re-verification and redirect migration are documented instead of being left implicit."
  - "Given verification tokens and console screenshots can expose account-sensitive data, when this story ships, then retained evidence uses the redacted artifact shape below and never commits raw verification tokens or account identifiers."
ui_impact: "No"
data_impact: "No"
---

## Context

The current launch assessment can verify public edge behavior from the outside, but it cannot prove
whether Search Console or Bing ownership, sitemap submission, or live indexing requests already
exist.

That means the repo still lacks an operator-visible “we know what search engines have been told”
lane even after the technical crawl fixes are in place.

## Notes

- This story is intentionally operational. It should end with a repeatable checklist, not only a
  one-time screenshot or memory of having clicked the right buttons.
- Do not promise “indexed by launch day” as a binary engineering acceptance criterion. Promise that
  the public surface is technically eligible and properly submitted.
- Keep the operator workflow aligned with the canonical host decision from `ST-35-01`.

## Operator Handoff Contract

| Responsibility | Owner | Proof shape |
|---|---|---|
| Prepare technical endpoints and curl checklist | Agents/developer | Commands and pass/fail results retained in docs or handoff |
| Verify Google Search Console property | Product owner or deployment operator with account access | Redacted note with property type, canonical host, verification method, date, and operator initials |
| Verify Bing Webmaster Tools site | Product owner or deployment operator with account access | Redacted note with site URL, verification method, date, and operator initials |
| Submit sitemap and inspect sample URLs | Product owner or deployment operator with account access | Redacted note with sitemap URL, submitted timestamp, sample URL inspection outcomes, and follow-up date |
| Revalidate after deploy or host migration | Deployment operator | Post-deploy note covering DNS, TLS, redirects, robots, sitemap, and sample URL inspection |

## Allowed Verification Methods

- Preferred: DNS verification for durable ownership when the operator controls the relevant DNS
  zone. Retain only the record type and verified date; do not retain raw token values.
- Acceptable for URL-prefix properties: HTML-file verification if the exact root-level file can be
  served publicly without authentication and without redirects that break the service's verifier.
- Acceptable for URL-prefix properties: homepage meta-tag verification only if the `ST-35-03`
  initial-HTML contract can carry the tag in the backend-served `<head>` for `/`.
- Blocked state: if no account-owning operator is available, the story may close only as
  `blocked`, with the missing account/access path and next human action recorded. It must not claim
  Search Console or Bing setup is complete.

## Redacted Evidence Fields

Retain a short Markdown note or review attachment with:

- canonical host and property/site URL
- service name: Google Search Console or Bing Webmaster Tools
- verification method category: DNS, HTML file, or meta tag
- verification result and date
- sitemap URL submitted
- sample URLs inspected
- post-deploy revalidation date
- operator initials or role, not account email

Do not retain raw verification token values, unredacted account emails, cookies, console session
URLs, or screenshots that expose account identifiers.

## Operator Checklist

1. Confirm DNS and TLS for `https://skriptoteket.hule.education`.
2. Confirm HTTP-to-HTTPS and host redirects do not split the canonical host.
3. Curl `/robots.txt`, `/sitemap.xml`, `/`, `/public/apps/classroom.group-seating-studio`, and a
   missing path after deploy.
4. Verify Google Search Console property or record the blocked owner/access state.
5. Verify Bing Webmaster Tools site or record the blocked owner/access state.
6. Submit `https://skriptoteket.hule.education/sitemap.xml`.
7. Inspect `/` and `/public/apps/classroom.group-seating-studio` in both tools when available.
8. Record post-deploy revalidation notes with redacted evidence fields only.

## Implementation Summary (as of 2026-04-15)

- `PR-0269` added
  [RUN-launch-seo-search-operations](../../runbooks/runbook-launch-seo-search-operations.md).
- The agent-owned preparation work is complete: the runbook documents technical preflight,
  Search Console, Bing Webmaster Tools, sitemap submission, URL inspection, redacted evidence, and
  host-migration rerun steps.
- This story remains `blocked` until a product owner or deployment operator with account access
  verifies Google Search Console and Bing Webmaster Tools for
  `https://skriptoteket.hule.education`, submits the sitemap, inspects the two public URLs, and
  retains redacted evidence. Missing access: account-owning operator access to both console tools
  and the chosen verification method.

## References

- Epic parent:
  [EPIC-35](../epics/epic-35-launch-seo-and-search-indexing-readiness.md)
- Evidence and analysis:
  [REF-launch-seo-and-search-indexing-readiness-2026-04-08](../../reference/ref-launch-seo-and-search-indexing-readiness-2026-04-08.md)
- Hemma deployment baseline:
  [080-home-server-deployment.md](../../../.codex/rules/080-home-server-deployment.md)
- Launch search operations runbook:
  [RUN-launch-seo-search-operations](../../runbooks/runbook-launch-seo-search-operations.md)
