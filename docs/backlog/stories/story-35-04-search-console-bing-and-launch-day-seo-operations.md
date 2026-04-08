---
type: story
id: ST-35-04
title: "Search Console, Bing, and launch-day SEO operations"
status: ready
owners: "agents"
created: 2026-04-08
updated: 2026-04-08
epic: "EPIC-35"
dependencies:
  - "ST-35-01"
  - "ST-35-02"
  - "ST-35-03"
  - "REF-launch-seo-and-search-indexing-readiness-2026-04-08"
acceptance_criteria:
  - "Given launch readiness needs operator proof rather than guesswork, when this story ships, then Google Search Console and Bing Webmaster Tools are configured for the chosen canonical host and the sitemap submission path is documented."
  - "Given indexing cannot be guaranteed instantly, when this story ships, then the success criteria distinguish clearly between `crawlable and submitted`, `eligible for indexing`, and `already indexed`."
  - "Given launch regressions will often be operational, when this story ships, then the operator checklist covers DNS, TLS validity, redirect checks, robots, sitemap, sample URL inspection, and post-deploy revalidation."
  - "Given the canonical host may change later, when this story ships, then the rerun steps for re-verification and redirect migration are documented instead of being left implicit."
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

## References

- Epic parent:
  [EPIC-35](../epics/epic-35-launch-seo-and-search-indexing-readiness.md)
- Evidence and analysis:
  [REF-launch-seo-and-search-indexing-readiness-2026-04-08](../../reference/ref-launch-seo-and-search-indexing-readiness-2026-04-08.md)
- Hemma deployment baseline:
  [080-home-server-deployment.md](../../../.agents/rules/080-home-server-deployment.md)
