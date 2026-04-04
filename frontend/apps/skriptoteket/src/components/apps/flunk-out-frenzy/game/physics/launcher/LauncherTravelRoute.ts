/**
 * Route math and bounded handoff helpers for the Flunk-Out Frenzy launcher.
 *
 * The launcher chain uses these helpers to classify authored route segments,
 * measure along-route motion, and keep any remaining route kinematics explicit
 * and testable while the broader runtime-shortcut remediation is in progress.
 */

import type {
  TableLauncherHandoffSeam3DDefinition,
  TableLauncherObservationSpine3DDefinition,
  TablePoint3D,
} from "../../table/tableDefinitionTypes";
import type { LauncherChainBallSnapshot } from "../launcherChain3d";
import type { ActiveTravelRoute, LauncherContext } from "./LauncherContext";

export function resolveTravelRoute(
  ctx: LauncherContext,
  chargeRatio: number,
): TableLauncherObservationSpine3DDefinition | null {
  const routes = resolveObservationSpines(ctx);
  if (routes.length === 0) {
    return null;
  }

  const eligible = routes.filter((route) => {
    const entryMode = route.entryMode ?? "release";
    return entryMode === "release" && chargeRatio >= route.minChargeRatio;
  });
  if (eligible.length === 0) {
    return null;
  }

  return eligible.sort((a, b) => b.minChargeRatio - a.minChargeRatio)[0];
}

export function buildActiveTravelRoute(
  route: TableLauncherObservationSpine3DDefinition,
  releaseSpeed: number,
): ActiveTravelRoute {
  const cumulativeDistances = buildCumulativeDistances(route.path);
  const totalDistance = cumulativeDistances[cumulativeDistances.length - 1] ?? 0;
  return {
    route,
    cumulativeDistances,
    totalDistance,
    distance: 0,
    speed: Math.max(releaseSpeed, 0),
  };
}

export function buildCumulativeDistances(
  path: readonly TablePoint3D[],
): readonly number[] {
  const cumulative: number[] = [0];
  for (let index = 1; index < path.length; index += 1) {
    const previous = path[index - 1];
    const current = path[index];
    const segmentDistance = Math.hypot(
      current.x - previous.x,
      current.y - previous.y,
      current.z - previous.z,
    );
    cumulative[index] = cumulative[index - 1] + segmentDistance;
  }
  return cumulative;
}

export function samplePointAlongTravelRoute(
  path: readonly TablePoint3D[],
  cumulativeDistances: readonly number[],
  totalDistance: number,
  distance: number,
): TablePoint3D {
  if (path.length === 0) {
    throw new Error("Launcher travel route cannot be empty.");
  }
  if (path.length === 1 || totalDistance <= 1e-6) {
    return path[0];
  }

  const clamped = Math.min(Math.max(distance, 0), totalDistance);
  for (let index = 1; index < path.length; index += 1) {
    const segmentStartDistance = cumulativeDistances[index - 1];
    const segmentEndDistance = cumulativeDistances[index];
    if (clamped > segmentEndDistance && index < path.length - 1) {
      continue;
    }
    const segmentLength = Math.max(
      segmentEndDistance - segmentStartDistance,
      1e-6,
    );
    const t = (clamped - segmentStartDistance) / segmentLength;
    const start = path[index - 1];
    const end = path[index];
    return {
      x: start.x + (end.x - start.x) * t,
      y: start.y + (end.y - start.y) * t,
      z: start.z + (end.z - start.z) * t,
    };
  }

  return path[path.length - 1];
}

export function advanceTravelRoute(
  ctx: LauncherContext,
  dtMs: number,
): LauncherChainBallSnapshot | null {
  if (!ctx.activeTravelRoute || !ctx.ballBody) {
    return null;
  }

  const dtSeconds = dtMs / 1000;
  const nextDistance = Math.min(
    ctx.activeTravelRoute.distance + ctx.activeTravelRoute.speed * dtSeconds,
    ctx.activeTravelRoute.totalDistance,
  );
  const nextPoint = samplePointAlongTravelRoute(
    ctx.activeTravelRoute.route.path,
    ctx.activeTravelRoute.cumulativeDistances,
    ctx.activeTravelRoute.totalDistance,
    nextDistance,
  );
  const velocity = resolveTravelRouteVelocity(
    ctx.activeTravelRoute.route.path,
    ctx.activeTravelRoute.cumulativeDistances,
    ctx.activeTravelRoute.totalDistance,
    nextDistance,
    ctx.activeTravelRoute.speed,
  );

  ctx.ballBody.setTranslation(nextPoint, true);
  ctx.ballBody.setLinvel(velocity, true);
  ctx.activeTravelRoute.distance = nextDistance;

  if (nextDistance < ctx.activeTravelRoute.totalDistance) {
    return null;
  }

  const nextRouteTag = ctx.activeTravelRoute.route.nextCarrierTag;
  const handoffSeam = resolveHandoffSeamByTag(ctx, nextRouteTag);
  if (!handoffSeam) {
    const seamFrom =
      ctx.activeTravelRoute.route.path[
        ctx.activeTravelRoute.route.path.length - 1
      ];
    const nextRoute = resolveTravelRouteByTag(ctx, nextRouteTag);
    const seamTo = nextRoute.path[0];
    ctx.seamTransition = {
      fromRouteTag: ctx.activeTravelRoute.route.tag,
      toRouteTag: nextRoute.tag,
      xyDeltaPx: Math.hypot(seamFrom.x - seamTo.x, seamFrom.y - seamTo.y),
      zDeltaPx: Math.abs(seamFrom.z - seamTo.z),
    };
    ctx.activeTravelRoute = buildActiveTravelRoute(
      nextRoute,
      ctx.activeTravelRoute.speed,
    );
    const startPoint = samplePointAlongTravelRoute(
      ctx.activeTravelRoute.route.path,
      ctx.activeTravelRoute.cumulativeDistances,
      ctx.activeTravelRoute.totalDistance,
      ctx.activeTravelRoute.distance,
    );
    const startVelocity = resolveTravelRouteVelocity(
      ctx.activeTravelRoute.route.path,
      ctx.activeTravelRoute.cumulativeDistances,
      ctx.activeTravelRoute.totalDistance,
      ctx.activeTravelRoute.distance,
      ctx.activeTravelRoute.speed,
    );
    ctx.ballBody.setTranslation(startPoint, true);
    ctx.ballBody.setLinvel(startVelocity, true);
    return null;
  }

  return {
    position: {
      x: handoffSeam.anchor.x,
      y: handoffSeam.anchor.y,
      z: handoffSeam.handoffZ,
    },
    velocity: handoffSeam.handoffVelocity,
  };
}

export function resolveTravelRouteVelocity(
  path: readonly TablePoint3D[],
  cumulativeDistances: readonly number[],
  totalDistance: number,
  distance: number,
  speed: number,
): { x: number; y: number; z: number } {
  const tangent = resolveTravelRouteTangent(path, cumulativeDistances, totalDistance, distance);
  return {
    x: tangent.x * speed,
    y: tangent.y * speed,
    z: tangent.z * speed,
  };
}

export function resolveObservedTravelRouteProgressSpeed(
  route: TableLauncherObservationSpine3DDefinition,
  velocity: { x: number; y: number; z: number },
): number {
  const cumulativeDistances = buildCumulativeDistances(route.path);
  const totalDistance = cumulativeDistances[cumulativeDistances.length - 1] ?? 0;
  const tangent = resolveTravelRouteTangent(route.path, cumulativeDistances, totalDistance, 0);
  const planarTangentMagnitude = Math.hypot(tangent.x, tangent.y);
  if (planarTangentMagnitude <= 1e-6) {
    return 0;
  }
  const observedPlanarSpeed = Math.hypot(velocity.x, velocity.y);
  return observedPlanarSpeed / planarTangentMagnitude;
}

function resolveTravelRouteTangent(
  path: readonly TablePoint3D[],
  cumulativeDistances: readonly number[],
  totalDistance: number,
  distance: number,
): { x: number; y: number; z: number } {
  if (path.length < 2 || totalDistance <= 1e-6) {
    return { x: 0, y: 0, z: 0 };
  }

  const clamped = Math.min(Math.max(distance, 0), totalDistance);
  for (let index = 1; index < path.length; index += 1) {
    const segmentEndDistance = cumulativeDistances[index];
    if (clamped > segmentEndDistance && index < path.length - 1) {
      continue;
    }
    return normalizeTravelRouteVector(
      path[index].x - path[index - 1].x,
      path[index].y - path[index - 1].y,
      path[index].z - path[index - 1].z,
    );
  }

  const lastIndex = path.length - 1;
  return normalizeTravelRouteVector(
    path[lastIndex].x - path[lastIndex - 1].x,
    path[lastIndex].y - path[lastIndex - 1].y,
    path[lastIndex].z - path[lastIndex - 1].z,
  );
}

function normalizeTravelRouteVector(
  dx: number,
  dy: number,
  dz: number,
): { x: number; y: number; z: number } {
  const magnitude = Math.hypot(dx, dy, dz);
  if (magnitude <= 1e-6) {
    return { x: 0, y: 0, z: 0 };
  }
  return {
    x: dx / magnitude,
    y: dy / magnitude,
    z: dz / magnitude,
  };
}

export function resolveTravelRouteByTag(
  ctx: LauncherContext,
  tag: string,
): TableLauncherObservationSpine3DDefinition {
  const route = resolveObservationSpines(ctx).find(
    (candidate) => candidate.tag === tag,
  );
  if (!route) {
    throw new Error(`Launcher travel route "${tag}" is not defined.`);
  }
  return route;
}

function resolveObservationSpines(
  ctx: LauncherContext,
): readonly TableLauncherObservationSpine3DDefinition[] {
  return ctx.launcher.threeD.carriers.filter((carrier) => {
    return carrier.kind === "observation_spine";
  }) as readonly TableLauncherObservationSpine3DDefinition[];
}

function resolveHandoffSeamByTag(
  ctx: LauncherContext,
  tag: string,
): TableLauncherHandoffSeam3DDefinition | null {
  const carrier = ctx.launcher.threeD.carriers.find((candidate) => {
    return candidate.tag === tag && candidate.kind === "handoff_seam";
  });
  if (!carrier || carrier.kind !== "handoff_seam") {
    return null;
  }
  return carrier;
}
