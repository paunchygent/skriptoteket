# VPW ROM Example Table Donor Map

Purpose: capture the whole-board topology grammar we are borrowing for
Flunk-Out Frenzy without importing VPX/ROM code directly.

Current corrective rule:
- the board carriers in `prototypeAlphaVpwDonorMap.ts` now follow donor
  drag-point chains directly for the outer boundary, inner guides, outlanes,
  inlanes, drain guides, and shooter walls
- donor geometry is no longer supposed to be "cleaned up" into a local redraw
  before rendering

Semantic fidelity rule:
- richer donor objects are not allowed to be flattened into simpler local
  rectangles, circles, or axis-aligned bands just because the current schema
  cannot represent them yet
- donor lanes and launcher corridors are not allowed to be flattened into local
  `laneBounds` or other AABB containment seams when the donor defines a shaped
  lane region
- if a donor trigger, gate, or rollover shape exceeds the current authored or
  compiled schema, the schema must be extended first
- undocumented semantic remaps and "good enough" vibe-ports are not acceptable
  donor work
- `PR-0198` owns donor topology and board-carrier fidelity; `PR-0199` owns full
  donor semantic representation for richer triggers, gates, and rollover shapes

Source repo clone:
- `.artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/`

Board normalization:
- donor bounds: `1081 x 2162`
- Flunk-Out Frenzy normalized board: `600 x 1200`
- scale factor: `600 / 1081`

Borrowed boundary carriers:
- top arch and broad outer envelope:
  - `gameitems/Wall.Wall263.json`
- upper-left inner guide/orbit family:
  - `gameitems/Wall.Wall268.json`
- upper-right return/orbit family:
  - `gameitems/Wall.Wall264.json`
- lower-left outlane/inlane fork:
  - `gameitems/Wall.Wall76.json`
  - `gameitems/Wall.Wall016.json`
  - `gameitems/Wall.LeftSlingShot.json`
- lower-right outlane/inlane fork:
  - `gameitems/Wall.Wall234.json`
  - `gameitems/Wall.Wall015.json`
  - `gameitems/Wall.RightSlingShot.json`
- center drain funnel:
  - `gameitems/Wall.Wall013.json`
  - `gameitems/Wall.Wall021.json`
- shooter corridor:
  - `gameitems/Wall.Wall95.json`
  - `gameitems/Wall.Wall34.json`
  - `gameitems/Wall.Wall011.json`
  - `gameitems/Wall.Wall010.json`
  - `gameitems/Wall.Apron2.json`
  - `gameitems/Wall.Apron1.json`
- upper-right receiving mouth continuation:
  - `gameitems/Wall.Wall264.json`
  - `gameitems/Wall.Wall018.json`
  - `gameitems/Wall.Wall019.json`
- upper inner metal guide carriers:
  - `gameitems/Wall.Wall017.json`
  - `gameitems/Wall.Wall002.json`

Borrowed above-playfield metal/wire rails:
- shooter vertical wire rail:
  - `gameitems/Ramp.RampS3.json`
- shooter-mouth connector:
  - `gameitems/Ramp.RampS001.json`
- top-right wire continuation:
  - `gameitems/Ramp.RampS002.json`
- top-arch wire rail:
  - `gameitems/Ramp.RampS4.json`

Borrowed device anchors:
- flipper pivots:
  - `gameitems/Flipper.LeftFlipper.json`
  - `gameitems/Flipper.RightFlipper.json`
- flipper proportions and swing envelope hints:
  - `gameitems/Flipper.LeftFlipper.json`
  - `gameitems/Flipper.RightFlipper.json`
- sling faces:
  - `gameitems/Wall.LeftSlingShot.json`
  - `gameitems/Wall.RightSlingShot.json`
- lower inlane/outlane switch footprints:
  - `gameitems/Trigger.sw53.json`
  - `gameitems/Trigger.sw54.json`
  - `gameitems/Trigger.sw55.json`
  - `gameitems/Trigger.sw56.json`
- shooter/plunger trigger band:
  - `gameitems/Trigger.swplunger.json`
  - `gameitems/Trigger.sw16.json`
- gate placements that inform later schema work:
  - `gameitems/Gate.GateSW49.json`
  - `gameitems/Gate.GateSW51.json`
  - `gameitems/Gate.Gate001.json`
- top rollover and orbit rollover footprints:
  - `gameitems/Trigger.sw21.json`
  - `gameitems/Trigger.sw22.json`
  - `gameitems/Trigger.sw23.json`
  - `gameitems/Trigger.sw58.json`
  - `gameitems/Trigger.sw60.json`
- left drop-target bank footprints:
  - `gameitems/Wall.sw33.json`
  - `gameitems/Wall.sw34.json`
  - `gameitems/Wall.sw59.json`
- middle scoop footprint:
  - `gameitems/Trigger.sw38.json`
- drain/apron mouth relationship:
  - `gameitems/Wall.Wall013.json`
  - `gameitems/Wall.Wall021.json`
  - `gameitems/Wall.Apron2.json`

Deliberately not borrowed verbatim:
- `script.vbs` ROM/PinMAME rule code
- VPX presentation/editor artifacts in `gamedata.json`, `images.json`,
  `sounds.json`, `Primitive.*`, `Light.*`, `Flasher.*`
- dense donor wall point clouds as direct runtime truth

Current schema mapping:
- donor perimeter and lane forks -> donor-derived drag-point rail chains in
  `prototypeAlphaVpwDonorMap.ts`
- donor switch and gate footprints -> semantic anchors and provenance records
  for launcher, outlane/inlane, and return-lane placement
- donor visible-device footprints -> donor-derived rollover, drop-target, scoop,
  and drain anchors in `prototypeAlphaVpwDonorDevices.ts`
- donor shooter corridor and right-side receiving path -> outer shooter wall,
  lane divider, donor-shaped launcher lane regions, apron closure, and
  served-ball containment
- donor full-board path target -> perimeter/lane carriers plus explicit inner
  metal guides (`Wall017` / `Wall002`) and above-playfield wire rails
  (`RampS3`/`RampS001`/`RampS002`/`RampS4`) represented as provenance-backed
  elevated carriers in table spec/compile output
- donor flipper and sling objects -> flipper proportions plus donor-derived
  sling faces instead of local triangle redraws

Current semantic gap to close:
- donor shooter/plunger triggers such as `gameitems/Trigger.swplunger.json` and
  `gameitems/Trigger.sw16.json`, plus rotated gate footprints such as
  `gameitems/Gate.GateSW49.json`, exceed the current simplified trigger
  representation whenever they are reduced to plain local bounding shapes
- `PR-0199` tracks the required schema/compiler/runtime expansion so those donor
  objects can be represented directly instead of being flattened
- donor launcher-chain geometry such as `gameitems/Wall.Wall34.json` and
  `gameitems/Plunger.PlungerRose.json` must no longer be flattened into a flat
  launcher blocker plus impulse path; `PR-0200` now tracks the Rapier 3D
  launcher-chain migration required to represent that donor handoff truthfully

Tracking:
- story: `docs/backlog/stories/story-25-06-flunk-out-frenzy-vpw-donor-topology-and-table-spec-rebuild.md`
- task: `docs/backlog/prs/pr-0198-flunk-out-frenzy-vpw-donor-topology-and-spec-cutover.md`
- follow-up task:
  `docs/backlog/prs/pr-0199-flunk-out-frenzy-donor-semantic-representation-and-trigger-shape-fidelity.md`
- launcher-chain follow-up:
  `docs/backlog/prs/pr-0200-flunk-out-frenzy-launcher-release-path-and-donor-wall-face-representation.md`
- full-board 3D donor-carrier follow-up:
  `docs/backlog/prs/pr-0202-flunk-out-frenzy-full-board-donor-3d-carrier-mapping-and-elevated-rails.md`
