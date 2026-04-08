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
  - "ST-28-05"
  - "EPIC-32"
  - "ST-32-07"
  - "ST-32-08"
  - "ST-32-09"
  - "REF-huleedu-launch-surface-and-shared-auth-topology-2026-04-08"
  - "REF-launch-seo-and-search-indexing-readiness-2026-04-08"
acceptance_criteria:
  - "Given `ST-28-05` freezes the broader HuleEdu launch topology, when this story is complete, then the Skriptoteket-side host policy names explicitly the canonical public app host, the behavior of any non-canonical Skriptoteket-owned variants, and the way Skriptoteket links or defers to the HuleEdu-owned landing and gateway surfaces."
  - "Given the live 2026-04-08 edge state shows `https://skriptoteket.hule.education` serving the real app while `https://hule.education` serves a placeholder and `www.hule.education` does not resolve, when this story is reviewed, then the decision package aligns with the intended HuleEdu landing + gateway direction rather than treating the apex as Skriptoteket vacancy."
  - "Given canonical host policy affects indexing, certificates, redirects, and operator tooling, when this story is complete, then the expected behavior for `skriptoteket.hule.education`, `hule.education`, `www.hule.education`, and any other public variant is specified as one of: canonical, permanent redirect, placeholder/non-competing, or not in launch scope."
  - "Given the host decision may require edge or deployment updates, when this story is complete, then the implementation checklist includes DNS, TLS, redirect, compose/env, search-console verification, and alignment with the HuleEdu identity/gateway rollout."
ui_impact: "No"
data_impact: "No"
---

## Context

Skriptoteket is close to launch, but the public hostname story is still ambiguous if viewed in
isolation.

As of April 8, 2026:

- `https://skriptoteket.hule.education` is the live app host.
- `https://hule.education` is live but serves a placeholder.
- `https://api.hule.education` is reserved and already TLS-covered, but still placeholder-owned at
  the edge.
- `www.hule.education` does not resolve.

That means this story is no longer the owner of the whole topology decision. The topology is frozen
upstream in `ST-28-05`; this story consumes it and turns it into the correct Skriptoteket-side host
and indexability policy.

## Notes

- This is a decision-and-ops story first, not a metadata story.
- Do not start by polishing titles or sitemaps while the canonical host policy is still ambiguous.
- The current recommended launch path is to keep `https://skriptoteket.hule.education` as the
  canonical public Skriptoteket app host while `https://hule.education` becomes the HuleEdu
  landing page and `https://api.hule.education` becomes the shared auth/API edge.
- Search-console and sitemap work must consume the chosen host policy, not invent it.
- Implementation PR slices should be carved only after `REV-EPIC-35` approves the package.

## References

- Epic parent:
  [EPIC-35](../epics/epic-35-launch-seo-and-search-indexing-readiness.md)
- Upstream topology gate:
  [ST-28-05](story-28-05-cross-repo-launch-surface-and-shared-auth-dependency-freeze.md)
- Cross-repo topology reference:
  [REF-huleedu-launch-surface-and-shared-auth-topology-2026-04-08](../../reference/ref-huleedu-launch-surface-and-shared-auth-topology-2026-04-08.md)
- Evidence and analysis:
  [REF-launch-seo-and-search-indexing-readiness-2026-04-08](../../reference/ref-launch-seo-and-search-indexing-readiness-2026-04-08.md)
- Production host wiring:
  [compose.prod.yaml](../../../compose.prod.yaml)
- Hemma deploy rule:
  [080-home-server-deployment.md](../../../.agents/rules/080-home-server-deployment.md)
