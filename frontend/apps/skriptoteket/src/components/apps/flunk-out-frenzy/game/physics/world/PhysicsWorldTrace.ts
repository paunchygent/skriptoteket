import type {
  PhysicsLaunchToDropPhase,
  PhysicsLaunchToDropTraceStep,
  PhysicsLauncherTelemetrySnapshot,
} from "../physicsTypes";
import type { PhysicsWorldContext } from "./PhysicsWorldContext";

export function buildLaunchToDropTraceStep(
  ctx: PhysicsWorldContext,
  launcherTelemetry: PhysicsLauncherTelemetrySnapshot | null,
): PhysicsLaunchToDropTraceStep | null {
  if (!launcherTelemetry) {
    return null;
  }

  return {
    stepIndex: ctx.traceStepIndex,
    dtMs: ctx.lastStepDtMs,
    phase: resolveLaunchToDropPhase(ctx, launcherTelemetry),
    ballOwner: launcherTelemetry.ball.owner,
    ballPosition: launcherTelemetry.ball.position,
    ballVelocity: launcherTelemetry.ball.velocity,
    plunger: launcherTelemetry.plunger,
    route: launcherTelemetry.route,
    routeCapture: launcherTelemetry.routeCapture,
    sensors: launcherTelemetry.sensors,
    contact: launcherTelemetry.contact,
    seamTransition: launcherTelemetry.seamTransition,
    events: [...ctx.lastStepEvents],
    handoffToBoardStep: ctx.lastHandoffToBoardStep,
    firstBoardCollisionStep: ctx.firstBoardCollisionStep,
    boardCollisionStartedThisStep: ctx.boardCollisionStartedThisStep,
  };
}

export function resolveLaunchToDropPhase(
  ctx: PhysicsWorldContext,
  launcherTelemetry: PhysicsLauncherTelemetrySnapshot,
): PhysicsLaunchToDropPhase {
  const routeTag = launcherTelemetry.route.activeRouteTag;
  if (routeTag === "launcher/travel/overhead") {
    return "route_overhead";
  }
  if (routeTag === "launcher/travel/endpoint-bridge") {
    return "route_endpoint_bridge";
  }
  if (routeTag === "launcher/travel/descent") {
    return "route_descent";
  }

  if (launcherTelemetry.ball.owner === "main_world") {
    if (
      ctx.lastHandoffToBoardStep !== null &&
      ctx.traceStepIndex === ctx.lastHandoffToBoardStep
    ) {
      return "handoff_to_board";
    }
    if (
      ctx.firstBoardCollisionStep !== null &&
      ctx.traceStepIndex > ctx.firstBoardCollisionStep
    ) {
      return "board_drop_postimpact";
    }
    return "board_drop_preimpact";
  }

  if (launcherTelemetry.plunger.phase === "charging") {
    return "charge_pull";
  }
  if (
    launcherTelemetry.plunger.phase === "released" &&
    launcherTelemetry.ball.owner === "launcher_chain"
  ) {
    return "release_strike_window";
  }

  return "feed_rest";
}
