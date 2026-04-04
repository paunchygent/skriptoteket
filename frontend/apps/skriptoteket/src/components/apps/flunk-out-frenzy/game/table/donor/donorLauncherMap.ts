/**
 * Donor-derived elevated launcher-route geometry for Flunk-Out Frenzy.
 *
 * These exports keep the overhead rails and chained 3D route anchors separate
 * from the 2D playfield map so the donor barrel can stay within repo size
 * limits without losing provenance.
 */

import {
  RAMP_S001_POINTS,
  RAMP_S002_POINTS,
  RAMP_S3_POINTS,
  RAMP_S4_POINTS,
} from "./donor3dPaths";
import {
  PROTOTYPE_ALPHA_VPW_DONOR_SOURCES,
  donorPath3DWithLinearHeightProfile,
  mergePath3DSegments,
  path3DWithLinearHeightProfile,
  planarPath,
  scaleDonorLength,
} from "./donorScale";
import { VPW_LEFT_UPPER_GUIDE_DESCENT_PATH } from "./donorPlayfieldMap";

export const VPW_METAL_RAIL_3D_SPECS = Object.freeze({
  shooterVertical: Object.freeze({
    donorSourceId: PROTOTYPE_ALPHA_VPW_DONOR_SOURCES.shooterWireVertical,
    path: donorPath3DWithLinearHeightProfile(planarPath(RAMP_S3_POINTS), 0, 180),
    radius: scaleDonorLength(3.5),
    heightBottom: scaleDonorLength(0),
    heightTop: scaleDonorLength(180),
  }),
  shooterMouthConnector: Object.freeze({
    donorSourceId: PROTOTYPE_ALPHA_VPW_DONOR_SOURCES.shooterWireMouthConnector,
    path: donorPath3DWithLinearHeightProfile(planarPath(RAMP_S001_POINTS), 180, 180),
    radius: scaleDonorLength(3.5),
    heightBottom: scaleDonorLength(180),
    heightTop: scaleDonorLength(180),
  }),
  shooterTopRight: Object.freeze({
    donorSourceId: PROTOTYPE_ALPHA_VPW_DONOR_SOURCES.shooterWireTopRight,
    path: donorPath3DWithLinearHeightProfile(planarPath(RAMP_S002_POINTS), 180, 180),
    radius: scaleDonorLength(3.5),
    heightBottom: scaleDonorLength(180),
    heightTop: scaleDonorLength(180),
  }),
  shooterTopArch: Object.freeze({
    donorSourceId: PROTOTYPE_ALPHA_VPW_DONOR_SOURCES.shooterWireTopArch,
    path: donorPath3DWithLinearHeightProfile(planarPath(RAMP_S4_POINTS), 180, 100),
    radius: scaleDonorLength(3.5),
    heightBottom: scaleDonorLength(100),
    heightTop: scaleDonorLength(180),
  }),
});

const VPW_LEFT_UPPER_GUIDE_DESCENT_PATH_3D = path3DWithLinearHeightProfile(
  VPW_LEFT_UPPER_GUIDE_DESCENT_PATH,
  scaleDonorLength(100),
  scaleDonorLength(0),
);

export const VPW_LAUNCH_TRAVEL_ROUTE_OVERHEAD_DONOR_SOURCES = Object.freeze([
  PROTOTYPE_ALPHA_VPW_DONOR_SOURCES.shooterWireVertical,
  PROTOTYPE_ALPHA_VPW_DONOR_SOURCES.shooterWireMouthConnector,
  PROTOTYPE_ALPHA_VPW_DONOR_SOURCES.shooterWireTopRight,
  PROTOTYPE_ALPHA_VPW_DONOR_SOURCES.shooterWireTopArch,
] as const);

export const VPW_LAUNCH_TRAVEL_ROUTE_OVERHEAD_3D_PATH = mergePath3DSegments([
  VPW_METAL_RAIL_3D_SPECS.shooterVertical.path,
  VPW_METAL_RAIL_3D_SPECS.shooterMouthConnector.path,
  VPW_METAL_RAIL_3D_SPECS.shooterTopRight.path,
  VPW_METAL_RAIL_3D_SPECS.shooterTopArch.path,
]);

export const VPW_LAUNCH_TRAVEL_ROUTE_OVERHEAD_EXIT_ANCHOR_3D = Object.freeze({
  ...VPW_LAUNCH_TRAVEL_ROUTE_OVERHEAD_3D_PATH[VPW_LAUNCH_TRAVEL_ROUTE_OVERHEAD_3D_PATH.length - 1],
});

export const VPW_LAUNCH_TRAVEL_ROUTE_DESCENT_DONOR_SOURCES = Object.freeze([
  PROTOTYPE_ALPHA_VPW_DONOR_SOURCES.leftUpperGuide,
] as const);

export const VPW_LAUNCH_TRAVEL_ROUTE_DESCENT_3D_PATH = mergePath3DSegments([
  VPW_LEFT_UPPER_GUIDE_DESCENT_PATH_3D,
]);

export const VPW_LAUNCH_TRAVEL_ROUTE_DESCENT_ENTRY_ANCHOR_3D = Object.freeze({
  ...VPW_LAUNCH_TRAVEL_ROUTE_DESCENT_3D_PATH[0],
});

export const VPW_LAUNCH_TRAVEL_ROUTE_ENDPOINT_BRIDGE_DONOR_SOURCES = Object.freeze([
  PROTOTYPE_ALPHA_VPW_DONOR_SOURCES.shooterWireTopArch,
  PROTOTYPE_ALPHA_VPW_DONOR_SOURCES.leftUpperGuide,
] as const);

export const VPW_LAUNCH_TRAVEL_ROUTE_ENDPOINT_BRIDGE_3D_PATH = Object.freeze([
  VPW_LAUNCH_TRAVEL_ROUTE_OVERHEAD_EXIT_ANCHOR_3D,
  VPW_LAUNCH_TRAVEL_ROUTE_DESCENT_ENTRY_ANCHOR_3D,
] as const);
