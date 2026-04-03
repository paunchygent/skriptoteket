/**
 * Explicit launcher-lane state machine for Flunk-Out Frenzy.
 *
 * This helper keeps launcher feed, charge, release, and relaunch timing
 * private to the physics layer while emitting a small semantic event seam for
 * downstream rules and presentation work.
 */

import type { MachineEvent } from "./physicsTypes";
import type {
  TableLauncherDefinition,
  TablePoint,
  TableRegionShapeDefinition,
  TableTriggerShapeDefinition,
} from "../table/tableDefinitionTypes";

export type PlungerLanePhase =
  | "idle"
  | "feeding"
  | "fed"
  | "charging"
  | "released"
  | "relaunch";

export interface PlungerLaneBallSnapshot {
  position: TablePoint;
  velocity: TablePoint;
}

export interface PlungerLaneState {
  phase: PlungerLanePhase;
  chargeMs: number;
  relaunchCooldownMs: number;
  chargedEventEmitted: boolean;
}

export interface PlungerLaneStepResult {
  nextState: PlungerLaneState;
  machineEvents: MachineEvent[];
  chargeRatio: number | null;
  releaseChargeRatio: number | null;
}

export interface StepPlungerLaneStateArgs {
  state: PlungerLaneState;
  ball: PlungerLaneBallSnapshot | null;
  launchPressed: boolean;
  launcher: TableLauncherDefinition;
  dtMs: number;
}

export function createInitialPlungerLaneState(): PlungerLaneState {
  return {
    phase: "idle",
    chargeMs: 0,
    relaunchCooldownMs: 0,
    chargedEventEmitted: false,
  };
}

export function stepPlungerLaneState(args: StepPlungerLaneStateArgs): PlungerLaneStepResult {
  const { state, ball, launchPressed, launcher, dtMs } = args;
  const machineEvents: MachineEvent[] = [];

  if (!ball || !isPointInLauncherLaneRegion(ball.position, launcher)) {
    return {
      nextState: createInitialPlungerLaneState(),
      machineEvents,
      chargeRatio: null,
      releaseChargeRatio: null,
    };
  }

  const ballSettled = isBallSettled(ball, launcher);
  const ballReadyForCharge = ballSettled
    || state.phase === "fed"
    || state.phase === "charging";

  if (state.phase === "released" || state.phase === "relaunch") {
    const relaunchCooldownMs = Math.max(state.relaunchCooldownMs - dtMs, 0);
    const cooledState: PlungerLaneState = {
      phase: relaunchCooldownMs > 0 ? "relaunch" : state.phase,
      chargeMs: 0,
      relaunchCooldownMs,
      chargedEventEmitted: false,
    };

    if (relaunchCooldownMs === 0 && ballSettled) {
      return enterFedState(cooledState, launcher.tag, launchPressed, launcher, dtMs);
    }

    return {
      nextState: {
        ...cooledState,
        phase: relaunchCooldownMs > 0 ? "relaunch" : "feeding",
      },
      machineEvents,
      chargeRatio: null,
      releaseChargeRatio: null,
    };
  }

  if (!ballReadyForCharge) {
    return {
      nextState: {
        phase: "feeding",
        chargeMs: 0,
        relaunchCooldownMs: 0,
        chargedEventEmitted: false,
      },
      machineEvents,
      chargeRatio: null,
      releaseChargeRatio: null,
    };
  }

  if (state.phase === "charging" && !launchPressed && state.chargeMs > 0) {
    return {
      nextState: {
        phase: "released",
        chargeMs: 0,
        relaunchCooldownMs: launcher.relaunchCooldownMs,
        chargedEventEmitted: false,
      },
      machineEvents: [{ type: "launcher-released", tag: launcher.tag }],
      chargeRatio: null,
      releaseChargeRatio: resolveReleaseChargeRatio(launcher, state.chargeMs),
    };
  }

  return enterFedState(state, launcher.tag, launchPressed, launcher, dtMs);
}

function enterFedState(
  state: PlungerLaneState,
  tag: string,
  launchPressed: boolean,
  launcher: TableLauncherDefinition,
  dtMs: number,
): PlungerLaneStepResult {
  const machineEvents: MachineEvent[] = [];
  const enteringReadyState = state.phase !== "fed" && state.phase !== "charging";

  if (enteringReadyState) {
    machineEvents.push({ type: "launcher-fed", tag });
  }

  if (!launchPressed) {
    return {
      nextState: {
        phase: "fed",
        chargeMs: 0,
        relaunchCooldownMs: 0,
        chargedEventEmitted: false,
      },
      machineEvents,
      chargeRatio: null,
      releaseChargeRatio: null,
    };
  }

  const nextChargeMs = Math.min(state.chargeMs + dtMs, launcher.chargeMsMax);
  const crossedChargeThreshold = !state.chargedEventEmitted && nextChargeMs >= launcher.chargeMsMin;
  if (crossedChargeThreshold) {
    machineEvents.push({ type: "launcher-charged", tag });
  }

  return {
    nextState: {
      phase: "charging",
      chargeMs: nextChargeMs,
      relaunchCooldownMs: 0,
      chargedEventEmitted: state.chargedEventEmitted || crossedChargeThreshold,
    },
    machineEvents,
    chargeRatio: resolveReleaseChargeRatio(launcher, nextChargeMs),
    releaseChargeRatio: null,
  };
}

export function isPointInLauncherLaneRegion(
  position: TablePoint,
  launcher: TableLauncherDefinition,
): boolean {
  return launcher.laneRegions.some((region) => isPointInRegionShape(position, region));
}

function isBallSettled(
  ball: PlungerLaneBallSnapshot,
  launcher: TableLauncherDefinition,
): boolean {
  return Math.hypot(ball.velocity.x, ball.velocity.y) <= launcher.feedSettledSpeedMax;
}

function resolveReleaseChargeRatio(
  launcher: TableLauncherDefinition,
  chargeMs: number,
): number {
  return launcher.chargeMsMax === 0
    ? 1
    : clamp(chargeMs / launcher.chargeMsMax, 0, 1);
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

function isPointInRegionShape(point: TablePoint, shape: TableRegionShapeDefinition): boolean {
  switch (shape.kind) {
    case "rect":
      return isPointInRotatedRect(point, shape);
    case "circle":
      return Math.hypot(point.x - shape.center.x, point.y - shape.center.y) <= shape.radius;
    case "polygon":
      return isPointInPolygon(point, shape.points);
    case "capsule":
      return distanceToSegment(point, capsuleSegmentStart(shape), capsuleSegmentEnd(shape)) <= shape.radius;
    case "donor-corridor":
      return isPointInCorridor(point, shape.leftBoundary, shape.rightBoundary);
  }
}

export function isPointInTriggerShape(point: TablePoint, shape: TableTriggerShapeDefinition): boolean {
  switch (shape.kind) {
    case "rect":
      return isPointInRotatedRect(point, shape);
    case "circle":
      return Math.hypot(point.x - shape.center.x, point.y - shape.center.y) <= shape.radius;
    case "polygon":
      return isPointInPolygon(point, shape.points);
    case "capsule":
      return distanceToSegment(point, capsuleSegmentStart(shape), capsuleSegmentEnd(shape)) <= shape.radius;
    case "donor-wire-rollover":
      return distanceToSegment(
        point,
        donorWireRolloverStart(shape),
        donorWireRolloverEnd(shape),
      ) <= shape.wireRadius;
  }
}

function isPointInRotatedRect(
  point: TablePoint,
  shape: Extract<TableRegionShapeDefinition, { kind: "rect" }>,
): boolean {
  const angleRad = ((shape.angleDeg ?? 0) * Math.PI) / 180;
  const cos = Math.cos(-angleRad);
  const sin = Math.sin(-angleRad);
  const localX = (point.x - shape.center.x) * cos - (point.y - shape.center.y) * sin;
  const localY = (point.x - shape.center.x) * sin + (point.y - shape.center.y) * cos;

  return Math.abs(localX) <= shape.width / 2 && Math.abs(localY) <= shape.height / 2;
}

function isPointInPolygon(point: TablePoint, vertices: readonly TablePoint[]): boolean {
  let inside = false;

  for (let index = 0, previous = vertices.length - 1; index < vertices.length; previous = index++) {
    const current = vertices[index];
    const prior = vertices[previous];
    if (isPointOnSegment(point, prior, current)) {
      return true;
    }
    const intersects = ((current.y > point.y) !== (prior.y > point.y))
      && point.x
        < ((prior.x - current.x) * (point.y - current.y)) / ((prior.y - current.y) || 1e-9)
          + current.x;
    if (intersects) {
      inside = !inside;
    }
  }

  return inside;
}

function capsuleSegmentStart(
  shape: Extract<TableRegionShapeDefinition, { kind: "capsule" }>,
): TablePoint {
  const halfLength = shape.length / 2;
  const angleRad = ((shape.angleDeg ?? 0) * Math.PI) / 180;
  return {
    x: shape.center.x - Math.cos(angleRad) * halfLength,
    y: shape.center.y - Math.sin(angleRad) * halfLength,
  };
}

function capsuleSegmentEnd(
  shape: Extract<TableRegionShapeDefinition, { kind: "capsule" }>,
): TablePoint {
  const halfLength = shape.length / 2;
  const angleRad = ((shape.angleDeg ?? 0) * Math.PI) / 180;
  return {
    x: shape.center.x + Math.cos(angleRad) * halfLength,
    y: shape.center.y + Math.sin(angleRad) * halfLength,
  };
}

function donorWireRolloverStart(
  shape: Extract<TableTriggerShapeDefinition, { kind: "donor-wire-rollover" }>,
): TablePoint {
  const halfLength = shape.wireLength / 2;
  const angleRad = ((shape.angleDeg ?? 0) * Math.PI) / 180;
  return {
    x: shape.center.x - Math.cos(angleRad) * halfLength,
    y: shape.center.y - Math.sin(angleRad) * halfLength,
  };
}

function donorWireRolloverEnd(
  shape: Extract<TableTriggerShapeDefinition, { kind: "donor-wire-rollover" }>,
): TablePoint {
  const halfLength = shape.wireLength / 2;
  const angleRad = ((shape.angleDeg ?? 0) * Math.PI) / 180;
  return {
    x: shape.center.x + Math.cos(angleRad) * halfLength,
    y: shape.center.y + Math.sin(angleRad) * halfLength,
  };
}

function distanceToSegment(point: TablePoint, start: TablePoint, end: TablePoint): number {
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  const denominator = dx * dx + dy * dy;
  const t = denominator === 0
    ? 0
    : clamp(((point.x - start.x) * dx + (point.y - start.y) * dy) / denominator, 0, 1);
  const projection = {
    x: start.x + dx * t,
    y: start.y + dy * t,
  };
  return Math.hypot(point.x - projection.x, point.y - projection.y);
}

function isPointOnSegment(point: TablePoint, start: TablePoint, end: TablePoint): boolean {
  const cross = (point.y - start.y) * (end.x - start.x) - (point.x - start.x) * (end.y - start.y);
  if (Math.abs(cross) > 1e-6) {
    return false;
  }

  const dot = (point.x - start.x) * (end.x - start.x) + (point.y - start.y) * (end.y - start.y);
  if (dot < 0) {
    return false;
  }

  const squaredLength = (end.x - start.x) ** 2 + (end.y - start.y) ** 2;
  return dot <= squaredLength;
}

function isPointInCorridor(
  point: TablePoint,
  leftBoundary: readonly TablePoint[],
  rightBoundary: readonly TablePoint[],
): boolean {
  const leftX = xOnBoundaryAtY(leftBoundary, point.y);
  const rightX = xOnBoundaryAtY(rightBoundary, point.y);
  if (leftX === null || rightX === null) {
    return false;
  }

  return point.x >= Math.min(leftX, rightX) && point.x <= Math.max(leftX, rightX);
}

function xOnBoundaryAtY(path: readonly TablePoint[], y: number): number | null {
  for (let index = 0; index < path.length - 1; index += 1) {
    const start = path[index];
    const end = path[index + 1];
    const minY = Math.min(start.y, end.y);
    const maxY = Math.max(start.y, end.y);
    if (y < minY || y > maxY) {
      continue;
    }
    if (Math.abs(end.y - start.y) < 1e-6) {
      return Math.max(start.x, end.x);
    }
    const ratio = (y - start.y) / (end.y - start.y);
    return start.x + (end.x - start.x) * ratio;
  }

  return null;
}
