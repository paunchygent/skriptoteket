/**
 * Authored playfield carrier geometry for the Flunk-Out Frenzy prototype.
 *
 * This module groups the donor-backed rails, solids, and decorative render
 * surfaces so the top-level table spec stays focused on assembly.
 */

import type { PinballTableSpec } from "../pinballTablePlanTypes";
import {
  PROTOTYPE_ALPHA_VPW_DONOR_SOURCES,
  VPW_APRON_1_POLYGON,
  VPW_APRON_2_POLYGON,
  VPW_LEFT_DRAIN_PATH,
  VPW_LEFT_INLANE_PATH,
  VPW_LEFT_OUTLANE_PATH,
  VPW_LEFT_UPPER_GUIDE_PATH,
  VPW_LEFT_UPPER_INNER_METAL_PATH,
  VPW_METAL_RAIL_3D_SPECS,
  VPW_OUTER_BOUNDARY_MAIN_PATH,
  VPW_OUTER_BOUNDARY_RENDER_PATH,
  VPW_OUTER_BOUNDARY_RIGHT_DESCENT_PATH,
  VPW_OUTER_BOUNDARY_SHOOTER_CORRIDOR_PATH,
  VPW_RIGHT_DRAIN_PATH,
  VPW_RIGHT_INLANE_PATH,
  VPW_RIGHT_OUTLANE_PATH,
  VPW_RIGHT_RECEIVE_MOUTH_INNER_POLYGON,
  VPW_RIGHT_RECEIVE_MOUTH_OUTER_POLYGON,
  VPW_RIGHT_RETURN_THROAT_SHIELD_POLYGON,
  VPW_RIGHT_UPPER_GUIDE_PATH,
  VPW_RIGHT_UPPER_INNER_METAL_PATH,
  VPW_SHOOTER_DIVIDER_POLYGON,
  VPW_SHOOTER_HANDOFF_LOWER_POLYGON,
  VPW_SHOOTER_HANDOFF_UPPER_POLYGON,
  VPW_SHOOTER_LANE_LEFT_BOUNDARY_SEGMENTS,
  VPW_SHOOTER_OUTER_POLYGON,
  scaleDonorLength,
} from "../prototypeAlphaVpwDonorMap";

const DONOR_WALL_STYLE = Object.freeze({
  renderLayer: "walls",
  fillColor: 0xe9fff4,
  fillAlpha: 0.06,
  strokeColor: 0xf2fff6,
  strokeAlpha: 0.5,
  strokeWidth: 2,
});

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

function project3DPathTo2D(path: readonly { x: number; y: number; z: number }[]) {
  return path.map((point) => ({ x: point.x, y: point.y }));
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

export const ALPHA_RAILS = [
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
] as const satisfies PinballTableSpec["rails"];

export const ALPHA_SOLIDS = [
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
] as const satisfies PinballTableSpec["solids"];

export const ALPHA_RENDER_SURFACES = [
  OUTER_BOUNDARY_WALL263_RENDER_SURFACE,
  SHOOTER_DIVIDER_EDGE_RENDER_SURFACE,
  RIGHT_RETURN_THROAT_SHIELD_SURFACE,
] as const satisfies PinballTableSpec["renderSurfaces"];
