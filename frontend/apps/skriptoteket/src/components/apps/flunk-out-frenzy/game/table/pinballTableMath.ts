/**
 * Shared math helpers for pinball table authoring and compilation.
 *
 * These helpers keep authored table specs readable while letting the compile
 * step derive stable segment centers, rotations, and flipper offsets.
 */

import type { TableFlipperDefinition, TablePoint } from "./tableDefinitionTypes";

export function v(x: number, y: number): TablePoint {
  return { x, y };
}

export function add(a: TablePoint, b: TablePoint): TablePoint {
  return v(a.x + b.x, a.y + b.y);
}

export function mul(a: TablePoint, scalar: number): TablePoint {
  return v(a.x * scalar, a.y * scalar);
}

export function midpoint(a: TablePoint, b: TablePoint): TablePoint {
  return v((a.x + b.x) * 0.5, (a.y + b.y) * 0.5);
}

export function sub(a: TablePoint, b: TablePoint): TablePoint {
  return v(a.x - b.x, a.y - b.y);
}

export function magnitude(a: TablePoint): number {
  return Math.hypot(a.x, a.y);
}

export function normalize(a: TablePoint): TablePoint {
  const length = magnitude(a);
  if (length === 0) {
    throw new Error("Cannot normalize a zero-length vector.");
  }

  return v(a.x / length, a.y / length);
}

export function segmentAngle(a: TablePoint, b: TablePoint): number {
  return Math.atan2(b.y - a.y, b.x - a.x);
}

export function degreesToRadians(deg: number): number {
  return (deg * Math.PI) / 180;
}

export function radiansToDegrees(rad: number): number {
  return (rad * 180) / Math.PI;
}

export function mirrorX(boardWidth: number, point: TablePoint): TablePoint {
  return v(boardWidth - point.x, point.y);
}

export function mirrorPath(boardWidth: number, path: readonly TablePoint[]): readonly TablePoint[] {
  return path.map((point) => mirrorX(boardWidth, point));
}

export function sampleArcPath(args: {
  center: TablePoint;
  radius: number;
  startDeg: number;
  endDeg: number;
  segments: number;
}): readonly TablePoint[] {
  const { center, radius, startDeg, endDeg, segments } = args;
  const points: TablePoint[] = [];
  const steps = Math.max(1, segments);

  for (let index = 0; index <= steps; index += 1) {
    const ratio = index / steps;
    const angleRad = degreesToRadians(startDeg + (endDeg - startDeg) * ratio);
    points.push(
      v(
        center.x + Math.cos(angleRad) * radius,
        center.y + Math.sin(angleRad) * radius,
      ),
    );
  }

  return points;
}

export function makeFlipperFromPivot(args: {
  id: string;
  side: "left" | "right";
  pivot: TablePoint;
  length: number;
  thickness: number;
  restAngleDeg: number;
  activeAngleDeg: number;
  contactModel: TableFlipperDefinition["contactModel"];
}): TableFlipperDefinition {
  return {
    side: args.side,
    pivot: args.pivot,
    length: args.length,
    thickness: args.thickness,
    restAngleDeg: args.restAngleDeg,
    activeAngleDeg: args.activeAngleDeg,
    contactModel: args.contactModel,
  };
}
