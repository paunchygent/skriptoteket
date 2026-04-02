/**
 * Angle-aware flipper contact heuristics for Flunk-Out Frenzy.
 *
 * This helper computes bounded strike impulses from authored flipper geometry
 * and contact tuning so `PhysicsWorld` can improve flipper feel without
 * leaking Rapier concerns above the physics boundary.
 */

import type {
  TableFlipperDefinition,
  TablePoint,
} from "../table/tableDefinitionTypes";

export interface FlipperContactBallSnapshot {
  x: number;
  y: number;
  radius: number;
}

export interface FlipperContactImpulse {
  impulse: TablePoint;
  point: TablePoint;
}

export interface ResolveFlipperContactImpulseArgs {
  ball: FlipperContactBallSnapshot | null;
  flipper: TableFlipperDefinition;
  angleRad: number;
}

export function resolveFlipperContactImpulse(
  args: ResolveFlipperContactImpulseArgs,
): FlipperContactImpulse | null {
  const { ball, flipper, angleRad } = args;
  if (!ball) {
    return null;
  }

  const tip = resolveFlipperTip(flipper, angleRad);
  const closestPoint = closestPointOnSegment(ball, flipper.pivot, tip);
  const distanceToSurface = Math.hypot(ball.x - closestPoint.x, ball.y - closestPoint.y);
  const maxContactDistance = ball.radius + flipper.contactModel.maxContactDistance;

  if (distanceToSurface > maxContactDistance) {
    return null;
  }

  if (ball.y > closestPoint.y + ball.radius * 0.5) {
    return null;
  }

  const distanceFromPivot = Math.hypot(
    closestPoint.x - flipper.pivot.x,
    closestPoint.y - flipper.pivot.y,
  );
  const contactRatio = distanceFromPivot / flipper.length;
  if (
    contactRatio < flipper.contactModel.minContactRatio
    || contactRatio > flipper.contactModel.maxContactRatio
  ) {
    return null;
  }

  const ratioSpan = flipper.contactModel.maxContactRatio - flipper.contactModel.minContactRatio;
  const normalizedRatio = ratioSpan <= 0
    ? 1
    : clamp(
        (contactRatio - flipper.contactModel.minContactRatio) / ratioSpan,
        0,
        1,
      );
  const impulseMagnitude = lerp(
    flipper.contactModel.minImpulse,
    flipper.contactModel.maxImpulse,
    normalizedRatio,
  );

  const surfaceNormal = normalize({
    x: ball.x - closestPoint.x,
    y: ball.y - closestPoint.y,
  });
  const inwardBiasX = flipper.side === "left"
    ? flipper.contactModel.lateralBias
    : -flipper.contactModel.lateralBias;
  const launchDirection = normalize({
    x: surfaceNormal.x + inwardBiasX,
    y: surfaceNormal.y - flipper.contactModel.liftBias,
  });

  return {
    impulse: {
      x: launchDirection.x * impulseMagnitude,
      y: launchDirection.y * impulseMagnitude,
    },
    point: closestPoint,
  };
}

function resolveFlipperTip(
  flipper: TableFlipperDefinition,
  angleRad: number,
): TablePoint {
  const signedLength = flipper.side === "left" ? flipper.length : -flipper.length;
  return {
    x: flipper.pivot.x + Math.cos(angleRad) * signedLength,
    y: flipper.pivot.y + Math.sin(angleRad) * signedLength,
  };
}

function closestPointOnSegment(
  point: TablePoint,
  start: TablePoint,
  end: TablePoint,
): TablePoint {
  const segment = {
    x: end.x - start.x,
    y: end.y - start.y,
  };
  const segmentLengthSq = segment.x ** 2 + segment.y ** 2;

  if (segmentLengthSq === 0) {
    return { ...start };
  }

  const pointOffset = {
    x: point.x - start.x,
    y: point.y - start.y,
  };
  const projection = clamp(
    (pointOffset.x * segment.x + pointOffset.y * segment.y) / segmentLengthSq,
    0,
    1,
  );

  return {
    x: start.x + segment.x * projection,
    y: start.y + segment.y * projection,
  };
}

function normalize(point: TablePoint): TablePoint {
  const magnitude = Math.hypot(point.x, point.y);
  if (magnitude === 0) {
    return {
      x: 0,
      y: -1,
    };
  }

  return {
    x: point.x / magnitude,
    y: point.y / magnitude,
  };
}

function lerp(start: number, end: number, ratio: number): number {
  return start + (end - start) * ratio;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}
