/**
 * Flipper actuation helpers for Flunk-Out Frenzy physics.
 *
 * These utilities keep kinematic flipper motion and one-shot contact impulse
 * resolution separate from `PhysicsWorld` orchestration.
 */

import RAPIER3D from "@dimforge/rapier3d-compat";

import type { TableFlipperDefinition } from "../table/tableDefinitionTypes";
import { resolveFlipperContactImpulse } from "./flipperContactModel";

interface FlipperContactBallSnapshot {
  x: number;
  y: number;
  radius: number;
}

export function driveFlipperKinematic(
  body: RAPIER3D.RigidBody,
  flipper: TableFlipperDefinition,
  pressed: boolean,
  dtSeconds: number,
  currentAngleRad: number,
): number {
  const targetAngleRad = degreesToRadians(
    pressed ? flipper.activeAngleDeg : flipper.restAngleDeg,
  );
  const maxDelta = dtSeconds * 18;
  const nextAngleRad = approachAngle(currentAngleRad, targetAngleRad, maxDelta);
  body.setNextKinematicRotation(quaternionFromYaw(nextAngleRad));
  return nextAngleRad;
}

export function applyFlipperContactImpulse(args: {
  ballBody: RAPIER3D.RigidBody;
  ball: FlipperContactBallSnapshot;
  flipper: TableFlipperDefinition;
  angleRad: number;
}): void {
  const { ballBody, ball, flipper, angleRad } = args;
  const contactImpulse = resolveFlipperContactImpulse({
    ball,
    flipper,
    angleRad,
  });
  if (!contactImpulse) {
    return;
  }

  ballBody.applyImpulse(
    {
      x: contactImpulse.impulse.x,
      y: contactImpulse.impulse.y,
      z: 0,
    },
    true,
  );
}

export function degreesToRadians(deg: number): number {
  return (deg * Math.PI) / 180;
}

export function radiansToDegrees(rad: number): number {
  return (rad * 180) / Math.PI;
}

function approachAngle(current: number, target: number, maxDelta: number): number {
  if (Math.abs(target - current) <= maxDelta) {
    return target;
  }
  return current + Math.sign(target - current) * maxDelta;
}

function quaternionFromYaw(angleRad: number): RAPIER3D.Rotation {
  return {
    x: 0,
    y: 0,
    z: Math.sin(angleRad / 2),
    w: Math.cos(angleRad / 2),
  };
}
