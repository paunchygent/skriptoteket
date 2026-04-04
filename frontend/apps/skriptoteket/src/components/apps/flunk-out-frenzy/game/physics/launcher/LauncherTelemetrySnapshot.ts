/**
 * Telemetry snapshot projection for the Flunk-Out Frenzy launcher chain.
 *
 * LauncherChain3D keeps mutable state in context; this helper turns that state
 * into the stable debug snapshot consumed by runtime proof telemetry.
 */

import type { PhysicsLauncherTelemetrySnapshot } from "../physicsTypes";
import type { LauncherContext } from "./LauncherContext";

export function buildLauncherTelemetrySnapshot(
  ctx: LauncherContext,
): PhysicsLauncherTelemetrySnapshot {
  const ballPosition = ctx.ballBody?.translation() ?? null;
  const ballVelocity = ctx.ballBody?.linvel() ?? null;

  return {
    plunger: {
      currentY: ctx.currentPlungerCenterY,
      targetY: ctx.currentPlungerTargetY,
      chargeRatio: null,
      phase: "idle",
    },
    ball: {
      owner: ctx.ballBody ? "launcher_chain" : "none",
      position: ballPosition
        ? { x: ballPosition.x, y: ballPosition.y, z: ballPosition.z }
        : null,
      velocity: ballVelocity
        ? { x: ballVelocity.x, y: ballVelocity.y, z: ballVelocity.z }
        : null,
    },
    route: {
      pendingReleaseChargeRatio: ctx.pendingReleaseChargeRatio,
      activeRouteTag: ctx.activeTravelRoute?.route.tag ?? null,
      captureWindowMsRemaining: ctx.routeCaptureWindowMsRemaining,
      routeProgressDistancePx: ctx.activeTravelRoute?.distance ?? 0,
    },
    routeCapture: {
      lastDecision: ctx.lastRouteCaptureDecision,
      lastRejectReason: ctx.lastRouteCaptureRejectReason,
    },
    sensors: {
      feedInside: ctx.feedInside,
      exitInside: ctx.exitInside,
      lastSw16ExitStep: ctx.lastSw16ExitStep,
    },
    contact: {
      plungerBallContactActive: ctx.plungerBallContactActive,
      contactEnteredThisStep: ctx.contactEnteredThisStep,
      contactExitedThisStep: ctx.contactExitedThisStep,
      separationPx: ctx.separationPx,
      overlapPx: ctx.overlapPx,
      relativeVyAtContact: ctx.relativeVyAtContact,
      lastContactAtStep: ctx.lastContactAtStep,
      impulseTransferMarker: ctx.impulseTransferMarker,
    },
    seamTransition: ctx.seamTransition,
  };
}
