import {
  isPointInLauncherLaneRegion,
  stepPlungerLaneState,
  type PlungerLaneBallSnapshot,
} from "../plungerLaneState";
import type { PhysicsWorldContext } from "./PhysicsWorldContext";
import type { MachineEvent } from "../physicsTypes";

export interface LauncherStateStep {
  machineEvents: MachineEvent[];
  chargeRatio: number | null;
  releaseChargeRatio: number | null;
}

export function updateLauncherState(
  ctx: PhysicsWorldContext,
  dtMs: number,
): LauncherStateStep {
  const result = stepPlungerLaneState({
    state: ctx.plungerLaneState,
    ball: currentPlungerBallSnapshot(ctx),
    launchPressed: ctx.launchPressed,
    launcher: ctx.table.launcher,
    dtMs,
  });
  ctx.plungerLaneState = result.nextState;
  if (!ctx.launcherChain?.hasBall()) {
    syncPlunger(ctx, dtMs, result.chargeRatio);
  }

  return {
    machineEvents: [...result.machineEvents],
    chargeRatio: result.chargeRatio,
    releaseChargeRatio: result.releaseChargeRatio,
  };
}

function currentPlungerBallSnapshot(
  ctx: PhysicsWorldContext,
): PlungerLaneBallSnapshot | null {
  const launcherBall = ctx.launcherChain?.currentSnapshot();
  if (launcherBall) {
    return {
      position: launcherBall.position,
      velocity: launcherBall.velocity,
    };
  }
  return null;
}

function syncPlunger(
  ctx: PhysicsWorldContext,
  dtMs: number,
  chargeRatio: number | null,
): void {
  const plunger = ctx.table.launcher.threeD.plunger;
  const dtSeconds = dtMs / 1000;
  const targetCenterY =
    chargeRatio !== null
      ? plunger.center.y + plunger.stroke * chargeRatio
      : plunger.center.y;
  const maxTravel =
    chargeRatio !== null
      ? plunger.speedPull * dtMs
      : plunger.speedFire * dtSeconds;
  const delta = targetCenterY - ctx.currentPlungerCenterY;
  const travel =
    Math.abs(delta) <= maxTravel ? delta : Math.sign(delta) * maxTravel;
  ctx.currentPlungerCenterY += travel;
}

export function tryTransferMainWorldBallToLauncherChain(
  ctx: PhysicsWorldContext,
): void {
  if (!ctx.ballBody || !ctx.launcherChain || ctx.launcherChain.hasBall()) {
    return;
  }

  const translation = ctx.ballBody.translation();
  const position = {
    x: translation.x,
    y: translation.y,
  };
  if (!isPointInLauncherLaneRegion(position, ctx.table.launcher)) {
    return;
  }

  const velocity = ctx.ballBody.linvel();
  const speed = Math.hypot(velocity.x, velocity.y);
  if (speed > ctx.table.launcher.feedSettledSpeedMax) {
    return;
  }

  removeMainWorldBall(ctx);
  ctx.launcherChain.spawnBall(position);
}

function removeMainWorldBall(ctx: PhysicsWorldContext): void {
  if (!ctx.ballBody) {
    return;
  }

  if (ctx.ballColliderHandle !== null) {
    ctx.colliderMetaByHandle.delete(ctx.ballColliderHandle);
  }
  ctx.world.removeRigidBody(ctx.ballBody);
  ctx.ballBody = null;
  ctx.ballColliderHandle = null;
  // resetCaptureLifecycleState handled by caller or removed elsewhere
}
