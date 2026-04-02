# VPW ROM Example Table Donor Map

Purpose: capture the whole-board topology grammar we are borrowing for
Flunk-Out Frenzy without importing VPX/ROM code directly.

Current corrective rule:
- the board carriers in `prototypeAlphaVpwDonorMap.ts` now follow donor
  drag-point chains directly for the outer boundary, inner guides, outlanes,
  inlanes, drain guides, and shooter walls
- donor geometry is no longer supposed to be "cleaned up" into a local redraw
  before rendering

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
  - `gameitems/Ramp.RampS001.json`
  - `gameitems/Ramp.RampS002.json`
  - `gameitems/Ramp.RampS3.json`

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
- donor switch and gate footprints -> semantic anchors for launcher,
  outlane/inlane, and return-lane placement
- donor visible-device footprints -> donor-derived rollover, drop-target, scoop,
  shooter-exit, and drain anchors in `prototypeAlphaVpwDonorDevices.ts`
- donor shooter corridor -> outer shooter wall, lane divider, launcher lane
  bounds, and launch exit positioning
- donor flipper and sling objects -> flipper proportions plus donor-derived
  sling faces instead of local triangle redraws

Tracking:
- story: `docs/backlog/stories/story-25-06-flunk-out-frenzy-vpw-donor-topology-and-table-spec-rebuild.md`
- task: `docs/backlog/prs/pr-0198-flunk-out-frenzy-vpw-donor-topology-and-spec-cutover.md`
