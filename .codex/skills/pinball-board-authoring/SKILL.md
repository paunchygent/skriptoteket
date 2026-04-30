---
name: pinball-board-authoring
description: Use when authoring or refactoring Skriptoteket Flunk-Out Frenzy pinball playfield geometry, shooter lanes, flippers, inlanes, outlanes, center drains, board underlays, donor table semantics, or physics-wall carriers. Generate boards from geometric primitives and canonical pinball lane grammar; never hand-draw walls, rails, or guides as ad hoc point sketches.
---

# Pinball Board Authoring

Author Skriptoteket pinball boards from geometry, not sketches.

Hard rules:
- Never hand-draw board rails, walls, lanes, or guide lines as arbitrary point clouds.
- Start from canonical playfield grammar: top arch, outer walls, shooter lane, outlanes, inlanes, center drain, slings, flipper pivots.
- Define metrics first: board size, lane widths, drain width, pivot spread, arch radius, wall insets, lower-third exits.
- Generate authored paths from primitives such as arcs, straight segments, offsets, mirrors, and lane bands.
- Use one source of truth for both visible underlay and compiled physics walls.
- When porting from a donor table, apply the same fidelity standard to donor device semantics as to donor geometry.
- Never flatten richer donor objects such as wire rollovers, rotated gates, compound triggers, or shaped sensors into simpler local rectangles or circles just because the current schema is easier to fit.
- Never flatten donor lane or launcher regions into local AABB `laneBounds` or other coarse containment boxes when the donor defines a shaped corridor or lane region.
- Lane membership, launcher feed/rest/recharge semantics, and lane-exit semantics must be expressed through donor-shaped lane-region semantics rather than inferred from approximate bounds.
- For donor elevated-route seams, keep continuity contracts strict and explicit.
  Do not relax seam tolerance to hide authored gaps.
- When two donor-owned routes do not meet at the same point, model a named
  seam artifact path from exactly the donor endpoint anchors (two points only)
  and keep provenance tied to adjacent donor carriers.
- Do not add helper rails, synthetic smoothing points, or freehand bridge
  geometry to hide launcher seams.
- If the authored or compiled schema cannot express the donor object semantics, stop and extend the schema/compiler/runtime before continuing.
- Never "vibe-port" donor devices with undocumented remaps or "good enough" approximations.
- If a board still "looks sketched," stop tuning numbers and move one level higher in abstraction.

Workflow:
1. Declare board metrics and canonical regions.
1. If using a donor table, inventory the donor object's native geometry and semantics before mapping.
1. Generate rails and guides from primitives.
1. Extend the authored and compiled representation whenever donor semantics exceed the current model, including donor-shaped lane regions and launcher corridors.
1. Compile generated rails and explicit device semantics into the runtime plan.
1. Render the same generated geometry and semantic footprints in the underlay or debug view.
1. Only after the board and donor semantics read correctly should mechanics tuning resume.
