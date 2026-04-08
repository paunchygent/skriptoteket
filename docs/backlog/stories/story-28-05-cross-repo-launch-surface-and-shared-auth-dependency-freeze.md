---
type: story
id: ST-28-05
title: "Cross-repo launch surface and shared auth dependency freeze"
status: ready
owners: "agents"
created: 2026-04-08
updated: 2026-04-08
epic: "EPIC-28"
dependencies:
  - "ADR-0076"
  - "EPIC-32"
  - "REF-huleedu-launch-surface-and-shared-auth-topology-2026-04-08"
acceptance_criteria:
  - "Given the launch-critical public surface now spans HuleEdu and Skriptoteket, when this story is complete, then the canonical host topology is frozen explicitly as `https://hule.education` for the HuleEdu landing page, `https://api.hule.education` for the shared browser auth/API edge, and `https://skriptoteket.hule.education` for the canonical public Skriptoteket app host."
  - "Given the current browser auth cutover depends on upstream HuleEdu work, when this story is complete, then the ownership matrix names clearly which work belongs to the HuleEdu repo/platform versus the Skriptoteket repo and which downstream stories remain blocked until the upstream edge exists."
  - "Given launch pacing matters, when this story is complete, then the phased critical path distinguishes platform-first decisions and rollout gates from later Skriptoteket-local SEO hardening and polish."
  - "Given Skriptoteket should not harden around a temporary apex vacancy, when this story is reviewed, then `EPIC-28` and `EPIC-35` both consume the same frozen topology and shared-auth assumptions."
ui_impact: "No"
data_impact: "No"
---

## Context

The original `EPIC-28` package correctly identified the target browser auth contract, but it still
assumed the shared HuleEdu session surface would simply appear as a ready dependency.

That is no longer enough. The real launch concern is broader and cross-repo:

- `hule.education` should become the HuleEdu landing page
- `api.hule.education` should become the HuleEdu Identity/Gateway edge
- `skriptoteket.hule.education` should remain the canonical public Skriptoteket app host

Without one explicit dependency-freeze story, later work risks mixing upstream platform rollout,
Skriptoteket auth cutover, and SEO cleanup into one blurry critical path.

## Notes

- This is the sequencing and ownership gate for the rest of `EPIC-28`.
- It is also the upstream dependency freeze that `EPIC-35` should consume rather than recreate.
- The story is planning-first and cross-repo by design. It should not be reduced to a local frontend
  implementation slice.

## References

- Epic parent:
  [EPIC-28](../epics/epic-28-skriptoteket-auth-authority-cutover-to-huleedu.md)
- Cross-repo topology reference:
  [REF-huleedu-launch-surface-and-shared-auth-topology-2026-04-08](../../reference/ref-huleedu-launch-surface-and-shared-auth-topology-2026-04-08.md)
- Browser-session target:
  [ADR-0076](../../adr/adr-0076-huleedu-owned-browser-session-authority-for-skriptoteket.md)
- Downstream launch SEO epic:
  [EPIC-35](../epics/epic-35-launch-seo-and-search-indexing-readiness.md)
