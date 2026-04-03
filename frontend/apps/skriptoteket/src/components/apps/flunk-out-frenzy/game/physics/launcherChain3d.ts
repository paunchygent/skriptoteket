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

import type {
  LauncherRouteCaptureDecision,
  LauncherRouteCaptureRejectReason,
  MachineEvent,
  PhysicsLauncherTelemetrySnapshot,
} from "./physicsTypes";
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

const RELEASE_ROUTE_ENTRY_TOLERANCE_MULTIPLIER = 1.5;
const RELEASE_ROUTE_ENTRY_MIN_UPWARD_SPEED = 1;
const RELEASE_ROUTE_CAPTURE_WINDOW_MS = 2200;
const STRIKE_READY_REST_GAP_PX = 1;
const RELEASE_INTEGRATION_SUBSTEP_MS = 4;
const RELEASE_INTEGRATION_WINDOW_MS = 64;
const RELEASE_STRIKE_LEAD_PX = 3;
const RELEASE_CONTACT_OVERLAP_PX = 1.5;
const RELEASE_STRIKE_SETTLE_MARGIN_MS = 24;

type RouteCaptureRejectReason = Exclude<LauncherRouteCaptureRejectReason, null>;

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
  private pendingReleaseChargeRatio: number | null = null;
  private routeCaptureWindowMsRemaining = 0;
  private stepCounter = 0;
  private feedInside = false;
  private lastSw16ExitStep: number | null = null;
  private lastRouteCaptureDecision: LauncherRouteCaptureDecision = "none";
  private lastRouteCaptureRejectReason: LauncherRouteCaptureRejectReason = null;
  private currentPlungerTargetY = 0;
  private currentPlungerVelocityY = 0;
  private plungerBallContactActive = false;
  private contactEnteredThisStep = false;
  private contactExitedThisStep = false;
  private separationPx: number | null = null;
  private overlapPx = 0;
  private relativeVyAtContact: number | null = null;
  private lastContactAtStep: number | null = null;
  private impulseTransferMarker = 0;
  private releaseIntegrationWindowMsRemaining = 0;

  constructor(
    private readonly launcher: TableLauncherDefinition,
    private readonly ball: TableBallDefinition,
  ) {
    this.world = new RAPIER3D.World({ x: 0, y: 0, z: -981 });
    this.parkCenter = launcher.threeD.plunger.center;
    this.releasePlaneY = resolveReleasePlaneY(launcher);
    this.currentPlungerCenterY = this.parkCenter.y;
    this.currentPlungerTargetY = this.parkCenter.y;

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
    const strikeReadyPosition = this.resolveStrikeReadySpawnPosition(position);

    const body = this.world.createRigidBody(
      RAPIER3D.RigidBodyDesc.dynamic()
        .setTranslation(strikeReadyPosition.x, strikeReadyPosition.y, this.launcher.threeD.ballRestZ)
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
    this.ballBody.setLinvel({ x: 0, y: 0, z: 0 }, true);
    this.ballBody.setAngvel({ x: 0, y: 0, z: 0 }, true);
    this.stepCounter = 0;
    this.feedInside = this.isInsideFeedSensor();
    this.exitInside = this.isInsideExitSensor();
    this.lastSw16ExitStep = null;
    this.boardHandoffArmed = false;
    this.activeTravelRoute = null;
    this.pendingReleaseChargeRatio = null;
    this.routeCaptureWindowMsRemaining = 0;
    this.lastRouteCaptureDecision = "none";
    this.lastRouteCaptureRejectReason = null;
    this.plungerBallContactActive = false;
    this.contactEnteredThisStep = false;
    this.contactExitedThisStep = false;
    this.separationPx = null;
    this.overlapPx = 0;
    this.relativeVyAtContact = null;
    this.lastContactAtStep = null;
    this.impulseTransferMarker = 0;
    this.releaseIntegrationWindowMsRemaining = 0;
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
    this.pendingReleaseChargeRatio = null;
    this.routeCaptureWindowMsRemaining = 0;
    this.feedInside = false;
    this.stepCounter = 0;
    this.currentPlungerTargetY = this.parkCenter.y;
    this.currentPlungerVelocityY = 0;
    this.plungerBallContactActive = false;
    this.contactEnteredThisStep = false;
    this.contactExitedThisStep = false;
    this.separationPx = null;
    this.overlapPx = 0;
    this.relativeVyAtContact = null;
    this.lastContactAtStep = null;
    this.impulseTransferMarker = 0;
    this.releaseIntegrationWindowMsRemaining = 0;
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

  currentTelemetrySnapshot(): PhysicsLauncherTelemetrySnapshot {
    const ballPosition = this.ballBody?.translation() ?? null;
    const ballVelocity = this.ballBody?.linvel() ?? null;

    return {
      plunger: {
        currentY: this.currentPlungerCenterY,
        targetY: this.currentPlungerTargetY,
        chargeRatio: null,
        phase: "idle",
      },
      ball: {
        owner: this.ballBody ? "launcher_chain" : "none",
        position: ballPosition
          ? { x: ballPosition.x, y: ballPosition.y, z: ballPosition.z }
          : null,
        velocity: ballVelocity
          ? { x: ballVelocity.x, y: ballVelocity.y, z: ballVelocity.z }
          : null,
      },
      route: {
        pendingReleaseChargeRatio: this.pendingReleaseChargeRatio,
        activeRouteTag: this.activeTravelRoute?.route.tag ?? null,
        captureWindowMsRemaining: this.routeCaptureWindowMsRemaining,
      },
      routeCapture: {
        lastDecision: this.lastRouteCaptureDecision,
        lastRejectReason: this.lastRouteCaptureRejectReason,
      },
      sensors: {
        feedInside: this.feedInside,
        exitInside: this.exitInside,
        lastSw16ExitStep: this.lastSw16ExitStep,
      },
      contact: {
        plungerBallContactActive: this.plungerBallContactActive,
        contactEnteredThisStep: this.contactEnteredThisStep,
        contactExitedThisStep: this.contactExitedThisStep,
        separationPx: this.separationPx,
        overlapPx: this.overlapPx,
        relativeVyAtContact: this.relativeVyAtContact,
        lastContactAtStep: this.lastContactAtStep,
        impulseTransferMarker: this.impulseTransferMarker,
      },
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
    this.stepCounter += 1;
    this.contactEnteredThisStep = false;
    this.contactExitedThisStep = false;
    this.overlapPx = 0;
    this.relativeVyAtContact = null;
    this.impulseTransferMarker = 0;
    if (releaseChargeRatio !== null) {
      this.pendingReleaseChargeRatio = releaseChargeRatio;
      this.boardHandoffArmed = false;
      this.routeCaptureWindowMsRemaining = RELEASE_ROUTE_CAPTURE_WINDOW_MS;
      this.lastRouteCaptureDecision = "none";
      this.lastRouteCaptureRejectReason = null;
      this.releaseIntegrationWindowMsRemaining = this.computeReleaseIntegrationWindowMs();
    }
    this.stepWorldWithReleaseIntegration(dtMs, chargeRatio);
    this.tryEnterReleaseTravelRoute();
    if (this.pendingReleaseChargeRatio !== null && !this.activeTravelRoute) {
      this.routeCaptureWindowMsRemaining = Math.max(
        this.routeCaptureWindowMsRemaining - dtMs,
        0,
      );
      if (this.routeCaptureWindowMsRemaining === 0) {
        this.pendingReleaseChargeRatio = null;
        this.markRouteCaptureRejected("window_expired");
      }
    }

    const routeHandoff = this.activeTravelRoute ? this.advanceTravelRoute(dtMs) : null;
    if (this.activeTravelRoute) {
      this.boardHandoffArmed = false;
    }
    this.feedInside = this.isInsideFeedSensor();
    const wasInsideExit = this.exitInside;
    const isInsideExit = this.isInsideExitSensor();
    this.exitInside = isInsideExit;

    if (wasInsideExit && !isInsideExit) {
      machineEvents.push({ type: "gate-passed", tag: "gate/launch-lane-exit" });
      this.boardHandoffArmed = true;
      this.lastSw16ExitStep = this.stepCounter;
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

  private resolveStrikeReadySpawnPosition(position: TablePoint): TablePoint {
    const plungerFrontFaceY = this.parkCenter.y - this.launcher.threeD.plunger.depth / 2;
    const desiredBallY = plungerFrontFaceY - this.ball.radius - STRIKE_READY_REST_GAP_PX;
    return {
      x: position.x,
      y: Math.min(position.y, desiredBallY),
    };
  }

  private stepWorldWithReleaseIntegration(
    dtMs: number,
    chargeRatio: number | null,
  ): void {
    let remainingMs = dtMs;
    while (remainingMs > 0) {
      const stepMs = this.releaseIntegrationWindowMsRemaining > 0
        ? Math.min(RELEASE_INTEGRATION_SUBSTEP_MS, remainingMs)
        : remainingMs;
      this.syncPlunger(stepMs, chargeRatio);
      this.world.timestep = stepMs / 1000;
      this.world.step();
      this.updateContactTelemetry();
      remainingMs -= stepMs;
    }
    this.releaseIntegrationWindowMsRemaining = Math.max(
      this.releaseIntegrationWindowMsRemaining - dtMs,
      0,
    );
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
    const releaseStrikeTargetY = this.resolveReleaseStrikeTargetY();
    const targetCenterY = chargeRatio !== null
      ? this.parkCenter.y + plunger.stroke * chargeRatio
      : (this.releaseIntegrationWindowMsRemaining > 0
        ? releaseStrikeTargetY
        : this.parkCenter.y);
    this.currentPlungerTargetY = targetCenterY;

    const maxTravel = chargeRatio !== null
      ? plunger.speedPull * dtMs
      : plunger.speedFire * dtSeconds;
    const delta = targetCenterY - this.currentPlungerCenterY;
    const travel = Math.abs(delta) <= maxTravel
      ? delta
      : Math.sign(delta) * maxTravel;
    this.currentPlungerCenterY += travel;
    this.currentPlungerVelocityY = dtSeconds > 0 ? travel / dtSeconds : 0;

    this.plungerBody.setNextKinematicTranslation({
      x: this.parkCenter.x,
      y: this.currentPlungerCenterY,
      z: this.parkCenter.z,
    });
  }

  private resolveReleaseStrikeTargetY(): number {
    const defaultTarget = this.parkCenter.y - RELEASE_STRIKE_LEAD_PX;
    if (!this.ballBody) {
      return defaultTarget;
    }
    const ballBottomY = this.ballBody.translation().y + this.ball.radius;
    const contactTarget = ballBottomY
      - RELEASE_CONTACT_OVERLAP_PX
      + this.launcher.threeD.plunger.depth / 2;
    return Math.min(defaultTarget, contactTarget);
  }

  private computeReleaseIntegrationWindowMs(): number {
    const plunger = this.launcher.threeD.plunger;
    const strikeTargetY = this.resolveReleaseStrikeTargetY();
    const distanceToStrike = Math.abs(this.currentPlungerCenterY - strikeTargetY);
    const speedPerSecond = Math.max(plunger.speedFire, 1e-6);
    const travelMs = (distanceToStrike / speedPerSecond) * 1000;
    return Math.max(
      RELEASE_INTEGRATION_WINDOW_MS,
      Math.ceil(travelMs + RELEASE_STRIKE_SETTLE_MARGIN_MS),
    );
  }

  private tryEnterReleaseTravelRoute(): void {
    if (!this.ballBody) {
      return;
    }

    if (this.activeTravelRoute || this.pendingReleaseChargeRatio === null) {
      return;
    }
    if (this.routeCaptureWindowMsRemaining <= 0) {
      this.pendingReleaseChargeRatio = null;
      return;
    }

    const chargeRatio = this.pendingReleaseChargeRatio;
    const travelRoute = this.resolveTravelRoute(chargeRatio);
    if (!travelRoute) {
      this.pendingReleaseChargeRatio = null;
       this.markRouteCaptureRejected("no_route");
      return;
    }

    const routeEligibility = this.canAttachReleaseTravelRoute(travelRoute);
    if (!routeEligibility.canAttach) {
      this.markRouteCaptureRejected(routeEligibility.reason);
      if (this.hasClearedReleasePlane()) {
        this.pendingReleaseChargeRatio = null;
      }
      return;
    }

    const velocity = this.ballBody.linvel();
    const measuredSpeed = Math.hypot(velocity.x, velocity.y, velocity.z);
    const routeSpeed = Math.max(
      measuredSpeed,
      resolveLaunchSpeedFromCharge(this.launcher, chargeRatio),
    );

    this.activeTravelRoute = buildActiveTravelRoute(travelRoute, routeSpeed);
    this.boardHandoffArmed = false;
    this.pendingReleaseChargeRatio = null;
    this.markRouteCaptureAccepted();
    const startPoint = samplePointAlongTravelRoute(
      this.activeTravelRoute.route.path,
      this.activeTravelRoute.cumulativeDistances,
      this.activeTravelRoute.totalDistance,
      this.activeTravelRoute.distance,
    );
    this.ballBody.setTranslation(startPoint, true);
    this.ballBody.setLinvel({ x: 0, y: 0, z: 0 }, true);
  }

  private canAttachReleaseTravelRoute(route: TableLauncherTravelRoute3DDefinition): {
    canAttach: boolean;
    reason: RouteCaptureRejectReason;
  } {
    if (!this.ballBody) {
      return { canAttach: false, reason: "no_route" };
    }

    const entryMode = route.entryMode ?? "release";
    if (entryMode !== "release") {
      return { canAttach: false, reason: "no_route" };
    }

    const ballPosition = this.ballBody.translation();
    const routeStart = route.path[0];
    const routeEntryTolerance = this.ball.radius * RELEASE_ROUTE_ENTRY_TOLERANCE_MULTIPLIER;
    const xyDistance = Math.hypot(ballPosition.x - routeStart.x, ballPosition.y - routeStart.y);
    const zDistance = Math.abs(ballPosition.z - routeStart.z);
    if (xyDistance > routeEntryTolerance || zDistance > routeEntryTolerance) {
      if (xyDistance > routeEntryTolerance) {
        return { canAttach: false, reason: "distance_xy" };
      }
      return { canAttach: false, reason: "distance_z" };
    }

    if (this.ballBody.linvel().y > -RELEASE_ROUTE_ENTRY_MIN_UPWARD_SPEED) {
      return { canAttach: false, reason: "vy_gate" };
    }
    return { canAttach: true, reason: "no_route" };
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
    const handoffVelocity = this.activeTravelRoute.route.handoffVelocity;
    if (!handoffVelocity) {
      throw new Error(
        `Launcher travel route "${this.activeTravelRoute.route.tag}" is missing terminal handoff velocity.`,
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

  private resolveTravelRouteByTag(tag: string): TableLauncherTravelRoute3DDefinition {
    const route = this.launcher.threeD.travelRoutes?.find((candidate) => candidate.tag === tag);
    if (!route) {
      throw new Error(`Launcher travel route "${tag}" is not defined.`);
    }
    return route;
  }

  private markRouteCaptureAccepted(): void {
    this.lastRouteCaptureDecision = "accepted";
    this.lastRouteCaptureRejectReason = null;
  }

  private markRouteCaptureRejected(reason: RouteCaptureRejectReason): void {
    this.lastRouteCaptureDecision = "rejected";
    this.lastRouteCaptureRejectReason = reason;
  }

  private updateContactTelemetry(): void {
    if (!this.ballBody) {
      this.separationPx = null;
      this.overlapPx = 0;
      this.relativeVyAtContact = null;
      this.impulseTransferMarker = 0;
      if (this.plungerBallContactActive) {
        this.contactExitedThisStep = true;
      }
      this.plungerBallContactActive = false;
      return;
    }

    const ballPosition = this.ballBody.translation();
    const ballVelocity = this.ballBody.linvel();
    const plungerFrontFaceY = this.currentPlungerCenterY - this.launcher.threeD.plunger.depth / 2;
    const separation = plungerFrontFaceY - (ballPosition.y + this.ball.radius);
    const overlap = Math.max(-separation, 0);
    const contactActive = overlap > 0;
    this.separationPx = separation;
    this.overlapPx = Math.max(this.overlapPx, overlap);
    if (contactActive) {
      const relativeVyAtContact = ballVelocity.y - this.currentPlungerVelocityY;
      this.relativeVyAtContact = this.relativeVyAtContact === null
        ? relativeVyAtContact
        : Math.min(this.relativeVyAtContact, relativeVyAtContact);
    }
    this.impulseTransferMarker = clamp01(
      Math.max(this.overlapPx / Math.max(this.ball.radius, 1e-6), 0),
    );

    if (contactActive && !this.plungerBallContactActive) {
      this.contactEnteredThisStep = true;
    }
    if (!contactActive && this.plungerBallContactActive) {
      this.contactExitedThisStep = true;
    }
    this.plungerBallContactActive = contactActive;
    if (contactActive) {
      this.lastContactAtStep = this.stepCounter;
    }
  }

  private isInsideFeedSensor(): boolean {
    if (!this.ballBody) {
      return false;
    }
    const feedSensor = this.launcher.threeD.sensors.find((sensor) => sensor.semanticRole === "feed");
    if (!feedSensor) {
      return false;
    }
    const position = this.ballBody.translation();
    return isPointInTriggerShape({ x: position.x, y: position.y }, feedSensor.shape);
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

function resolveLaunchSpeedFromCharge(
  launcher: TableLauncherDefinition,
  chargeRatio: number,
): number {
  const plunger = launcher.threeD.plunger;
  const minimumLaunchSpeed = launcher.launchImpulseMin * plunger.momentumTransfer;
  const maximumLaunchSpeed = launcher.launchImpulseMax * plunger.momentumTransfer;
  return minimumLaunchSpeed + (maximumLaunchSpeed - minimumLaunchSpeed) * chargeRatio;
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

function clamp01(value: number): number {
  return Math.min(Math.max(value, 0), 1);
}
