/**
 * Shared authored-table constants for the Flunk-Out Frenzy prototype.
 *
 * These constants define the stable board, gravity, and flipper contracts used
 * by the assembled prototype table spec.
 */

import type { PinballTableSpec } from "../pinballTablePlanTypes";
import { makeFlipperFromPivot, v } from "../pinballTableMath";
import {
  PROTOTYPE_ALPHA_VPW_DONOR_BOARD,
  VPW_FLIPPER_GEOMETRY,
  VPW_FLIPPER_PIVOTS,
} from "../prototypeAlphaVpwDonorMap";

export const ALPHA_BALL_RADIUS = 12;

const CONTACT_MODEL = {
  minImpulse: 280,
  maxImpulse: 840,
  maxContactDistance: 22,
  minContactRatio: 0.22,
  maxContactRatio: 0.98,
  liftBias: 0.9,
  lateralBias: 0.22,
} as const;

export const ALPHA_BOARD = {
  width: PROTOTYPE_ALPHA_VPW_DONOR_BOARD.width,
  height: PROTOTYPE_ALPHA_VPW_DONOR_BOARD.height,
  displayAspectRatio: 0.76,
} as const satisfies PinballTableSpec["board"];

export const ALPHA_GRAVITY = v(0, 981);

export const ALPHA_FLIPPERS = {
  left: makeFlipperFromPivot({
    id: "flipper-left",
    side: "left",
    pivot: VPW_FLIPPER_PIVOTS.left,
    length: VPW_FLIPPER_GEOMETRY.length,
    thickness: VPW_FLIPPER_GEOMETRY.thickness,
    restAngleDeg: -24,
    activeAngleDeg: -58,
    contactModel: CONTACT_MODEL,
  }),
  right: makeFlipperFromPivot({
    id: "flipper-right",
    side: "right",
    pivot: VPW_FLIPPER_PIVOTS.right,
    length: VPW_FLIPPER_GEOMETRY.length,
    thickness: VPW_FLIPPER_GEOMETRY.thickness,
    restAngleDeg: 24,
    activeAngleDeg: 58,
    contactModel: CONTACT_MODEL,
  }),
} as const satisfies PinballTableSpec["flippers"];
