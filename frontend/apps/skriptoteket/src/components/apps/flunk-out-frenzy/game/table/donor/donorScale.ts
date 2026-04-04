/**
 * Shared VPW donor scaling and provenance helpers for Flunk-Out Frenzy.
 *
 * These utilities convert donor-space coordinates into local table-space values
 * and centralize the extracted donor source ledger used across the rebuilt
 * prototype table geometry.
 */

import type { TablePoint, TablePoint3D } from "../tableDefinitionTypes";
import { v } from "../pinballTableMath";

const DONOR_BOARD_WIDTH = 1081;
const DONOR_BOARD_HEIGHT = 2162;

export const PROTOTYPE_ALPHA_VPW_DONOR_SCALE = 600 / DONOR_BOARD_WIDTH;
export const PROTOTYPE_ALPHA_VPW_DONOR_BOARD = Object.freeze({
  width: 600,
  height: Math.round(DONOR_BOARD_HEIGHT * PROTOTYPE_ALPHA_VPW_DONOR_SCALE),
});

export const PROTOTYPE_ALPHA_VPW_DONOR_SOURCES = Object.freeze({
  outerBoundary:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.Wall263.json",
  leftUpperGuide:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.Wall268.json",
  rightUpperGuide:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.Wall264.json",
  leftOutlane:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.Wall76.json",
  leftInlane:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.Wall016.json",
  rightInlane:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.Wall015.json",
  rightOutlane:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.Wall234.json",
  leftDrainGuide:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.Wall013.json",
  rightDrainGuide:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.Wall021.json",
  shooterOuterWall:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.Wall95.json",
  shooterLaneDivider:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.Wall34.json",
  rightReceiveMouthOuter:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.Wall018.json",
  rightReceiveMouthInner:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.Wall019.json",
  shooterHandoffUpper:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.Wall010.json",
  shooterHandoffLower:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.Wall011.json",
  rightReturnThroatShield:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.Wall024.json",
  rightUpperInnerMetal:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.Wall002.json",
  leftUpperInnerMetal:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.Wall017.json",
  shooterWireVertical:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Ramp.RampS3.json",
  shooterWireMouthConnector:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Ramp.RampS001.json",
  shooterWireTopRight:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Ramp.RampS002.json",
  shooterWireTopArch:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Ramp.RampS4.json",
  leftSling:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.LeftSlingShot.json",
  rightSling:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.RightSlingShot.json",
  leftFlipper:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Flipper.LeftFlipper.json",
  rightFlipper:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Flipper.RightFlipper.json",
  leftInlaneSwitch:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Trigger.sw53.json",
  leftOutlaneSwitch:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Trigger.sw54.json",
  rightInlaneSwitch:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Trigger.sw56.json",
  rightOutlaneSwitch:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Trigger.sw55.json",
  shooterTrigger:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Trigger.swplunger.json",
  plungerRollover:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Trigger.sw16.json",
  returnGate:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Gate.GateSW49.json",
  apron1:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.Apron1.json",
  apron2:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.Apron2.json",
});

function donorPoint(x: number, y: number): TablePoint {
  return v(
    roundTenth(x * PROTOTYPE_ALPHA_VPW_DONOR_SCALE),
    roundTenth(y * PROTOTYPE_ALPHA_VPW_DONOR_SCALE),
  );
}

export function scaleDonorPoint(x: number, y: number): TablePoint {
  return donorPoint(x, y);
}

export function scaleDonorLength(value: number): number {
  return roundTenth(value * PROTOTYPE_ALPHA_VPW_DONOR_SCALE);
}

export function donorPath(points: readonly (readonly [number, number])[]): readonly TablePoint[] {
  return points.map(([x, y]) => donorPoint(x, y));
}

export function closeDonorPath(points: readonly (readonly [number, number])[]): readonly TablePoint[] {
  const path = donorPath(points);
  if (path.length === 0) {
    return path;
  }

  return [...path, path[0]];
}

export function donorPath3DWithLinearHeightProfile(
  points: readonly (readonly [number, number])[],
  heightBottom: number,
  heightTop: number,
): readonly TablePoint3D[] {
  if (points.length === 0) {
    return [];
  }

  const scaled = points.map(([x, y]) => donorPoint(x, y));
  return interpolatePathZProfile(
    scaled,
    scaleDonorLength(heightBottom),
    scaleDonorLength(heightTop),
  );
}

export function path3DWithLinearHeightProfile(
  path: readonly TablePoint[],
  zStart: number,
  zEnd: number,
): readonly TablePoint3D[] {
  if (path.length === 0) {
    return [];
  }

  return interpolatePathZProfile(path, zStart, zEnd);
}

export function mergePath3DSegments(
  segments: readonly (readonly TablePoint3D[])[],
): readonly TablePoint3D[] {
  const merged: TablePoint3D[] = [];
  for (const segment of segments) {
    for (const point of segment) {
      const previous = merged[merged.length - 1];
      if (
        previous
        && Math.abs(previous.x - point.x) < 1e-6
        && Math.abs(previous.y - point.y) < 1e-6
        && Math.abs(previous.z - point.z) < 1e-6
      ) {
        continue;
      }
      merged.push(point);
    }
  }
  return merged;
}

export function planarPath(
  points: readonly (readonly [number, number, number])[],
): readonly (readonly [number, number])[] {
  return points.map(([x, y]) => [x, y] as const);
}

function interpolatePathZProfile(
  path: readonly TablePoint[],
  zStart: number,
  zEnd: number,
): readonly TablePoint3D[] {
  const cumulativeDistances: number[] = [0];
  for (let index = 1; index < path.length; index += 1) {
    const previous = path[index - 1];
    const current = path[index];
    const distance = Math.hypot(current.x - previous.x, current.y - previous.y);
    cumulativeDistances[index] = cumulativeDistances[index - 1] + distance;
  }

  const totalDistance = cumulativeDistances[cumulativeDistances.length - 1];
  return path.map((point, index) => {
    const t = totalDistance <= 0 ? 0 : cumulativeDistances[index] / totalDistance;
    return {
      x: point.x,
      y: point.y,
      z: roundTenth(zStart + (zEnd - zStart) * t),
    };
  });
}

function roundTenth(value: number): number {
  return Math.round(value * 10) / 10;
}
