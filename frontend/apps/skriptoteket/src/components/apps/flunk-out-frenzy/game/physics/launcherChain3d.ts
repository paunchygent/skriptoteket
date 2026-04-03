/**
 * Dedicated Rapier 3D launcher-chain seam for Flunk-Out Frenzy.
 *
 * This module owns only the donor-backed shooter lane, plunger, and immediate
 * right-side receiving handoff. It exists because the flat board model makes
 * donor `Wall34` a false full cap across the launcher path. The rest of the
 * board still consumes top-down snapshots and machine events through
 * `PhysicsWorld`.
 */

import RAPIER3D from "@dimforge/rapier3d-compat";

import type { MachineEvent } from "./physicsTypes";
import { isPointInTriggerShape } from "./plungerLaneState";
import type {
  TableBallDefinition,
  TableLauncherDefinition,
  TableLauncherTravelRoute3DDefinition,
  TablePoint,
  TablePoint3D,
} from "../table/tableDefinitionTypes";
import { magnitude, midpoint, segmentAngle } from "../table/pinballTableMath";

export interface LauncherChainBallSnapshot {
  position: TablePoint3D;
  velocity: TablePoint;
}

export interface LauncherChainPlungerSnapshot {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface LauncherChainStepResult {
  releaseToBoard: LauncherChainBallSnapshot | null;
  machineEvents: MachineEvent[];
}

interface ActiveTravelRoute {
  route: TableLauncherTravelRoute3DDefinition;
  cumulativeDistances: readonly number[];
  totalDistance: number;
  distance: number;
  speed: number;
}

export class LauncherChain3D {
  private readonly world: RAPIER3D.World;
  private readonly plungerBody: RAPIER3D.RigidBody;
  private ballBody: RAPIER3D.RigidBody | null = null;
  private readonly parkCenter: TablePoint3D;
  private readonly releasePlaneY: number;
  private currentPlungerCenterY: number;
  private exitInside = false;
  private boardHandoffArmed = false;
  private activeTravelRoute: ActiveTravelRoute | null = null;
  private pendingRouteGateEvent = false;

  constructor(
    private readonly launcher: TableLauncherDefinition,
    private readonly ball: TableBallDefinition,
  ) {
    this.world = new RAPIER3D.World({ x: 0, y: 0, z: -981 });
    this.parkCenter = launcher.threeD.plunger.center;
    this.releasePlaneY = resolveReleasePlaneY(launcher);
    this.currentPlungerCenterY = this.parkCenter.y;

    this.createFloor();
    this.createWalls();
    this.plungerBody = this.createPlungerBody();
  }

  dispose(): void {
    this.world.free();
  }

  hasBall(): boolean {
    return this.ballBody !== null;
  }

  spawnBall(position: TablePoint): void {
    this.removeBall();

    const body = this.world.createRigidBody(
      RAPIER3D.RigidBodyDesc.dynamic()
        .setTranslation(position.x, position.y, this.launcher.threeD.ballRestZ)
        .setCanSleep(false)
        .setLinearDamping(0.08)
        .setAngularDamping(0.08)
        .setCcdEnabled(true),
    );
    this.world.createCollider(
      RAPIER3D.ColliderDesc.ball(this.ball.radius)
        .setMass(this.ball.mass)
        .setRestitution(0.25)
        .setFriction(0.16),
      body,
    );

    this.ballBody = body;
    this.exitInside = this.isInsideExitSensor();
    this.boardHandoffArmed = false;
    this.activeTravelRoute = null;
    this.pendingRouteGateEvent = false;
  }

  removeBall(): void {
    if (!this.ballBody) {
      return;
    }

    this.world.removeRigidBody(this.ballBody);
    this.ballBody = null;
    this.exitInside = false;
    this.boardHandoffArmed = false;
    this.activeTravelRoute = null;
    this.pendingRouteGateEvent = false;
  }

  currentSnapshot(): LauncherChainBallSnapshot | null {
    if (!this.ballBody) {
      return null;
    }

    const translation = this.ballBody.translation();
    const velocity = this.ballBody.linvel();
    return {
      position: { x: translation.x, y: translation.y, z: translation.z },
      velocity: { x: velocity.x, y: velocity.y },
    };
  }

  currentPlungerSnapshot(): LauncherChainPlungerSnapshot {
    const plunger = this.launcher.threeD.plunger;
    return {
      x: this.parkCenter.x,
      y: this.currentPlungerCenterY,
      width: plunger.width,
      height: plunger.depth,
    };
  }

  step(
    dtMs: number,
    chargeRatio: number | null,
    releaseChargeRatio: number | null,
  ): LauncherChainStepResult {
    if (!this.ballBody) {
      return { releaseToBoard: null, machineEvents: [] };
    }

    const machineEvents: MachineEvent[] = [];
    if (releaseChargeRatio !== null) {
      this.applyReleaseImpulse(releaseChargeRatio);
    }
    this.syncPlunger(dtMs, chargeRatio);
    this.world.timestep = dtMs / 1000;
    this.world.step();

    const routeHandoff = this.activeTravelRoute ? this.advanceTravelRoute(dtMs) : null;
    if (this.activeTravelRoute) {
      this.boardHandoffArmed = false;
    }
    const wasInsideExit = this.exitInside;
    const isInsideExit = this.isInsideExitSensor();
    this.exitInside = isInsideExit;

    if (this.pendingRouteGateEvent) {
      machineEvents.push({ type: "gate-passed", tag: "gate/launch-lane-exit" });
      this.pendingRouteGateEvent = false;
    }

    if (wasInsideExit && !isInsideExit) {
      machineEvents.push({ type: "gate-passed", tag: "gate/launch-lane-exit" });
      this.boardHandoffArmed = true;
    }

    if (this.boardHandoffArmed && !this.activeTravelRoute && this.hasClearedReleasePlane()) {
      const snapshot = this.currentSnapshot();
      this.removeBall();
      return { releaseToBoard: snapshot, machineEvents };
    }

    if (routeHandoff) {
      this.removeBall();
      return { releaseToBoard: routeHandoff, machineEvents };
    }

    return { releaseToBoard: null, machineEvents };
  }

  private createFloor(): void {
    this.world.createCollider(
      RAPIER3D.ColliderDesc.cuboid(1000, 2000, 2).setTranslation(0, 0, -2),
    );
  }

  private createWalls(): void {
    for (const wall of this.launcher.threeD.walls) {
      const collider = createExtrudedPolygonColliderDesc(
        wall.points,
        wall.heightBottom,
        wall.heightTop,
      );
      this.world.createCollider(collider);
    }

    for (const rail of this.launcher.threeD.guideRails) {
      const halfHeight = Math.max((rail.heightTop - rail.heightBottom) / 2, 0.5);
      const centerZ = rail.heightBottom + halfHeight;
      for (let index = 0; index < rail.path.length - 1; index += 1) {
        const from = rail.path[index];
        const to = rail.path[index + 1];
        this.world.createCollider(
          RAPIER3D.ColliderDesc.cuboid(
            magnitude({ x: to.x - from.x, y: to.y - from.y }) / 2,
            rail.radius,
            halfHeight,
          )
            .setTranslation(midpoint(from, to).x, midpoint(from, to).y, centerZ)
            .setRotation(quaternionFromYaw(segmentAngle(from, to))),
        );
      }
    }
  }

  private createPlungerBody(): RAPIER3D.RigidBody {
    const plunger = this.launcher.threeD.plunger;
    const body = this.world.createRigidBody(
      RAPIER3D.RigidBodyDesc.kinematicPositionBased().setTranslation(
        plunger.center.x,
        plunger.center.y,
        plunger.center.z,
      ),
    );

    this.world.createCollider(
      RAPIER3D.ColliderDesc.cuboid(
        plunger.width / 2,
        plunger.depth / 2,
        Math.max(plunger.height / 2, 0.5),
      )
        .setRestitution(0.1)
        .setFriction(0.25),
      body,
    );

    return body;
  }

  private syncPlunger(dtMs: number, chargeRatio: number | null): void {
    const plunger = this.launcher.threeD.plunger;
    const dtSeconds = dtMs / 1000;
    const targetCenterY = chargeRatio !== null
      ? this.parkCenter.y + plunger.stroke * chargeRatio
      : this.parkCenter.y;

    const maxTravel = chargeRatio !== null
      ? plunger.speedPull * dtMs
      : plunger.speedFire * dtSeconds;
    const delta = targetCenterY - this.currentPlungerCenterY;
    const travel = Math.abs(delta) <= maxTravel
      ? delta
      : Math.sign(delta) * maxTravel;
    this.currentPlungerCenterY += travel;

    this.plungerBody.setNextKinematicTranslation({
      x: this.parkCenter.x,
      y: this.currentPlungerCenterY,
      z: this.parkCenter.z,
    });
  }

  private applyReleaseImpulse(chargeRatio: number): void {
    if (!this.ballBody) {
      return;
    }
    const plunger = this.launcher.threeD.plunger;
    const velocity = this.ballBody.linvel();
    const minimumLaunchSpeed = this.launcher.launchImpulseMin * plunger.momentumTransfer;
    const maximumLaunchSpeed = this.launcher.launchImpulseMax * plunger.momentumTransfer;
    const launchSpeed = minimumLaunchSpeed + (maximumLaunchSpeed - minimumLaunchSpeed) * chargeRatio;

    if (-velocity.y >= launchSpeed) {
      return;
    }

    const travelRoute = this.resolveTravelRoute(chargeRatio);
    if (travelRoute) {
      this.activeTravelRoute = buildActiveTravelRoute(travelRoute, launchSpeed);
      this.boardHandoffArmed = false;
      this.pendingRouteGateEvent = true;
      const startPoint = samplePointAlongTravelRoute(
        this.activeTravelRoute.route.path,
        this.activeTravelRoute.cumulativeDistances,
        this.activeTravelRoute.totalDistance,
        this.activeTravelRoute.distance,
      );
      this.ballBody.setTranslation(startPoint, true);
      this.ballBody.setLinvel({ x: 0, y: 0, z: 0 }, true);
      return;
    }

    this.ballBody.setLinvel(
      {
        x: velocity.x,
        y: -launchSpeed,
        z: velocity.z,
      },
      true,
    );
  }

  private resolveTravelRoute(chargeRatio: number): TableLauncherTravelRoute3DDefinition | null {
    const routes = this.launcher.threeD.travelRoutes;
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

  private advanceTravelRoute(dtMs: number): LauncherChainBallSnapshot | null {
    if (!this.activeTravelRoute || !this.ballBody) {
      return null;
    }

    const dtSeconds = dtMs / 1000;
    const nextDistance = Math.min(
      this.activeTravelRoute.distance + this.activeTravelRoute.speed * dtSeconds,
      this.activeTravelRoute.totalDistance,
    );
    const currentPoint = samplePointAlongTravelRoute(
      this.activeTravelRoute.route.path,
      this.activeTravelRoute.cumulativeDistances,
      this.activeTravelRoute.totalDistance,
      this.activeTravelRoute.distance,
    );
    const nextPoint = samplePointAlongTravelRoute(
      this.activeTravelRoute.route.path,
      this.activeTravelRoute.cumulativeDistances,
      this.activeTravelRoute.totalDistance,
      nextDistance,
    );
    const dx = nextPoint.x - currentPoint.x;
    const dy = nextPoint.y - currentPoint.y;
    const dz = nextPoint.z - currentPoint.z;
    const segmentMagnitude = Math.hypot(dx, dy, dz);
    const velocity = segmentMagnitude <= 1e-6
      ? { x: 0, y: 0, z: 0 }
      : {
          x: (dx / segmentMagnitude) * this.activeTravelRoute.speed,
          y: (dy / segmentMagnitude) * this.activeTravelRoute.speed,
          z: (dz / segmentMagnitude) * this.activeTravelRoute.speed,
        };

    this.ballBody.setTranslation(nextPoint, true);
    this.ballBody.setLinvel(velocity, true);
    this.activeTravelRoute.distance = nextDistance;

    if (nextDistance < this.activeTravelRoute.totalDistance) {
      return null;
    }

    const nextRouteTag = this.activeTravelRoute.route.nextRouteTag;
    if (nextRouteTag) {
      const nextRoute = this.resolveTravelRouteByTag(nextRouteTag);
      this.activeTravelRoute = buildActiveTravelRoute(
        nextRoute,
        this.activeTravelRoute.speed,
      );
      const startPoint = samplePointAlongTravelRoute(
        this.activeTravelRoute.route.path,
        this.activeTravelRoute.cumulativeDistances,
        this.activeTravelRoute.totalDistance,
        this.activeTravelRoute.distance,
      );
      this.ballBody.setTranslation(startPoint, true);
      this.ballBody.setLinvel({ x: 0, y: 0, z: 0 }, true);
      return null;
    }

    const handoffZ = this.activeTravelRoute.route.handoffZ ?? this.launcher.threeD.ballRestZ;

    return {
      position: {
        x: nextPoint.x,
        y: nextPoint.y,
        z: handoffZ,
      },
      velocity: this.activeTravelRoute.route.handoffVelocity,
    };
  }

  private resolveTravelRouteByTag(tag: string): TableLauncherTravelRoute3DDefinition {
    const route = this.launcher.threeD.travelRoutes?.find((candidate) => candidate.tag === tag);
    if (!route) {
      throw new Error(`Launcher travel route "${tag}" is not defined.`);
    }
    return route;
  }

  private isInsideExitSensor(): boolean {
    if (!this.ballBody) {
      return false;
    }

    const exitSensor = this.launcher.threeD.sensors.find((sensor) => sensor.semanticRole === "exit");
    if (!exitSensor) {
      return false;
    }

    const position = this.ballBody.translation();
    return isPointInTriggerShape({ x: position.x, y: position.y }, exitSensor.shape);
  }

  private hasClearedReleasePlane(): boolean {
    if (!this.ballBody) {
      return false;
    }

    return this.ballBody.translation().y <= this.releasePlaneY;
  }
}

function buildActiveTravelRoute(
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

function buildCumulativeDistances(path: readonly TablePoint3D[]): readonly number[] {
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

function samplePointAlongTravelRoute(
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
    const segmentLength = Math.max(segmentEndDistance - segmentStartDistance, 1e-6);
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

function createExtrudedPolygonColliderDesc(
  points: readonly TablePoint[],
  heightBottom: number,
  heightTop: number,
): RAPIER3D.ColliderDesc {
  const top = Math.max(heightTop, heightBottom + 0.5);
  const vertices = new Float32Array(
    points.flatMap((point) => [
      point.x,
      point.y,
      heightBottom,
      point.x,
      point.y,
      top,
    ]),
  );
  const collider = RAPIER3D.ColliderDesc.convexHull(vertices);
  if (!collider) {
    throw new Error("Failed to compile 3D launcher-chain wall from donor polygon.");
  }
  return collider;
}

function quaternionFromYaw(angleRad: number): RAPIER3D.Rotation {
  return {
    x: 0,
    y: 0,
    z: Math.sin(angleRad / 2),
    w: Math.cos(angleRad / 2),
  };
}

function resolveReleasePlaneY(launcher: TableLauncherDefinition): number {
  const divider = launcher.threeD.walls.find((wall) => wall.tag === "launcher/wall34");
  if (!divider) {
    throw new Error("3D launcher chain is missing donor Wall34 for board handoff.");
  }

  return Math.min(...divider.points.map((point) => point.y));
}
