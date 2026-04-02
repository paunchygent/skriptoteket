/**
 * Prototype-alpha pinball table spec for Flunk-Out Frenzy.
 *
 * The current board is authored from VPW donor carriers instead of locally
 * invented lane geometry. The compiled runtime still owns physics and semantic
 * device plans; this module swaps in donor-derived board geometry while
 * keeping Flunk-Out-specific semantics on top of that skeleton.
 */

import type { PinballTableSpec } from "./pinballTablePlanTypes";
import { makeFlipperFromPivot, v } from "./pinballTableMath";
import {
  VPW_DRAIN_SPEC,
  VPW_LEFT_DROP_BANK_SPECS,
  VPW_POPUP_TARGET_SPECS,
  VPW_SHOOTER_EXIT_SPEC,
  VPW_TOP_ROLLOVER_SPECS,
} from "./prototypeAlphaVpwDonorDevices";
import {
  PROTOTYPE_ALPHA_VPW_DONOR_BOARD,
  VPW_BUMPER_CENTERS,
  VPW_FLIPPER_GEOMETRY,
  VPW_FLIPPER_PIVOTS,
  VPW_GATE_SPECS,
  VPW_LEFT_DRAIN_PATH,
  VPW_LEFT_INLANE_PATH,
  VPW_LEFT_SLING_TRIANGLE,
  VPW_LEFT_OUTLANE_PATH,
  VPW_LEFT_UPPER_GUIDE_PATH,
  VPW_OUTER_BOUNDARY_PATH,
  VPW_RIGHT_DRAIN_PATH,
  VPW_RIGHT_INLANE_PATH,
  VPW_RIGHT_OUTLANE_PATH,
  VPW_RIGHT_SLING_TRIANGLE,
  VPW_RIGHT_UPPER_GUIDE_PATH,
  VPW_SHOOTER_LANE_BOUNDS,
  VPW_SHOOTER_DIVIDER_PATH,
  VPW_SHOOTER_OUTER_PATH,
  VPW_SHOOTER_SENSOR_CENTER,
} from "./prototypeAlphaVpwDonorMap";

const BOARD_WIDTH = PROTOTYPE_ALPHA_VPW_DONOR_BOARD.width;
const BOARD_HEIGHT = PROTOTYPE_ALPHA_VPW_DONOR_BOARD.height;

const BALL_SPAWN = v(VPW_SHOOTER_SENSOR_CENTER.x, VPW_SHOOTER_SENSOR_CENTER.y + 18);

const CONTACT_MODEL = {
  minImpulse: 280,
  maxImpulse: 840,
  maxContactDistance: 22,
  minContactRatio: 0.22,
  maxContactRatio: 0.98,
  liftBias: 0.9,
  lateralBias: 0.22,
} as const;

const FLIPPER_LENGTH = VPW_FLIPPER_GEOMETRY.length;
const FLIPPER_THICKNESS = VPW_FLIPPER_GEOMETRY.thickness;

export const PROTOTYPE_ALPHA_TABLE_SPEC = {
  id: "prototype-alpha",
  name: "Flunk-Out Frenzy Prototype Alpha",
  version: 1,
  board: {
    width: BOARD_WIDTH,
    height: BOARD_HEIGHT,
    displayAspectRatio: 0.76,
  },
  ballsPerGame: 3,
  gravity: v(0, 981),
  ball: {
    radius: 12,
    spawn: BALL_SPAWN,
    mass: 1,
  },
  launcher: {
    tag: "launcher/main",
    laneBounds: VPW_SHOOTER_LANE_BOUNDS,
    feedSettledSpeedMax: 40,
    chargeMsMin: 160,
    chargeMsMax: 900,
    relaunchCooldownMs: 120,
    launchImpulseMin: 1400,
    launchImpulseMax: 2200,
    launchAssistX: -35,
  },
  spawns: [
    {
      id: "spawn/main",
      position: BALL_SPAWN,
      launchVelocity: v(0, -240),
      tags: ["serve"],
    },
  ],
  rails: [
    { id: "outer-boundary", path: VPW_OUTER_BOUNDARY_PATH, radius: 8, renderLayer: "walls" },
    { id: "upper-left-guide", path: VPW_LEFT_UPPER_GUIDE_PATH, radius: 7, renderLayer: "walls" },
    { id: "upper-right-guide", path: VPW_RIGHT_UPPER_GUIDE_PATH, radius: 7, renderLayer: "walls" },
    { id: "left-outlane", path: VPW_LEFT_OUTLANE_PATH, radius: 7, renderLayer: "walls" },
    { id: "left-inlane-guide", path: VPW_LEFT_INLANE_PATH, radius: 7, renderLayer: "walls" },
    { id: "left-drain-guide", path: VPW_LEFT_DRAIN_PATH, radius: 7, renderLayer: "walls" },
    { id: "right-inlane-guide", path: VPW_RIGHT_INLANE_PATH, radius: 7, renderLayer: "walls" },
    { id: "right-outlane", path: VPW_RIGHT_OUTLANE_PATH, radius: 7, renderLayer: "walls" },
    { id: "right-drain-guide", path: VPW_RIGHT_DRAIN_PATH, radius: 7, renderLayer: "walls" },
    { id: "shooter-outer-wall", path: VPW_SHOOTER_OUTER_PATH, radius: 6, renderLayer: "walls" },
    { id: "shooter-divider", path: VPW_SHOOTER_DIVIDER_PATH, radius: 6, renderLayer: "walls" },
  ],
  flippers: {
    left: makeFlipperFromPivot({
      id: "flipper-left",
      side: "left",
      pivot: VPW_FLIPPER_PIVOTS.left,
      length: FLIPPER_LENGTH,
      thickness: FLIPPER_THICKNESS,
      restAngleDeg: -24,
      activeAngleDeg: -58,
      contactModel: CONTACT_MODEL,
    }),
    right: makeFlipperFromPivot({
      id: "flipper-right",
      side: "right",
      pivot: VPW_FLIPPER_PIVOTS.right,
      length: FLIPPER_LENGTH,
      thickness: FLIPPER_THICKNESS,
      restAngleDeg: 24,
      activeAngleDeg: 58,
      contactModel: CONTACT_MODEL,
    }),
  },
  bumpers: [
    {
      tag: "bumper/pop-top",
      x: VPW_BUMPER_CENTERS.top.x,
      y: VPW_BUMPER_CENTERS.top.y,
      radius: 30,
      sensorRadius: 40,
      impulse: 420,
    },
    {
      tag: "bumper/pop-left",
      x: VPW_BUMPER_CENTERS.left.x,
      y: VPW_BUMPER_CENTERS.left.y,
      radius: 30,
      sensorRadius: 40,
      impulse: 420,
    },
    {
      tag: "bumper/pop-right",
      x: VPW_BUMPER_CENTERS.right.x,
      y: VPW_BUMPER_CENTERS.right.y,
      radius: 30,
      sensorRadius: 40,
      impulse: 420,
    },
  ],
  slings: [
    {
      tag: "sling/left",
      side: "left",
      vertices: [...VPW_LEFT_SLING_TRIANGLE],
      impulse: v(260, -460),
    },
    {
      tag: "sling/right",
      side: "right",
      vertices: [...VPW_RIGHT_SLING_TRIANGLE],
      impulse: v(-260, -460),
    },
  ],
  rollovers: [
    {
      tag: "lane/top-l",
      label: "L",
      x: VPW_TOP_ROLLOVER_SPECS.leftOrbit.center.x,
      y: VPW_TOP_ROLLOVER_SPECS.leftOrbit.center.y,
      width: VPW_TOP_ROLLOVER_SPECS.leftOrbit.width,
      height: VPW_TOP_ROLLOVER_SPECS.leftOrbit.height,
      bankTag: "bank/late-top",
    },
    {
      tag: "lane/top-a",
      label: "A",
      x: VPW_TOP_ROLLOVER_SPECS.topLeft.center.x,
      y: VPW_TOP_ROLLOVER_SPECS.topLeft.center.y,
      width: VPW_TOP_ROLLOVER_SPECS.topLeft.width,
      height: VPW_TOP_ROLLOVER_SPECS.topLeft.height,
      bankTag: "bank/late-top",
    },
    {
      tag: "lane/top-t",
      label: "T",
      x: VPW_TOP_ROLLOVER_SPECS.topMiddle.center.x,
      y: VPW_TOP_ROLLOVER_SPECS.topMiddle.center.y,
      width: VPW_TOP_ROLLOVER_SPECS.topMiddle.width,
      height: VPW_TOP_ROLLOVER_SPECS.topMiddle.height,
      bankTag: "bank/late-top",
    },
    {
      tag: "lane/top-e",
      label: "E",
      x: VPW_TOP_ROLLOVER_SPECS.topRight.center.x,
      y: VPW_TOP_ROLLOVER_SPECS.topRight.center.y,
      width: VPW_TOP_ROLLOVER_SPECS.topRight.width,
      height: VPW_TOP_ROLLOVER_SPECS.topRight.height,
      bankTag: "bank/late-top",
    },
  ],
  tripwires: [
    {
      tag: "tripwire/right-orbit-return",
      x: VPW_GATE_SPECS.rightReturn.center.x,
      y: VPW_GATE_SPECS.rightReturn.center.y,
      width: VPW_GATE_SPECS.rightReturn.width,
      height: VPW_GATE_SPECS.rightReturn.height,
      laneTag: "lane/right-orbit-return",
    },
  ],
  gates: [
    {
      tag: "gate/launch-lane-exit",
      x: VPW_SHOOTER_EXIT_SPEC.center.x,
      y: VPW_SHOOTER_EXIT_SPEC.center.y,
      width: VPW_SHOOTER_EXIT_SPEC.width,
      height: VPW_SHOOTER_EXIT_SPEC.height,
      laneTag: "lane/launch-exit",
    },
  ],
  standupTargets: [
    {
      tag: "target/jock-left",
      x: VPW_LEFT_DROP_BANK_SPECS.left.center.x,
      y: VPW_LEFT_DROP_BANK_SPECS.left.center.y,
      width: VPW_LEFT_DROP_BANK_SPECS.left.width,
      height: VPW_LEFT_DROP_BANK_SPECS.left.height,
      angleDeg: VPW_LEFT_DROP_BANK_SPECS.left.angleDeg,
      bankTag: "bank/jocks",
    },
    {
      tag: "target/jock-center",
      x: VPW_LEFT_DROP_BANK_SPECS.center.center.x,
      y: VPW_LEFT_DROP_BANK_SPECS.center.center.y,
      width: VPW_LEFT_DROP_BANK_SPECS.center.width,
      height: VPW_LEFT_DROP_BANK_SPECS.center.height,
      angleDeg: VPW_LEFT_DROP_BANK_SPECS.center.angleDeg,
      bankTag: "bank/jocks",
    },
    {
      tag: "target/jock-right",
      x: VPW_LEFT_DROP_BANK_SPECS.right.center.x,
      y: VPW_LEFT_DROP_BANK_SPECS.right.center.y,
      width: VPW_LEFT_DROP_BANK_SPECS.right.width,
      height: VPW_LEFT_DROP_BANK_SPECS.right.height,
      angleDeg: VPW_LEFT_DROP_BANK_SPECS.right.angleDeg,
      bankTag: "bank/jocks",
    },
  ],
  popupTargets: [
    {
      tag: "target/pop-study",
      x: VPW_POPUP_TARGET_SPECS.middleScoop.center.x,
      y: VPW_POPUP_TARGET_SPECS.middleScoop.center.y,
      radius: VPW_POPUP_TARGET_SPECS.middleScoop.radius,
      sensorRadius: VPW_POPUP_TARGET_SPECS.middleScoop.sensorRadius,
      bankTag: "bank/study-pop",
    },
  ],
  drain: {
    tag: "drain/main",
    x: VPW_DRAIN_SPEC.center.x,
    y: VPW_DRAIN_SPEC.center.y,
    width: VPW_DRAIN_SPEC.width,
    height: VPW_DRAIN_SPEC.height,
  },
} as const satisfies PinballTableSpec;
