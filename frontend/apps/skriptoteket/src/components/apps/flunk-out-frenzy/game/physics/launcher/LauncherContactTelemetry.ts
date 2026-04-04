import type { LauncherContext } from "./LauncherContext";

export function updateContactTelemetry(ctx: LauncherContext): void {
  if (!ctx.ballBody) {
    ctx.separationPx = null;
    ctx.overlapPx = 0;
    ctx.relativeVyAtContact = null;
    ctx.impulseTransferMarker = 0;
    if (ctx.plungerBallContactActive) {
      ctx.contactExitedThisStep = true;
    }
    ctx.plungerBallContactActive = false;
    return;
  }

  const ballPosition = ctx.ballBody.translation();
  const ballVelocity = ctx.ballBody.linvel();
  const plungerFrontFaceY =
    ctx.currentPlungerCenterY - ctx.launcher.threeD.plunger.depth / 2;
  const separation = plungerFrontFaceY - (ballPosition.y + ctx.ball.radius);
  const overlap = Math.max(-separation, 0);
  const contactActive = overlap > 0;

  ctx.separationPx = separation;
  ctx.overlapPx = Math.max(ctx.overlapPx, overlap);

  if (contactActive) {
    const relativeVyAtContact = ballVelocity.y - ctx.currentPlungerVelocityY;
    ctx.relativeVyAtContact =
      ctx.relativeVyAtContact === null
        ? relativeVyAtContact
        : Math.min(ctx.relativeVyAtContact, relativeVyAtContact);
  }

  ctx.impulseTransferMarker = Math.min(
    Math.max(ctx.overlapPx / Math.max(ctx.ball.radius, 1e-6), 0),
    1,
  );

  if (contactActive && !ctx.plungerBallContactActive) {
    ctx.contactEnteredThisStep = true;
  }
  if (!contactActive && ctx.plungerBallContactActive) {
    ctx.contactExitedThisStep = true;
  }
  ctx.plungerBallContactActive = contactActive;

  if (contactActive) {
    ctx.lastContactAtStep = ctx.stepCounter;
  }
}
