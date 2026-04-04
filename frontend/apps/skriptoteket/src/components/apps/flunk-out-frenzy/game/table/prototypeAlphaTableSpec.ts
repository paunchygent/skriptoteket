/**
 * Prototype-alpha pinball table spec for Flunk-Out Frenzy.
 *
 * The top-level authored table now assembles focused launcher, geometry, and
 * device sub-specs so the source-of-truth table stays readable and compliant
 * with the repo file-size limits.
 */

import type { PinballTableSpec } from "./pinballTablePlanTypes";
import { VPW_DRAIN_SPEC } from "./prototypeAlphaVpwDonorDevices";
import { ALPHA_BUMPERS, ALPHA_SLINGS } from "./spec/specBumpers";
import { ALPHA_BOARD, ALPHA_FLIPPERS, ALPHA_GRAVITY } from "./spec/specCommon";
import {
  ALPHA_CAPTURE_DEVICES,
  ALPHA_GATES,
  ALPHA_POPUP_TARGETS,
  ALPHA_ROLLOVERS,
  ALPHA_SAVE_DEVICES,
  ALPHA_STANDUP_TARGETS,
  ALPHA_TRIPWIRES,
} from "./spec/specDevices";
import { ALPHA_BALL, ALPHA_LAUNCHER, ALPHA_SPAWNS } from "./spec/specLauncher";
import {
  ALPHA_RAILS,
  ALPHA_RENDER_SURFACES,
  ALPHA_SOLIDS,
} from "./spec/specPlayfieldGeometry";

export const PROTOTYPE_ALPHA_TABLE_SPEC = {
  id: "prototype-alpha",
  name: "Flunk-Out Frenzy Prototype Alpha",
  version: 1,
  board: ALPHA_BOARD,
  ballsPerGame: 3,
  gravity: ALPHA_GRAVITY,
  ball: ALPHA_BALL,
  launcher: ALPHA_LAUNCHER,
  spawns: ALPHA_SPAWNS,
  rails: ALPHA_RAILS,
  solids: ALPHA_SOLIDS,
  renderSurfaces: ALPHA_RENDER_SURFACES,
  flippers: ALPHA_FLIPPERS,
  bumpers: ALPHA_BUMPERS,
  slings: ALPHA_SLINGS,
  rollovers: ALPHA_ROLLOVERS,
  tripwires: ALPHA_TRIPWIRES,
  gates: ALPHA_GATES,
  standupTargets: ALPHA_STANDUP_TARGETS,
  popupTargets: ALPHA_POPUP_TARGETS,
  captureDevices: ALPHA_CAPTURE_DEVICES,
  saveDevices: ALPHA_SAVE_DEVICES,
  drain: {
    tag: "drain/main",
    x: VPW_DRAIN_SPEC.center.x,
    y: VPW_DRAIN_SPEC.center.y,
    width: VPW_DRAIN_SPEC.width,
    height: VPW_DRAIN_SPEC.height,
  },
} as const satisfies PinballTableSpec;
