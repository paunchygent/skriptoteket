---
type: story
id: ST-35-01
title: "Canonical public host and edge indexability decision package"
status: ready
owners: "agents"
created: 2026-04-08
updated: 2026-04-08
epic: "EPIC-35"
dependencies:
  - "EPIC-32"
  - "ST-32-07"
  - "ST-32-08"
  - "ST-32-09"
  - "REF-launch-seo-and-search-indexing-readiness-2026-04-08"
acceptance_criteria:
  - "Given Skriptoteket currently has more than one public hostname in play, when this story is complete, then one canonical public Skriptoteket launch host is named explicitly with absolute URL, rationale, and non-canonical host behavior."
  - "Given the live 2026-04-08 edge state shows `https://skriptoteket.hule.education` serving the real app while `https://hule.education` serves a placeholder and `www.hule.education` does not resolve, when this story is reviewed, then the decision package aligns with that current reality rather than an unspecified future brand topology."
  - "Given canonical host policy affects indexing, certificates, redirects, and operator tooling, when this story is complete, then the expected behavior for `skriptoteket.hule.education`, `hule.education`, `www.hule.education`, and any other public variant is specified as one of: canonical, permanent redirect, placeholder/non-competing, or not in launch scope."
  - "Given the host decision may require edge or deployment updates, when this story is complete, then the implementation checklist includes DNS, TLS, redirect, compose/env, and search-console verification steps."
ui_impact: "No"
data_impact: "No"
---

## Context

Skriptoteket is close to launch, but the public hostname story is still ambiguous.

As of April 8, 2026:

- `https://skriptoteket.hule.education` is the live app host.
- `https://hule.education` is live but serves a placeholder.
- `www.hule.education` does not resolve.

That is survivable for a private beta, but it is not a clean launch posture for search indexing,
canonicalization, or operator ownership.

## Notes

- This is a decision-and-ops story first, not a metadata story.
- Do not start by polishing titles or sitemaps while the canonical host policy is still ambiguous.
- The current recommended launch path is to keep `https://skriptoteket.hule.education` canonical
  unless the apex is becoming the real Skriptoteket public home immediately.
- Search-console and sitemap work must consume the chosen host policy, not invent it.
- Implementation PR slices should be carved only after `REV-EPIC-35` approves the package.

## References

- Epic parent:
  [EPIC-35](../epics/epic-35-launch-seo-and-search-indexing-readiness.md)
- Evidence and analysis:
  [REF-launch-seo-and-search-indexing-readiness-2026-04-08](../../reference/ref-launch-seo-and-search-indexing-readiness-2026-04-08.md)
- Production host wiring:
  [compose.prod.yaml](../../../compose.prod.yaml)
- Hemma deploy rule:
  [080-home-server-deployment.md](../../../.agents/rules/080-home-server-deployment.md)
