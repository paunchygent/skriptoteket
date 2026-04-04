/**
 * Authored launcher configuration for the Flunk-Out Frenzy prototype table.
 *
 * This module owns the shaped lane regions, strike-ready spawn, and donor-led
 * 3D launcher provenance so the top-level table spec can stay declarative.
 */

import type { PinballTableSpec } from "../pinballTablePlanTypes";
import { v } from "../pinballTableMath";
import {
  VPW_LAUNCH_LANE_EXIT_TRIGGER_SPEC,
  VPW_PLUNGER_ROSE_3D_SPEC,
  VPW_SHOOTER_PLUNGER_TRIGGER_SPEC,
} from "../prototypeAlphaVpwDonorDevices";
import {
  PROTOTYPE_ALPHA_VPW_DONOR_SOURCES,
  VPW_APRON_1_POLYGON,
  VPW_APRON_2_POLYGON,
  VPW_LAUNCH_TRAVEL_ROUTE_DESCENT_3D_PATH,
  VPW_LAUNCH_TRAVEL_ROUTE_DESCENT_DONOR_SOURCES,
  VPW_LAUNCH_TRAVEL_ROUTE_ENDPOINT_BRIDGE_3D_PATH,
  VPW_LAUNCH_TRAVEL_ROUTE_ENDPOINT_BRIDGE_DONOR_SOURCES,
  VPW_LAUNCH_TRAVEL_ROUTE_OVERHEAD_3D_PATH,
  VPW_LAUNCH_TRAVEL_ROUTE_OVERHEAD_DONOR_SOURCES,
  VPW_OUTER_BOUNDARY_SHOOTER_CORRIDOR_PATH,
  VPW_RIGHT_RECEIVE_MOUTH_INNER_POLYGON,
  VPW_RIGHT_RECEIVE_MOUTH_OUTER_POLYGON,
  VPW_RIGHT_UPPER_GUIDE_PATH,
  VPW_SHOOTER_DIVIDER_POLYGON,
  VPW_SHOOTER_HANDOFF_LOWER_POLYGON,
  VPW_SHOOTER_HANDOFF_UPPER_POLYGON,
  VPW_SHOOTER_LANE_LEFT_BOUNDARY_SEGMENTS,
  VPW_SHOOTER_OUTER_INNER_EDGE,
  VPW_SHOOTER_OUTER_POLYGON,
  scaleDonorLength,
} from "../prototypeAlphaVpwDonorMap";
import { ALPHA_BALL_RADIUS } from "./specCommon";

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
  PLUNGER_TRIGGER_SHAPE.kind === "rect" ? PLUNGER_TRIGGER_SHAPE.center.x : 300,
  PLUNGER_TRIGGER_SHAPE.kind === "rect"
    ? Math.min(
        PLUNGER_TRIGGER_SHAPE.center.y
          + PLUNGER_TRIGGER_SHAPE.height / 2
          - ALPHA_BALL_RADIUS
          - SHOOTER_REST_CLEARANCE,
        PLUNGER_TRIGGER_SHAPE.center.y
          + PLUNGER_TRIGGER_SHAPE.height / 2
          - ALPHA_BALL_RADIUS
          - SHOOTER_REST_CLEARANCE,
      )
    : 1200 - ALPHA_BALL_RADIUS - SHOOTER_REST_CLEARANCE,
);

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
    entryMode: "release",
    minChargeRatio: 0.2,
    nextRouteTag: "launcher/travel/endpoint-bridge",
  },
  {
    tag: "launcher/travel/endpoint-bridge",
    donorSourceIds: VPW_LAUNCH_TRAVEL_ROUTE_ENDPOINT_BRIDGE_DONOR_SOURCES,
    path: VPW_LAUNCH_TRAVEL_ROUTE_ENDPOINT_BRIDGE_3D_PATH,
    entryMode: "chain",
    minChargeRatio: 0,
    nextRouteTag: "launcher/travel/descent",
  },
  {
    tag: "launcher/travel/descent",
    donorSourceIds: VPW_LAUNCH_TRAVEL_ROUTE_DESCENT_DONOR_SOURCES,
    path: VPW_LAUNCH_TRAVEL_ROUTE_DESCENT_3D_PATH,
    entryMode: "chain",
    minChargeRatio: 0,
    handoffVelocity: v(-140, 360),
    handoffZ: ALPHA_BALL_RADIUS,
  },
] as const);

export const ALPHA_BALL = {
  radius: ALPHA_BALL_RADIUS,
  spawn: BALL_SPAWN,
  mass: 1,
} as const satisfies PinballTableSpec["ball"];

export const ALPHA_LAUNCHER = {
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
    ballRestZ: ALPHA_BALL_RADIUS,
  },
} as const satisfies PinballTableSpec["launcher"];

export const ALPHA_SPAWNS = [
  {
    id: "spawn/main",
    position: BALL_SPAWN,
    launchVelocity: v(0, 0),
    tags: ["serve"],
  },
] as const satisfies PinballTableSpec["spawns"];
