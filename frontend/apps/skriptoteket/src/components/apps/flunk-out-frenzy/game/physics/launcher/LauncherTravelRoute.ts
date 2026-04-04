import type {
  TableLauncherTravelRoute3DDefinition,
  TablePoint3D,
} from "../../table/tableDefinitionTypes";
import type { LauncherChainBallSnapshot } from "../launcherChain3d";
import type { ActiveTravelRoute, LauncherContext } from "./LauncherContext";

export function resolveTravelRoute(
  ctx: LauncherContext,
  chargeRatio: number,
): TableLauncherTravelRoute3DDefinition | null {
  const routes = ctx.launcher.threeD.travelRoutes;
  if (!routes || routes.length === 0) {
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
  route: TableLauncherTravelRoute3DDefinition,
  releaseSpeed: number,
): ActiveTravelRoute {
  const cumulativeDistances = buildCumulativeDistances(route.path);
  const totalDistance = cumulativeDistances[cumulativeDistances.length - 1] ?? 0;
  return {
    route,
    cumulativeDistances,
    totalDistance,
    distance: 0,
    speed: Math.max(releaseSpeed * 0.85, 850),
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
  const currentPoint = samplePointAlongTravelRoute(
    ctx.activeTravelRoute.route.path,
    ctx.activeTravelRoute.cumulativeDistances,
    ctx.activeTravelRoute.totalDistance,
    ctx.activeTravelRoute.distance,
  );
  const nextPoint = samplePointAlongTravelRoute(
    ctx.activeTravelRoute.route.path,
    ctx.activeTravelRoute.cumulativeDistances,
    ctx.activeTravelRoute.totalDistance,
    nextDistance,
  );
  const dx = nextPoint.x - currentPoint.x;
  const dy = nextPoint.y - currentPoint.y;
  const dz = nextPoint.z - currentPoint.z;
  const segmentMagnitude = Math.hypot(dx, dy, dz);
  const velocity =
    segmentMagnitude <= 1e-6
      ? { x: 0, y: 0, z: 0 }
      : {
          x: (dx / segmentMagnitude) * ctx.activeTravelRoute.speed,
          y: (dy / segmentMagnitude) * ctx.activeTravelRoute.speed,
          z: (dz / segmentMagnitude) * ctx.activeTravelRoute.speed,
        };

  ctx.ballBody.setTranslation(nextPoint, true);
  ctx.ballBody.setLinvel(velocity, true);
  ctx.activeTravelRoute.distance = nextDistance;

  if (nextDistance < ctx.activeTravelRoute.totalDistance) {
    return null;
  }

  const nextRouteTag = ctx.activeTravelRoute.route.nextRouteTag;
  if (nextRouteTag) {
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
    ctx.ballBody.setTranslation(startPoint, true);
    ctx.ballBody.setLinvel({ x: 0, y: 0, z: 0 }, true);
    return null;
  }

  const handoffZ =
    ctx.activeTravelRoute.route.handoffZ ?? ctx.launcher.threeD.ballRestZ;
  const handoffVelocity = ctx.activeTravelRoute.route.handoffVelocity;
  if (!handoffVelocity) {
    throw new Error(
      `Launcher travel route "${ctx.activeTravelRoute.route.tag}" is missing terminal handoff velocity.`,
    );
  }

  return {
    position: {
      x: nextPoint.x,
      y: nextPoint.y,
      z: handoffZ,
    },
    velocity: handoffVelocity,
  };
}

export function resolveTravelRouteByTag(
  ctx: LauncherContext,
  tag: string,
): TableLauncherTravelRoute3DDefinition {
  const route = ctx.launcher.threeD.travelRoutes?.find(
    (candidate) => candidate.tag === tag,
  );
  if (!route) {
    throw new Error(`Launcher travel route "${tag}" is not defined.`);
  }
  return route;
}
