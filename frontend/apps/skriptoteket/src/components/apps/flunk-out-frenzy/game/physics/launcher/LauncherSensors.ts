/**
 * Sensor and route-capture helpers for the Flunk-Out Frenzy launcher chain.
 *
 * LauncherChain3D delegates feed/exit probes and route-entry eligibility to
 * these pure-ish helpers so the main class can stay focused on step flow.
 */

import type {
  LauncherRouteCaptureRejectReason,
} from "../physicsTypes";
import { isPointInTriggerShape } from "../plungerLaneState";
import type {
  TableLauncherObservationSpine3DDefinition,
  TablePoint3D,
  TableTriggerShapeDefinition,
} from "../../table/tableDefinitionTypes";
import type { LauncherContext } from "./LauncherContext";

export type RouteCaptureRejectReason = Exclude<LauncherRouteCaptureRejectReason, null>;

export function canAttachReleaseTravelRoute(
  ctx: LauncherContext,
  route: TableLauncherObservationSpine3DDefinition,
  routeEntryToleranceMultiplier: number,
  minUpwardSpeed: number,
): { canAttach: boolean; reason: RouteCaptureRejectReason } {
  if (!ctx.ballBody) {
    return { canAttach: false, reason: "no_route" };
  }

  const entryMode = route.entryMode ?? "release";
  if (entryMode !== "release") {
    return { canAttach: false, reason: "no_route" };
  }
  if (ctx.pendingReleaseNeedsSw16Exit) {
    return { canAttach: false, reason: "no_route" };
  }

  const ballPosition = ctx.ballBody.translation();
  const routeStart = route.path[0];
  const routeEntryTolerance = ctx.ball.radius * routeEntryToleranceMultiplier;
  const xyDistance = Math.hypot(ballPosition.x - routeStart.x, ballPosition.y - routeStart.y);
  const zDistance = Math.abs(ballPosition.z - routeStart.z);
  if (xyDistance > routeEntryTolerance || zDistance > routeEntryTolerance) {
    if (xyDistance > routeEntryTolerance) {
      return { canAttach: false, reason: "distance_xy" };
    }
    return { canAttach: false, reason: "distance_z" };
  }

  if (ctx.ballBody.linvel().y > -minUpwardSpeed) {
    return { canAttach: false, reason: "vy_gate" };
  }
  return { canAttach: true, reason: "no_route" };
}

export function isInsideFeedSensor(ctx: LauncherContext): boolean {
  return isInsideLauncherSensor(ctx, "feed");
}

export function isInsideExitSensor(ctx: LauncherContext): boolean {
  return isInsideLauncherSensor(ctx, "exit");
}

export function resolveExitSensorShape(ctx: LauncherContext): TableTriggerShapeDefinition | null {
  const exitSensor = ctx.launcher.threeD.sensors.find((sensor) => sensor.semanticRole === "exit");
  return exitSensor?.shape ?? null;
}

export function currentBallPosition(ctx: LauncherContext): TablePoint3D | null {
  if (!ctx.ballBody) {
    return null;
  }
  const position = ctx.ballBody.translation();
  return { x: position.x, y: position.y, z: position.z };
}

export function didCrossExitSensorDuringStep(
  ctx: LauncherContext,
  previousPosition: TablePoint3D | null,
  currentPosition: TablePoint3D | null,
): boolean {
  if (!previousPosition || !currentPosition) {
    return false;
  }
  const exitSensorShape = resolveExitSensorShape(ctx);
  if (!exitSensorShape) {
    return false;
  }

  const travelDistance = Math.hypot(
    currentPosition.x - previousPosition.x,
    currentPosition.y - previousPosition.y,
  );
  if (travelDistance <= 1e-3) {
    return false;
  }

  const sampleCount = Math.max(2, Math.ceil(travelDistance / Math.max(ctx.ball.radius / 2, 1)));
  let sawInside = false;
  let sawOutside = false;
  for (let sampleIndex = 0; sampleIndex <= sampleCount; sampleIndex += 1) {
    const t = sampleIndex / sampleCount;
    const samplePoint = {
      x: previousPosition.x + (currentPosition.x - previousPosition.x) * t,
      y: previousPosition.y + (currentPosition.y - previousPosition.y) * t,
    };
    const isInside = isPointInTriggerShape(samplePoint, exitSensorShape);
    if (isInside) {
      sawInside = true;
    } else {
      sawOutside = true;
    }
    if (sawInside && sawOutside) {
      return true;
    }
  }

  return false;
}

export function isExitCrossingUpward(
  ctx: LauncherContext,
  previousPosition: TablePoint3D | null,
  currentPosition: TablePoint3D | null,
  minUpwardSpeed: number,
): boolean {
  if (!previousPosition || !currentPosition || !ctx.ballBody) {
    return false;
  }
  const vy = ctx.ballBody.linvel().y;
  return vy <= -minUpwardSpeed || currentPosition.y < previousPosition.y;
}

export function hasClearedReleasePlane(ctx: LauncherContext): boolean {
  if (!ctx.ballBody) {
    return false;
  }
  return ctx.ballBody.translation().y <= ctx.releasePlaneY;
}

function isInsideLauncherSensor(
  ctx: LauncherContext,
  semanticRole: "feed" | "exit",
): boolean {
  if (!ctx.ballBody) {
    return false;
  }
  const sensor = ctx.launcher.threeD.sensors.find((item) => item.semanticRole === semanticRole);
  if (!sensor) {
    return false;
  }
  const position = ctx.ballBody.translation();
  return isPointInTriggerShape({ x: position.x, y: position.y }, sensor.shape);
}
