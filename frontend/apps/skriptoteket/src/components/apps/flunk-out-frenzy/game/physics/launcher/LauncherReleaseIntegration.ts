import type { LauncherContext } from "./LauncherContext";

const RELEASE_STRIKE_LEAD_PX = 3;
const RELEASE_CONTACT_OVERLAP_PX = 1.5;
const RELEASE_INTEGRATION_WINDOW_MS = 64;
const RELEASE_STRIKE_SETTLE_MARGIN_MS = 24;

export function resolveReleaseStrikeTargetY(ctx: LauncherContext): number {
  const defaultTarget = ctx.parkCenter.y - RELEASE_STRIKE_LEAD_PX;
  if (!ctx.ballBody) {
    return defaultTarget;
  }
  const ballBottomY = ctx.ballBody.translation().y + ctx.ball.radius;
  const contactTarget =
    ballBottomY -
    RELEASE_CONTACT_OVERLAP_PX +
    ctx.launcher.threeD.plunger.depth / 2;
  return Math.min(defaultTarget, contactTarget);
}

export function computeReleaseIntegrationWindowMs(ctx: LauncherContext): number {
  const plunger = ctx.launcher.threeD.plunger;
  const strikeTargetY = resolveReleaseStrikeTargetY(ctx);
  const distanceToStrike = Math.abs(ctx.currentPlungerCenterY - strikeTargetY);
  const speedPerSecond = Math.max(plunger.speedFire, 1e-6);
  const travelMs = (distanceToStrike / speedPerSecond) * 1000;
  return Math.max(
    RELEASE_INTEGRATION_WINDOW_MS,
    Math.ceil(travelMs + RELEASE_STRIKE_SETTLE_MARGIN_MS),
  );
}
