import {
  applyFlipperContactImpulse,
  driveFlipperKinematic,
} from "../flipperActuation";
import type { PhysicsWorldContext } from "./PhysicsWorldContext";

export function updateFlippers(ctx: PhysicsWorldContext, dtSeconds: number): void {
  ctx.leftFlipperAngleRad = driveFlipperKinematic(
    ctx.leftFlipper,
    ctx.table.flippers.left,
    ctx.leftPressed,
    dtSeconds,
    ctx.leftFlipperAngleRad,
  );
  ctx.rightFlipperAngleRad = driveFlipperKinematic(
    ctx.rightFlipper,
    ctx.table.flippers.right,
    ctx.rightPressed,
    dtSeconds,
    ctx.rightFlipperAngleRad,
  );

  if (ctx.leftPressed && !ctx.wasLeftPressed) {
    applyFlipperContact(ctx, ctx.table.flippers.left, ctx.leftFlipperAngleRad);
  }
  if (ctx.rightPressed && !ctx.wasRightPressed) {
    applyFlipperContact(ctx, ctx.table.flippers.right, ctx.rightFlipperAngleRad);
  }
}

function applyFlipperContact(
  ctx: PhysicsWorldContext,
  flipper: PhysicsWorldContext["table"]["flippers"]["left"],
  angleRad: number,
): void {
  if (!ctx.ballBody) {
    return;
  }

  applyFlipperContactImpulse({
    ballBody: ctx.ballBody,
    ball: {
      x: ctx.ballBody.translation().x,
      y: ctx.ballBody.translation().y,
      radius: ctx.table.ball.radius,
    },
    flipper,
    angleRad,
  });
}
