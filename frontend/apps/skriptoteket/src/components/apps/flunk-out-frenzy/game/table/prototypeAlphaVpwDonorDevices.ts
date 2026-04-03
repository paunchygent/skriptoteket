/**
 * VPW donor-derived device anchors for the prototype-alpha table spec.
 *
 * This module keeps the remaining visible device placements on donor data
 * instead of local guesses. The board carriers already come from donor wall
 * chains; these exports finish the graft for rollover inserts, target banks,
 * scoop markers, donor-backed semantic trigger specs, and the drain footprint.
 */

import type {
  TableLauncherPlunger3DDefinition,
  TableTriggerPhaseDefinition,
  TableTriggerShapeDefinition,
} from "./tableDefinitionTypes";
import { v } from "./pinballTableMath";
import {
  scaleDonorLength,
  scaleDonorPoint,
} from "./prototypeAlphaVpwDonorMap";

type DonorPointTuple = readonly [number, number];

interface DonorRectSpec {
  center: Readonly<{ x: number; y: number }>;
  width: number;
  height: number;
}

interface DonorStandupSpec extends DonorRectSpec {
  angleDeg: number;
}

interface DonorPopupSpec {
  center: Readonly<{ x: number; y: number }>;
  radius: number;
  sensorRadius: number;
}

export interface DonorSemanticTriggerSpec {
  shape: TableTriggerShapeDefinition;
  triggerPhase: TableTriggerPhaseDefinition;
  donorSourceIds: readonly string[];
  authoredDecision?: string;
}

function donorRectFromPoints(points: readonly DonorPointTuple[]): DonorRectSpec {
  const xs = points.map(([x]) => x);
  const ys = points.map(([, y]) => y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);

  return Object.freeze({
    center: scaleDonorPoint((minX + maxX) / 2, (minY + maxY) / 2),
    width: scaleDonorLength(maxX - minX),
    height: scaleDonorLength(maxY - minY),
  });
}

function donorStandupFromPoints(points: readonly DonorPointTuple[]): DonorStandupSpec {
  const scaledPoints = points.map(([x, y]) => scaleDonorPoint(x, y));
  const edge01 = Math.hypot(
    scaledPoints[1].x - scaledPoints[0].x,
    scaledPoints[1].y - scaledPoints[0].y,
  );
  const edge12 = Math.hypot(
    scaledPoints[2].x - scaledPoints[1].x,
    scaledPoints[2].y - scaledPoints[1].y,
  );
  const longEdge = edge12 > edge01
    ? [scaledPoints[1], scaledPoints[2]]
    : [scaledPoints[0], scaledPoints[1]];

  return Object.freeze({
    center: v(
      average(scaledPoints.map((point) => point.x)),
      average(scaledPoints.map((point) => point.y)),
    ),
    width: roundTenth(Math.min(edge01, edge12)),
    height: roundTenth(Math.max(edge01, edge12)),
    angleDeg: roundTenth(
      (Math.atan2(longEdge[1].y - longEdge[0].y, longEdge[1].x - longEdge[0].x) * 180)
        / Math.PI,
    ),
  });
}

function donorPopupFromCenterAndBounds(
  center: DonorPointTuple,
  radius: number,
  points: readonly DonorPointTuple[],
): DonorPopupSpec {
  const bounds = donorRectFromPoints(points);
  return Object.freeze({
    center: scaleDonorPoint(center[0], center[1]),
    radius: scaleDonorLength(radius),
    sensorRadius: roundTenth(Math.max(bounds.width, bounds.height) / 2),
  });
}

function average(values: readonly number[]): number {
  return roundTenth(values.reduce((sum, value) => sum + value, 0) / values.length);
}

function roundTenth(value: number): number {
  return Math.round(value * 10) / 10;
}

function donorRectTriggerFromPoints(
  points: readonly DonorPointTuple[],
  donorSourceId: string,
  triggerPhase: TableTriggerPhaseDefinition,
  authoredDecision?: string,
): DonorSemanticTriggerSpec {
  const rect = donorRectFromPoints(points);
  return Object.freeze({
    shape: {
      kind: "rect" as const,
      center: rect.center,
      width: rect.width,
      height: rect.height,
      angleDeg: 0,
    },
    triggerPhase,
    donorSourceIds: [donorSourceId],
    authoredDecision,
  });
}

function donorWireRolloverTriggerFromPoints(
  points: readonly DonorPointTuple[],
  donorSourceId: string,
  triggerPhase: TableTriggerPhaseDefinition,
  authoredDecision?: string,
): DonorSemanticTriggerSpec {
  const bounds = donorRectFromPoints(points);
  return Object.freeze({
    shape: {
      kind: "donor-wire-rollover" as const,
      center: bounds.center,
      wireLength: roundTenth(bounds.height),
      wireRadius: roundTenth(bounds.width / 2),
      angleDeg: 0,
      donorSourceId,
    },
    triggerPhase,
    donorSourceIds: [donorSourceId],
    authoredDecision,
  });
}

function donorGateTriggerSpec(args: {
  center: Readonly<{ x: number; y: number }>;
  length: number;
  height: number;
  rotationDeg: number;
  donorSourceId: string;
  triggerPhase: TableTriggerPhaseDefinition;
  authoredDecision?: string;
}): DonorSemanticTriggerSpec {
  return Object.freeze({
    shape: {
      kind: "capsule" as const,
      center: args.center,
      length: args.length,
      radius: roundTenth(args.height / 2),
      angleDeg: args.rotationDeg,
    },
    triggerPhase: args.triggerPhase,
    donorSourceIds: [args.donorSourceId],
    authoredDecision: args.authoredDecision,
  });
}

const SW60_POINTS = [[192.67377, 81.37949], [154.66931, 107.20364], [120.84193, 137.63904], [162.67659, 182.24413], [222.97867, 131.91707]] as const;
const SW21_POINTS = [[468.35385, 172.13829], [457.81192, 224.39047], [508.67752, 232.01935], [516.791, 180.70618]] as const;
const SW22_POINTS = [[559.18884, 186.93991], [551.4995, 239.1523], [601.74646, 247.83693], [609.3412, 196.31644]] as const;
const SW23_POINTS = [[652.8716, 202.26335], [645.0925, 255.23965], [692.36304, 273.6964], [699.73553, 221.79839]] as const;
const SW58_POINTS = [[969.66254, 128.40265], [922.1621, 171.66994], [961.96014, 228.42395], [1016.81696, 200.10724], [998.1376, 163.82742]] as const;
const SW38_POINTS = [[554.81696, 848.3785], [554.81696, 908.37866], [614.8169, 908.37866], [614.8169, 848.3785]] as const;
const SW33_POINTS = [[147.96608, 1236.174], [153.98216, 1238.4755], [168.93086, 1194.94], [162.79356, 1192.7284]] as const;
const SW34_POINTS = [[165.24411, 1185.797], [171.26006, 1188.0984], [186.20888, 1144.563], [180.07144, 1142.3514]] as const;
const SW59_POINTS = [[183.48795, 1133.957], [189.50401, 1136.2585], [204.45271, 1092.723], [198.3154, 1090.5115]] as const;
const SWPLUNGER_POINTS = [[1002.51404, 1851.5724], [1002.51404, 1929.67], [1056.0, 1929.67], [1056.0, 1851.5724]] as const;
const SW16_POINTS = [[1009.75433, 1873.1346], [1009.75433, 1920.2291], [1055.0, 1920.2291], [1055.0, 1873.1346]] as const;
const PLUNGER_ROSE_WIDTH = 25;
const PLUNGER_ROSE_HEIGHT = 20;
const PLUNGER_ROSE_STROKE = 80;
const PLUNGER_ROSE_SPEED_PULL = 0.2;
const PLUNGER_ROSE_SPEED_FIRE = 450;
const PLUNGER_ROSE_PARK_POSITION = 0.16666667;
const PLUNGER_ROSE_MOMENTUM_TRANSFER = 1.0;

const LEFT_DRAIN_MOUTH = scaleDonorPoint(403.2655, 1872.2633);
const RIGHT_DRAIN_MOUTH = scaleDonorPoint(724.1052, 1872.3271);
const APRON_TOP_CENTER_Y = scaleDonorPoint(635.8008, 2063.048).y;

export const VPW_TOP_ROLLOVER_SPECS = Object.freeze({
  leftOrbit: donorRectFromPoints(SW60_POINTS),
  topLeft: donorRectFromPoints(SW21_POINTS),
  topMiddle: donorRectFromPoints(SW22_POINTS),
  topRight: donorRectFromPoints(SW23_POINTS),
  rightOrbit: donorRectFromPoints(SW58_POINTS),
});

export const VPW_LEFT_DROP_BANK_SPECS = Object.freeze({
  left: donorStandupFromPoints(SW33_POINTS),
  center: donorStandupFromPoints(SW34_POINTS),
  right: donorStandupFromPoints(SW59_POINTS),
});

export const VPW_RIGHT_RETURN_TRIGGER_SPEC = donorGateTriggerSpec({
  center: scaleDonorPoint(722.30853, 818.7679),
  length: scaleDonorLength(100),
  height: scaleDonorLength(50),
  rotationDeg: 14,
  donorSourceId:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Gate.GateSW49.json",
  triggerPhase: "enter",
});

export const VPW_SHOOTER_PLUNGER_TRIGGER_SPEC = donorRectTriggerFromPoints(
  SWPLUNGER_POINTS,
  ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Trigger.swplunger.json",
  "enter",
  "Keep swplunger as the donor plunger-band semantic anchor for launcher feed/rest semantics instead of collapsing launch-lane behavior onto the sw16 rollover alone.",
);

export const VPW_LAUNCH_LANE_EXIT_TRIGGER_SPEC = donorWireRolloverTriggerFromPoints(
  SW16_POINTS,
  ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Trigger.sw16.json",
  "exit",
  "Treat the donor sw16 wire_d rollover as an exit-phase launch-lane trigger so a served resting ball does not count as having passed the gate before it actually leaves the rollover footprint.",
);

const SHOOTER_PLUNGER_RECT = donorRectFromPoints(SWPLUNGER_POINTS);

export const VPW_PLUNGER_ROSE_3D_SPEC: TableLauncherPlunger3DDefinition = Object.freeze({
  tag: "launcher/plunger-rose",
  donorSourceId:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Plunger.PlungerRose.json",
  // The extracted PlungerRose object exposes stroke/speed hardware, while the
  // swplunger trigger band is the trustworthy board-space launcher anchor used
  // by the donor table's impulse-plunger path.
  center: {
    x: SHOOTER_PLUNGER_RECT.center.x,
    y: roundTenth(
      SHOOTER_PLUNGER_RECT.center.y
        + SHOOTER_PLUNGER_RECT.height / 2
        - scaleDonorLength(PLUNGER_ROSE_HEIGHT) / 2,
    ),
    z: roundTenth(scaleDonorLength(PLUNGER_ROSE_HEIGHT) / 2),
  },
  width: scaleDonorLength(PLUNGER_ROSE_WIDTH),
  depth: scaleDonorLength(PLUNGER_ROSE_HEIGHT),
  height: scaleDonorLength(PLUNGER_ROSE_HEIGHT),
  stroke: scaleDonorLength(PLUNGER_ROSE_STROKE),
  speedPull: PLUNGER_ROSE_SPEED_PULL,
  speedFire: scaleDonorLength(PLUNGER_ROSE_SPEED_FIRE),
  parkPosition: PLUNGER_ROSE_PARK_POSITION,
  momentumTransfer: PLUNGER_ROSE_MOMENTUM_TRANSFER,
});

export const VPW_POPUP_TARGET_SPECS = Object.freeze({
  middleScoop: donorPopupFromCenterAndBounds([587.0731, 881.10693], 25, SW38_POINTS),
});

export const VPW_DRAIN_SPEC = Object.freeze({
  center: v(
    roundTenth((LEFT_DRAIN_MOUTH.x + RIGHT_DRAIN_MOUTH.x) / 2),
    APRON_TOP_CENTER_Y,
  ),
  width: roundTenth(RIGHT_DRAIN_MOUTH.x - LEFT_DRAIN_MOUTH.x),
  height: scaleDonorLength(44),
});
