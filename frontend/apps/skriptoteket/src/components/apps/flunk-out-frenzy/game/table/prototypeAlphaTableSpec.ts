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
  VPW_LAUNCH_LANE_EXIT_TRIGGER_SPEC,
  VPW_PLUNGER_ROSE_3D_SPEC,
  VPW_POPUP_TARGET_SPECS,
  VPW_RIGHT_RETURN_TRIGGER_SPEC,
  VPW_SHOOTER_PLUNGER_TRIGGER_SPEC,
  VPW_TOP_ROLLOVER_SPECS,
} from "./prototypeAlphaVpwDonorDevices";
import {
  PROTOTYPE_ALPHA_VPW_DONOR_BOARD,
  PROTOTYPE_ALPHA_VPW_DONOR_SOURCES,
  VPW_BUMPER_CENTERS,
  VPW_FLIPPER_GEOMETRY,
  VPW_FLIPPER_PIVOTS,
  VPW_LEFT_DRAIN_PATH,
  VPW_LEFT_INLANE_PATH,
  VPW_LEFT_SLING_TRIANGLE,
  VPW_LEFT_UPPER_INNER_METAL_PATH,
  VPW_LEFT_OUTLANE_PATH,
  VPW_LEFT_UPPER_GUIDE_PATH,
  VPW_LAUNCH_TRAVEL_ROUTE_OVERHEAD_3D_PATH,
  VPW_LAUNCH_TRAVEL_ROUTE_OVERHEAD_DONOR_SOURCES,
  VPW_METAL_RAIL_3D_SPECS,
  VPW_OUTER_BOUNDARY_MAIN_PATH,
  VPW_OUTER_BOUNDARY_RIGHT_DESCENT_PATH,
  VPW_OUTER_BOUNDARY_RENDER_PATH,
  VPW_OUTER_BOUNDARY_SHOOTER_CORRIDOR_PATH,
  VPW_RIGHT_DRAIN_PATH,
  VPW_RIGHT_INLANE_PATH,
  VPW_RIGHT_UPPER_INNER_METAL_PATH,
  VPW_RIGHT_RECEIVE_MOUTH_INNER_POLYGON,
  VPW_RIGHT_RECEIVE_MOUTH_OUTER_POLYGON,
  VPW_RIGHT_OUTLANE_PATH,
  VPW_RIGHT_SLING_TRIANGLE,
  VPW_RIGHT_RETURN_THROAT_SHIELD_POLYGON,
  VPW_RIGHT_UPPER_GUIDE_PATH,
  VPW_SHOOTER_HANDOFF_LOWER_POLYGON,
  VPW_SHOOTER_HANDOFF_UPPER_POLYGON,
  VPW_SHOOTER_LANE_LEFT_BOUNDARY_SEGMENTS,
  VPW_SHOOTER_OUTER_INNER_EDGE,
  VPW_SHOOTER_DIVIDER_POLYGON,
  VPW_SHOOTER_OUTER_POLYGON,
  VPW_APRON_1_POLYGON,
  VPW_APRON_2_POLYGON,
  scaleDonorLength,
} from "./prototypeAlphaVpwDonorMap";

const BOARD_WIDTH = PROTOTYPE_ALPHA_VPW_DONOR_BOARD.width;
const BOARD_HEIGHT = PROTOTYPE_ALPHA_VPW_DONOR_BOARD.height;
const BALL_RADIUS = 12;
const SHOOTER_REST_CLEARANCE = 2;
const PLUNGER_TRIGGER_SHAPE = VPW_SHOOTER_PLUNGER_TRIGGER_SPEC.shape;
const SHOOTER_LANE_REGIONS = PLUNGER_TRIGGER_SHAPE.kind === "rect"
  ? [
      {
        kind: "rect" as const,
        center: PLUNGER_TRIGGER_SHAPE.center,
        width: PLUNGER_TRIGGER_SHAPE.width,
        height: PLUNGER_TRIGGER_SHAPE.height,
        angleDeg: PLUNGER_TRIGGER_SHAPE.angleDeg,
      },
      {
        kind: "donor-corridor" as const,
        leftBoundary: VPW_SHOOTER_LANE_LEFT_BOUNDARY_SEGMENTS.apronToPlunger,
        rightBoundary: VPW_SHOOTER_OUTER_INNER_EDGE,
      },
      {
        kind: "donor-corridor" as const,
        leftBoundary: VPW_SHOOTER_LANE_LEFT_BOUNDARY_SEGMENTS.divider,
        rightBoundary: VPW_SHOOTER_OUTER_INNER_EDGE,
      },
      {
        kind: "donor-corridor" as const,
        leftBoundary: VPW_SHOOTER_LANE_LEFT_BOUNDARY_SEGMENTS.wall011ToDivider,
        rightBoundary: VPW_SHOOTER_OUTER_INNER_EDGE,
      },
      {
        kind: "donor-corridor" as const,
        leftBoundary: VPW_SHOOTER_LANE_LEFT_BOUNDARY_SEGMENTS.wall011,
        rightBoundary: VPW_SHOOTER_OUTER_INNER_EDGE,
      },
      {
        kind: "donor-corridor" as const,
        leftBoundary: VPW_SHOOTER_LANE_LEFT_BOUNDARY_SEGMENTS.wall010ToWall011,
        rightBoundary: VPW_SHOOTER_OUTER_INNER_EDGE,
      },
      {
        kind: "donor-corridor" as const,
        leftBoundary: VPW_SHOOTER_LANE_LEFT_BOUNDARY_SEGMENTS.wall010,
        rightBoundary: VPW_SHOOTER_OUTER_INNER_EDGE,
      },
      {
        kind: "donor-corridor" as const,
        leftBoundary: VPW_SHOOTER_LANE_LEFT_BOUNDARY_SEGMENTS.upperHandoff,
        rightBoundary: VPW_SHOOTER_OUTER_INNER_EDGE,
      },
    ]
  : [];

const BALL_SPAWN = v(
  PLUNGER_TRIGGER_SHAPE.kind === "rect"
    ? PLUNGER_TRIGGER_SHAPE.center.x
    : BOARD_WIDTH / 2,
  PLUNGER_TRIGGER_SHAPE.kind === "rect"
    ? Math.min(
        PLUNGER_TRIGGER_SHAPE.center.y
          + PLUNGER_TRIGGER_SHAPE.height / 2
          - BALL_RADIUS
          - SHOOTER_REST_CLEARANCE,
        PLUNGER_TRIGGER_SHAPE.center.y
          + PLUNGER_TRIGGER_SHAPE.height / 2
          - BALL_RADIUS
          - SHOOTER_REST_CLEARANCE,
      )
    : BOARD_HEIGHT - BALL_RADIUS - SHOOTER_REST_CLEARANCE,
);

const CONTACT_MODEL = {
  minImpulse: 280,
  maxImpulse: 840,
  maxContactDistance: 22,
  minContactRatio: 0.22,
  maxContactRatio: 0.98,
  liftBias: 0.9,
  lateralBias: 0.22,
} as const;

const DONOR_WALL_STYLE = Object.freeze({
  renderLayer: "walls",
  fillColor: 0xe9fff4,
  fillAlpha: 0.06,
  strokeColor: 0xf2fff6,
  strokeAlpha: 0.5,
  strokeWidth: 2,
});

// Wall024 is a donor-authored elevated shield (height 60-120 in VPW) with a
// non-convex footprint. The current 2D schema cannot carry that elevation
// truthfully as a collider without inventing a decomposition, so we keep it as
// an explicit donor render surface until z-aware collision support exists.
const RIGHT_RETURN_THROAT_SHIELD_SURFACE = Object.freeze({
  kind: "polygon" as const,
  id: "right-return-throat-shield",
  points: VPW_RIGHT_RETURN_THROAT_SHIELD_POLYGON,
  layer: "walls",
  fillColor: 0xe9fff4,
  fillAlpha: 0.06,
  strokeColor: 0xf2fff6,
  strokeAlpha: 0.5,
  strokeWidth: 2,
});

const OUTER_BOUNDARY_WALL263_RENDER_SURFACE = Object.freeze({
  kind: "polyline" as const,
  id: "outer-boundary-wall263-render",
  points: VPW_OUTER_BOUNDARY_RENDER_PATH,
  thickness: 16,
  layer: "walls",
});

const SHOOTER_DIVIDER_EDGE_RENDER_SURFACE = Object.freeze({
  kind: "polyline" as const,
  id: "shooter-divider-edge-render",
  points: VPW_SHOOTER_LANE_LEFT_BOUNDARY_SEGMENTS.divider,
  thickness: 4,
  layer: "walls",
});

const LAUNCHER_CHAIN_WALLS_3D = Object.freeze([
  {
    tag: "launcher/wall95",
    donorSourceId: PROTOTYPE_ALPHA_VPW_DONOR_SOURCES.shooterOuterWall,
    points: VPW_SHOOTER_OUTER_POLYGON,
    heightBottom: 0,
    heightTop: scaleDonorLength(50),
  },
  {
    tag: "launcher/wall34",
    donorSourceId: PROTOTYPE_ALPHA_VPW_DONOR_SOURCES.shooterLaneDivider,
    points: VPW_SHOOTER_DIVIDER_POLYGON,
    heightBottom: 0,
    heightTop: scaleDonorLength(50),
  },
  {
    tag: "launcher/wall011",
    donorSourceId: PROTOTYPE_ALPHA_VPW_DONOR_SOURCES.shooterHandoffLower,
    points: VPW_SHOOTER_HANDOFF_LOWER_POLYGON,
    heightBottom: 0,
    heightTop: scaleDonorLength(50),
  },
  {
    tag: "launcher/wall010",
    donorSourceId: PROTOTYPE_ALPHA_VPW_DONOR_SOURCES.shooterHandoffUpper,
    points: VPW_SHOOTER_HANDOFF_UPPER_POLYGON,
    heightBottom: 0,
    heightTop: scaleDonorLength(50),
  },
  {
    tag: "launcher/apron1",
    donorSourceId: PROTOTYPE_ALPHA_VPW_DONOR_SOURCES.apron1,
    points: VPW_APRON_1_POLYGON,
    heightBottom: 0,
    heightTop: scaleDonorLength(55),
  },
  {
    tag: "launcher/apron2",
    donorSourceId: PROTOTYPE_ALPHA_VPW_DONOR_SOURCES.apron2,
    points: VPW_APRON_2_POLYGON,
    heightBottom: 0,
    heightTop: scaleDonorLength(55),
  },
  {
    tag: "launcher/wall018",
    donorSourceId: PROTOTYPE_ALPHA_VPW_DONOR_SOURCES.rightReceiveMouthOuter,
    points: VPW_RIGHT_RECEIVE_MOUTH_OUTER_POLYGON,
    heightBottom: scaleDonorLength(180),
    heightTop: scaleDonorLength(180),
  },
  {
    tag: "launcher/wall019",
    donorSourceId: PROTOTYPE_ALPHA_VPW_DONOR_SOURCES.rightReceiveMouthInner,
    points: VPW_RIGHT_RECEIVE_MOUTH_INNER_POLYGON,
    heightBottom: scaleDonorLength(180),
    heightTop: scaleDonorLength(270),
  },
] as const);

const LAUNCHER_CHAIN_GUIDE_RAILS_3D = Object.freeze([
  {
    tag: "launcher/wall263-shoulder",
    donorSourceId: PROTOTYPE_ALPHA_VPW_DONOR_SOURCES.outerBoundary,
    path: VPW_OUTER_BOUNDARY_SHOOTER_CORRIDOR_PATH,
    radius: 2,
    heightBottom: 0,
    heightTop: scaleDonorLength(50),
  },
  {
    tag: "launcher/wall264",
    donorSourceId: PROTOTYPE_ALPHA_VPW_DONOR_SOURCES.rightUpperGuide,
    path: VPW_RIGHT_UPPER_GUIDE_PATH,
    radius: 7,
    heightBottom: 0,
    heightTop: scaleDonorLength(50),
  },
] as const);

const LAUNCHER_CHAIN_SENSORS_3D = Object.freeze([
  {
    tag: "launcher/feed",
    donorSourceIds: VPW_SHOOTER_PLUNGER_TRIGGER_SPEC.donorSourceIds,
    shape: VPW_SHOOTER_PLUNGER_TRIGGER_SPEC.shape,
    triggerPhase: VPW_SHOOTER_PLUNGER_TRIGGER_SPEC.triggerPhase,
    semanticRole: "feed" as const,
  },
  {
    tag: "gate/launch-lane-exit",
    donorSourceIds: VPW_LAUNCH_LANE_EXIT_TRIGGER_SPEC.donorSourceIds,
    shape: VPW_LAUNCH_LANE_EXIT_TRIGGER_SPEC.shape,
    triggerPhase: VPW_LAUNCH_LANE_EXIT_TRIGGER_SPEC.triggerPhase,
    semanticRole: "exit" as const,
  },
] as const);

const LAUNCHER_CHAIN_TRAVEL_ROUTES_3D = Object.freeze([
  {
    tag: "launcher/travel/overhead",
    donorSourceIds: VPW_LAUNCH_TRAVEL_ROUTE_OVERHEAD_DONOR_SOURCES,
    path: VPW_LAUNCH_TRAVEL_ROUTE_OVERHEAD_3D_PATH,
    minChargeRatio: 0.2,
    handoffVelocity: v(-140, 360),
    handoffZ: BALL_RADIUS,
  },
] as const);

const FLIPPER_LENGTH = VPW_FLIPPER_GEOMETRY.length;
const FLIPPER_THICKNESS = VPW_FLIPPER_GEOMETRY.thickness;

function project3DPathTo2D(path: readonly { x: number; y: number; z: number }[]) {
  return path.map((point) => v(point.x, point.y));
}

function pathZProfile(path: readonly { x: number; y: number; z: number }[]) {
  return path.map((point) => point.z);
}

function donorMetalRailSpec(args: {
  id: string;
  donorSourceId: string;
  path: readonly { x: number; y: number; z: number }[];
  radius: number;
  heightBottom: number;
  heightTop: number;
  physics: boolean;
}) {
  return {
    id: args.id,
    donorSourceId: args.donorSourceId,
    path: project3DPathTo2D(args.path),
    zPath: pathZProfile(args.path),
    radius: args.radius,
    heightBottom: args.heightBottom,
    heightTop: args.heightTop,
    physics: args.physics,
    renderLayer: "overhead-guides",
  } as const;
}

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
    radius: BALL_RADIUS,
    spawn: BALL_SPAWN,
    mass: 1,
  },
  launcher: {
    tag: "launcher/main",
    laneRegions: SHOOTER_LANE_REGIONS,
    feedSettledSpeedMax: 40,
    chargeMsMin: 160,
    chargeMsMax: 900,
    relaunchCooldownMs: 120,
    launchImpulseMin: 1700,
    launchImpulseMax: 2500,
    launchAssistX: 0,
    threeD: {
      plunger: VPW_PLUNGER_ROSE_3D_SPEC,
      walls: LAUNCHER_CHAIN_WALLS_3D,
      guideRails: LAUNCHER_CHAIN_GUIDE_RAILS_3D,
      sensors: LAUNCHER_CHAIN_SENSORS_3D,
      travelRoutes: LAUNCHER_CHAIN_TRAVEL_ROUTES_3D,
      ballRestZ: BALL_RADIUS,
    },
  },
  spawns: [
    {
      id: "spawn/main",
      position: BALL_SPAWN,
      launchVelocity: v(0, 0),
      tags: ["serve"],
    },
  ],
  rails: [
    {
      id: "outer-boundary-main",
      path: VPW_OUTER_BOUNDARY_MAIN_PATH,
      radius: 8,
      renderLayer: "walls",
      render: false,
    },
    {
      id: "outer-boundary-shooter-corridor",
      path: VPW_OUTER_BOUNDARY_SHOOTER_CORRIDOR_PATH,
      radius: 2,
      renderLayer: "walls",
      render: false,
    },
    {
      id: "outer-boundary-right-descent",
      path: VPW_OUTER_BOUNDARY_RIGHT_DESCENT_PATH,
      radius: 2,
      donorSourceId: PROTOTYPE_ALPHA_VPW_DONOR_SOURCES.outerBoundary,
      renderLayer: "walls",
      render: false,
    },
    {
      id: "upper-left-guide",
      path: VPW_LEFT_UPPER_GUIDE_PATH,
      radius: 7,
      donorSourceId: PROTOTYPE_ALPHA_VPW_DONOR_SOURCES.leftUpperGuide,
      renderLayer: "walls",
    },
    {
      id: "upper-right-guide",
      path: VPW_RIGHT_UPPER_GUIDE_PATH,
      radius: 7,
      donorSourceId: PROTOTYPE_ALPHA_VPW_DONOR_SOURCES.rightUpperGuide,
      renderLayer: "walls",
    },
    {
      id: "upper-left-inner-metal-wall017",
      path: VPW_LEFT_UPPER_INNER_METAL_PATH,
      radius: 2,
      donorSourceId: PROTOTYPE_ALPHA_VPW_DONOR_SOURCES.leftUpperInnerMetal,
      renderLayer: "walls",
    },
    {
      id: "upper-right-inner-metal-wall002",
      path: VPW_RIGHT_UPPER_INNER_METAL_PATH,
      radius: 2,
      donorSourceId: PROTOTYPE_ALPHA_VPW_DONOR_SOURCES.rightUpperInnerMetal,
      renderLayer: "walls",
    },
    donorMetalRailSpec({
      id: "overhead-wire-shooter-vertical-ramps3",
      donorSourceId: VPW_METAL_RAIL_3D_SPECS.shooterVertical.donorSourceId,
      path: VPW_METAL_RAIL_3D_SPECS.shooterVertical.path,
      radius: VPW_METAL_RAIL_3D_SPECS.shooterVertical.radius,
      heightBottom: VPW_METAL_RAIL_3D_SPECS.shooterVertical.heightBottom,
      heightTop: VPW_METAL_RAIL_3D_SPECS.shooterVertical.heightTop,
      physics: false,
    }),
    donorMetalRailSpec({
      id: "overhead-wire-shooter-mouth-ramps001",
      donorSourceId: VPW_METAL_RAIL_3D_SPECS.shooterMouthConnector.donorSourceId,
      path: VPW_METAL_RAIL_3D_SPECS.shooterMouthConnector.path,
      radius: VPW_METAL_RAIL_3D_SPECS.shooterMouthConnector.radius,
      heightBottom: VPW_METAL_RAIL_3D_SPECS.shooterMouthConnector.heightBottom,
      heightTop: VPW_METAL_RAIL_3D_SPECS.shooterMouthConnector.heightTop,
      physics: false,
    }),
    donorMetalRailSpec({
      id: "overhead-wire-shooter-top-right-ramps002",
      donorSourceId: VPW_METAL_RAIL_3D_SPECS.shooterTopRight.donorSourceId,
      path: VPW_METAL_RAIL_3D_SPECS.shooterTopRight.path,
      radius: VPW_METAL_RAIL_3D_SPECS.shooterTopRight.radius,
      heightBottom: VPW_METAL_RAIL_3D_SPECS.shooterTopRight.heightBottom,
      heightTop: VPW_METAL_RAIL_3D_SPECS.shooterTopRight.heightTop,
      physics: false,
    }),
    donorMetalRailSpec({
      id: "overhead-wire-shooter-top-arch-ramps4",
      donorSourceId: VPW_METAL_RAIL_3D_SPECS.shooterTopArch.donorSourceId,
      path: VPW_METAL_RAIL_3D_SPECS.shooterTopArch.path,
      radius: VPW_METAL_RAIL_3D_SPECS.shooterTopArch.radius,
      heightBottom: VPW_METAL_RAIL_3D_SPECS.shooterTopArch.heightBottom,
      heightTop: VPW_METAL_RAIL_3D_SPECS.shooterTopArch.heightTop,
      physics: false,
    }),
    { id: "left-outlane", path: VPW_LEFT_OUTLANE_PATH, radius: 7, renderLayer: "walls" },
    { id: "left-inlane-guide", path: VPW_LEFT_INLANE_PATH, radius: 7, renderLayer: "walls" },
    { id: "left-drain-guide", path: VPW_LEFT_DRAIN_PATH, radius: 7, renderLayer: "walls" },
    { id: "right-inlane-guide", path: VPW_RIGHT_INLANE_PATH, radius: 7, renderLayer: "walls" },
    { id: "right-outlane", path: VPW_RIGHT_OUTLANE_PATH, radius: 7, renderLayer: "walls" },
    { id: "right-drain-guide", path: VPW_RIGHT_DRAIN_PATH, radius: 6, renderLayer: "walls" },
  ],
  solids: [
    {
      id: "shooter-outer-wall",
      points: VPW_SHOOTER_OUTER_POLYGON,
      heightBottom: 0,
      heightTop: scaleDonorLength(50),
      ...DONOR_WALL_STYLE,
    },
    {
      id: "shooter-divider-wall34",
      points: VPW_SHOOTER_DIVIDER_POLYGON,
      heightBottom: 0,
      heightTop: scaleDonorLength(50),
      ...DONOR_WALL_STYLE,
    },
    {
      id: "right-receive-mouth-outer",
      points: VPW_RIGHT_RECEIVE_MOUTH_OUTER_POLYGON,
      heightBottom: scaleDonorLength(180),
      heightTop: scaleDonorLength(180),
      renderLayer: "overhead-guides",
      fillColor: 0x8eaebd,
      fillAlpha: 0.03,
      strokeColor: 0xa6d8ff,
      strokeAlpha: 0.24,
      strokeWidth: 1.5,
    },
    {
      id: "right-receive-mouth-inner",
      points: VPW_RIGHT_RECEIVE_MOUTH_INNER_POLYGON,
      heightBottom: scaleDonorLength(180),
      heightTop: scaleDonorLength(270),
      renderLayer: "overhead-guides",
      fillColor: 0x8eaebd,
      fillAlpha: 0.03,
      strokeColor: 0xa6d8ff,
      strokeAlpha: 0.24,
      strokeWidth: 1.5,
    },
    {
      id: "shooter-handoff-upper",
      points: VPW_SHOOTER_HANDOFF_UPPER_POLYGON,
      heightBottom: 0,
      heightTop: scaleDonorLength(50),
      ...DONOR_WALL_STYLE,
    },
    {
      id: "shooter-handoff-lower",
      points: VPW_SHOOTER_HANDOFF_LOWER_POLYGON,
      heightBottom: 0,
      heightTop: scaleDonorLength(50),
      ...DONOR_WALL_STYLE,
    },
    {
      id: "apron-1",
      points: VPW_APRON_1_POLYGON,
      heightBottom: 0,
      heightTop: scaleDonorLength(55),
      ...DONOR_WALL_STYLE,
    },
    {
      id: "apron-2",
      points: VPW_APRON_2_POLYGON,
      heightBottom: 0,
      heightTop: scaleDonorLength(55),
      ...DONOR_WALL_STYLE,
    },
  ],
  renderSurfaces: [
    OUTER_BOUNDARY_WALL263_RENDER_SURFACE,
    SHOOTER_DIVIDER_EDGE_RENDER_SURFACE,
    RIGHT_RETURN_THROAT_SHIELD_SURFACE,
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
      shape: VPW_RIGHT_RETURN_TRIGGER_SPEC.shape,
      triggerPhase: VPW_RIGHT_RETURN_TRIGGER_SPEC.triggerPhase,
      laneTag: "lane/right-orbit-return",
    },
  ],
  gates: [
    {
      tag: "gate/launch-lane-exit",
      shape: VPW_LAUNCH_LANE_EXIT_TRIGGER_SPEC.shape,
      triggerPhase: VPW_LAUNCH_LANE_EXIT_TRIGGER_SPEC.triggerPhase,
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
  captureDevices: [
    {
      tag: "capture/scoop-study",
      kind: "hole",
      x: VPW_POPUP_TARGET_SPECS.middleScoop.center.x,
      y: VPW_POPUP_TARGET_SPECS.middleScoop.center.y,
      width: 56,
      height: 56,
      holdMs: 560,
      cooldownMs: 900,
      ejectImpulse: v(-120, -1120),
    },
  ],
  saveDevices: [
    {
      tag: "save/right-kickback",
      kind: "kickback",
      x: 462,
      y: 1018,
      width: 62,
      height: 38,
      cooldownMs: 650,
      saveImpulse: v(-420, -560),
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
