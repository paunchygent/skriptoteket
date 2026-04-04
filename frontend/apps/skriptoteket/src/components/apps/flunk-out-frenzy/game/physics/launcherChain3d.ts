/**
 * Dedicated Rapier 3D launcher-chain seam for Flunk-Out Frenzy.
 *
 * This module owns only the donor-backed shooter lane, plunger, and immediate
 * right-side receiving handoff.
 */

import RAPIER3D from "@dimforge/rapier3d-compat";

import type {
  MachineEvent,
  PhysicsLauncherTelemetrySnapshot,
} from "./physicsTypes";
import type {
  TableBallDefinition,
  TableLauncherDefinition,
  TablePoint,
  TablePoint3D,
} from "../table/tableDefinitionTypes";

// Sub-modules
import type { LauncherContext } from "./launcher/LauncherContext";
import { updateContactTelemetry } from "./launcher/LauncherContactTelemetry";
import {
  advanceTravelRoute,
  buildActiveTravelRoute,
  resolveObservedTravelRouteProgressSpeed,
  resolveTravelRoute,
  resolveTravelRouteVelocity,
  samplePointAlongTravelRoute,
} from "./launcher/LauncherTravelRoute";
import {
  computeReleaseIntegrationWindowMs,
  resolveReleaseStrikeTargetY,
} from "./launcher/LauncherReleaseIntegration";
import {
  canAttachReleaseTravelRoute,
  currentBallPosition,
  didCrossExitSensorDuringStep,
  hasClearedReleasePlane,
  isExitCrossingUpward,
  isInsideExitSensor,
  isInsideFeedSensor,
  type RouteCaptureRejectReason,
} from "./launcher/LauncherSensors";
import {
  createLauncherPlungerBody,
  createLauncherWorldFloor,
  createLauncherWorldWalls,
  resolveReleasePlaneY,
} from "./launcher/LauncherWorldGeometry";
import { buildLauncherTelemetrySnapshot } from "./launcher/LauncherTelemetrySnapshot";

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

const RELEASE_ROUTE_ENTRY_TOLERANCE_MULTIPLIER = 1.5;
const RELEASE_ROUTE_ENTRY_MIN_UPWARD_SPEED = 1;
const RELEASE_ROUTE_CAPTURE_WINDOW_MS = 2200;
const STRIKE_READY_REST_GAP_PX = 1;
const RELEASE_INTEGRATION_SUBSTEP_MS = 4;

type MutableLauncherContext = {
  -readonly [K in keyof LauncherContext]: LauncherContext[K];
};

export class LauncherChain3D {
  private readonly ctx: LauncherContext;

  constructor(
    launcher: TableLauncherDefinition,
    ball: TableBallDefinition,
  ) {
    const world = new RAPIER3D.World({ x: 0, y: 0, z: -981 });
    const parkCenter = launcher.threeD.plunger.center;

    this.ctx = {
      world,
      launcher,
      ball,
      plungerBody: null as unknown as RAPIER3D.RigidBody,
      ballBody: null,
      parkCenter,
      releasePlaneY: resolveReleasePlaneY(launcher),
      currentPlungerCenterY: parkCenter.y,
      currentPlungerVelocityY: 0,
      currentPlungerTargetY: parkCenter.y,
      exitInside: false,
      feedInside: false,
      boardHandoffArmed: false,
      activeTravelRoute: null,
      pendingReleaseChargeRatio: null,
      pendingReleaseNeedsSw16Exit: false,
      routeCaptureWindowMsRemaining: 0,
      stepCounter: 0,
      lastSw16ExitStep: null,
      lastRouteCaptureDecision: "none",
      lastRouteCaptureRejectReason: null,
      plungerBallContactActive: false,
      contactEnteredThisStep: false,
      contactExitedThisStep: false,
      separationPx: null,
      overlapPx: 0,
      relativeVyAtContact: null,
      lastContactAtStep: null,
      impulseTransferMarker: 0,
      releaseIntegrationWindowMsRemaining: 0,
      seamTransition: null,
    };

    createLauncherWorldFloor(this.ctx.world);
    createLauncherWorldWalls(this.ctx.world, this.ctx.launcher);
    (this.ctx as MutableLauncherContext).plungerBody = createLauncherPlungerBody(this.ctx);
  }

  dispose(): void {
    this.ctx.world.free();
  }

  hasBall(): boolean {
    return this.ctx.ballBody !== null;
  }

  spawnBall(position: TablePoint): void {
    this.removeBall();
    const strikeReadyPosition = this.resolveStrikeReadySpawnPosition(position);

    const body = this.ctx.world.createRigidBody(
      RAPIER3D.RigidBodyDesc.dynamic()
        .setTranslation(
          strikeReadyPosition.x,
          strikeReadyPosition.y,
          this.ctx.launcher.threeD.ballRestZ,
        )
        .setCanSleep(false)
        .setLinearDamping(0.08)
        .setAngularDamping(0.08)
        .setCcdEnabled(true),
    );
    this.ctx.world.createCollider(
      RAPIER3D.ColliderDesc.ball(this.ctx.ball.radius)
        .setMass(this.ctx.ball.mass)
        .setRestitution(0.25)
        .setFriction(0.16),
      body,
    );

    this.ctx.ballBody = body;
    this.ctx.ballBody.setLinvel({ x: 0, y: 0, z: 0 }, true);
    this.ctx.ballBody.setAngvel({ x: 0, y: 0, z: 0 }, true);
    this.ctx.stepCounter = 0;
    this.ctx.feedInside = isInsideFeedSensor(this.ctx);
    this.ctx.exitInside = isInsideExitSensor(this.ctx);
    this.ctx.lastSw16ExitStep = null;
    this.ctx.boardHandoffArmed = false;
    this.ctx.activeTravelRoute = null;
    this.ctx.pendingReleaseChargeRatio = null;
    this.ctx.pendingReleaseNeedsSw16Exit = false;
    this.ctx.routeCaptureWindowMsRemaining = 0;
    this.ctx.lastRouteCaptureDecision = "none";
    this.ctx.lastRouteCaptureRejectReason = null;
    this.ctx.plungerBallContactActive = false;
    this.ctx.contactEnteredThisStep = false;
    this.ctx.contactExitedThisStep = false;
    this.ctx.separationPx = null;
    this.ctx.overlapPx = 0;
    this.ctx.relativeVyAtContact = null;
    this.ctx.lastContactAtStep = null;
    this.ctx.impulseTransferMarker = 0;
    this.ctx.releaseIntegrationWindowMsRemaining = 0;
    this.ctx.seamTransition = null;
  }

  removeBall(): void {
    if (!this.ctx.ballBody) {
      return;
    }

    this.ctx.world.removeRigidBody(this.ctx.ballBody);
    this.ctx.ballBody = null;
    this.ctx.exitInside = false;
    this.ctx.boardHandoffArmed = false;
    this.ctx.activeTravelRoute = null;
    this.ctx.pendingReleaseChargeRatio = null;
    this.ctx.pendingReleaseNeedsSw16Exit = false;
    this.ctx.routeCaptureWindowMsRemaining = 0;
    this.ctx.feedInside = false;
    this.ctx.stepCounter = 0;
    this.ctx.currentPlungerTargetY = this.ctx.parkCenter.y;
    this.ctx.currentPlungerVelocityY = 0;
    this.ctx.plungerBallContactActive = false;
    this.ctx.contactEnteredThisStep = false;
    this.ctx.contactExitedThisStep = false;
    this.ctx.separationPx = null;
    this.ctx.overlapPx = 0;
    this.ctx.relativeVyAtContact = null;
    this.ctx.lastContactAtStep = null;
    this.ctx.impulseTransferMarker = 0;
    this.ctx.releaseIntegrationWindowMsRemaining = 0;
    this.ctx.seamTransition = null;
  }

  currentSnapshot(): LauncherChainBallSnapshot | null {
    if (!this.ctx.ballBody) {
      return null;
    }

    const translation = this.ctx.ballBody.translation();
    const velocity = this.ctx.ballBody.linvel();
    return {
      position: { x: translation.x, y: translation.y, z: translation.z },
      velocity: { x: velocity.x, y: velocity.y },
    };
  }

  currentPlungerSnapshot(): LauncherChainPlungerSnapshot {
    const plunger = this.ctx.launcher.threeD.plunger;
    return {
      x: this.ctx.parkCenter.x,
      y: this.ctx.currentPlungerCenterY,
      width: plunger.width,
      height: plunger.depth,
    };
  }

  currentTelemetrySnapshot(): PhysicsLauncherTelemetrySnapshot {
    return buildLauncherTelemetrySnapshot(this.ctx);
  }

  step(
    dtMs: number,
    chargeRatio: number | null,
    releaseChargeRatio: number | null,
  ): LauncherChainStepResult {
    if (!this.ctx.ballBody) {
      return { releaseToBoard: null, machineEvents: [] };
    }

    const machineEvents: MachineEvent[] = [];
    this.ctx.stepCounter += 1;
    this.ctx.contactEnteredThisStep = false;
    this.ctx.contactExitedThisStep = false;
    this.ctx.overlapPx = 0;
    this.ctx.relativeVyAtContact = null;
    this.ctx.impulseTransferMarker = 0;
    this.ctx.seamTransition = null;

    if (releaseChargeRatio !== null) {
      this.ctx.pendingReleaseChargeRatio = releaseChargeRatio;
      this.ctx.pendingReleaseNeedsSw16Exit = true;
      this.ctx.boardHandoffArmed = false;
      this.ctx.routeCaptureWindowMsRemaining = RELEASE_ROUTE_CAPTURE_WINDOW_MS;
      this.ctx.lastRouteCaptureDecision = "none";
      this.ctx.lastRouteCaptureRejectReason = null;
      this.ctx.releaseIntegrationWindowMsRemaining = computeReleaseIntegrationWindowMs(this.ctx);
    }

    const preIntegrationPosition = currentBallPosition(this.ctx);
    this.stepWorldWithReleaseIntegration(dtMs, chargeRatio);
    const postIntegrationPosition = currentBallPosition(this.ctx);

    this.ctx.feedInside = isInsideFeedSensor(this.ctx);
    const wasInsideExit = this.ctx.exitInside;
    const isInsideExit = isInsideExitSensor(this.ctx);
    const hasSweptExitCrossing = didCrossExitSensorDuringStep(
      this.ctx,
      preIntegrationPosition,
      postIntegrationPosition,
    );
    const shouldEmitExit = isExitCrossingUpward(
      this.ctx,
      preIntegrationPosition,
      postIntegrationPosition,
      RELEASE_ROUTE_ENTRY_MIN_UPWARD_SPEED,
    ) && (
      (wasInsideExit && !isInsideExit)
      || (!wasInsideExit && !isInsideExit && hasSweptExitCrossing)
    );
    this.ctx.exitInside = isInsideExit;

    if (shouldEmitExit) {
      machineEvents.push({ type: "gate-passed", tag: "gate/launch-lane-exit" });
      this.ctx.boardHandoffArmed = true;
      this.ctx.lastSw16ExitStep = this.ctx.stepCounter;
      this.ctx.pendingReleaseNeedsSw16Exit = false;
    }

    this.tryEnterReleaseTravelRoute();
    if (this.ctx.pendingReleaseChargeRatio !== null && !this.ctx.activeTravelRoute) {
      this.ctx.routeCaptureWindowMsRemaining = Math.max(
        this.ctx.routeCaptureWindowMsRemaining - dtMs,
        0,
      );
      if (this.ctx.routeCaptureWindowMsRemaining === 0) {
        this.ctx.pendingReleaseChargeRatio = null;
        this.ctx.pendingReleaseNeedsSw16Exit = false;
        this.markRouteCaptureRejected("window_expired");
      }
    }

    const routeHandoff = this.ctx.activeTravelRoute ? advanceTravelRoute(this.ctx, dtMs) : null;
    if (this.ctx.activeTravelRoute) {
      this.ctx.boardHandoffArmed = false;
    }

    if (this.ctx.boardHandoffArmed && !this.ctx.activeTravelRoute && hasClearedReleasePlane(this.ctx)) {
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
    const plungerFrontFaceY = this.ctx.parkCenter.y - this.ctx.launcher.threeD.plunger.depth / 2;
    const desiredBallY = plungerFrontFaceY - this.ctx.ball.radius - STRIKE_READY_REST_GAP_PX;
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
      const stepMs = this.ctx.releaseIntegrationWindowMsRemaining > 0
        ? Math.min(RELEASE_INTEGRATION_SUBSTEP_MS, remainingMs)
        : remainingMs;
      this.syncPlunger(stepMs, chargeRatio);
      this.ctx.world.timestep = stepMs / 1000;
      this.ctx.world.step();
      updateContactTelemetry(this.ctx);
      remainingMs -= stepMs;
    }
    this.ctx.releaseIntegrationWindowMsRemaining = Math.max(
      this.ctx.releaseIntegrationWindowMsRemaining - dtMs,
      0,
    );
  }

  private syncPlunger(dtMs: number, chargeRatio: number | null): void {
    const plunger = this.ctx.launcher.threeD.plunger;
    const dtSeconds = dtMs / 1000;
    const releaseStrikeTargetY = resolveReleaseStrikeTargetY(this.ctx);
    const targetCenterY = chargeRatio !== null
      ? this.ctx.parkCenter.y + plunger.stroke * chargeRatio
      : (this.ctx.releaseIntegrationWindowMsRemaining > 0
        ? releaseStrikeTargetY
        : this.ctx.parkCenter.y);
    this.ctx.currentPlungerTargetY = targetCenterY;

    const maxTravel = chargeRatio !== null
      ? plunger.speedPull * dtMs
      : plunger.speedFire * dtSeconds;
    const delta = targetCenterY - this.ctx.currentPlungerCenterY;
    const travel = Math.abs(delta) <= maxTravel
      ? delta
      : Math.sign(delta) * maxTravel;
    this.ctx.currentPlungerCenterY += travel;
    this.ctx.currentPlungerVelocityY = dtSeconds > 0 ? travel / dtSeconds : 0;

    this.ctx.plungerBody.setNextKinematicTranslation({
      x: this.ctx.parkCenter.x,
      y: this.ctx.currentPlungerCenterY,
      z: this.ctx.parkCenter.z,
    });
  }

  private tryEnterReleaseTravelRoute(): void {
    if (!this.ctx.ballBody) {
      return;
    }

    if (this.ctx.activeTravelRoute || this.ctx.pendingReleaseChargeRatio === null) {
      return;
    }
    if (this.ctx.routeCaptureWindowMsRemaining <= 0) {
      this.ctx.pendingReleaseChargeRatio = null;
      return;
    }

    const chargeRatio = this.ctx.pendingReleaseChargeRatio;
    const travelRoute = resolveTravelRoute(this.ctx, chargeRatio);
    if (!travelRoute) {
      this.ctx.pendingReleaseChargeRatio = null;
      this.ctx.pendingReleaseNeedsSw16Exit = false;
       this.markRouteCaptureRejected("no_route");
      return;
    }

    const routeEligibility = canAttachReleaseTravelRoute(
      this.ctx,
      travelRoute,
      RELEASE_ROUTE_ENTRY_TOLERANCE_MULTIPLIER,
      RELEASE_ROUTE_ENTRY_MIN_UPWARD_SPEED,
    );
    if (!routeEligibility.canAttach) {
      this.markRouteCaptureRejected(routeEligibility.reason);
      if (hasClearedReleasePlane(this.ctx)) {
        this.ctx.pendingReleaseChargeRatio = null;
      }
      return;
    }

    const velocity = this.ctx.ballBody.linvel();
    const routeSpeed = resolveObservedTravelRouteProgressSpeed(travelRoute, velocity);
    if (routeSpeed <= 0) {
      this.markRouteCaptureRejected("vy_gate");
      if (hasClearedReleasePlane(this.ctx)) {
        this.ctx.pendingReleaseChargeRatio = null;
      }
      return;
    }

    this.ctx.activeTravelRoute = buildActiveTravelRoute(travelRoute, routeSpeed);
    this.ctx.boardHandoffArmed = false;
    this.ctx.pendingReleaseChargeRatio = null;
    this.ctx.pendingReleaseNeedsSw16Exit = false;
    this.markRouteCaptureAccepted();
    const startPoint = samplePointAlongTravelRoute(
      this.ctx.activeTravelRoute.route.path,
      this.ctx.activeTravelRoute.cumulativeDistances,
      this.ctx.activeTravelRoute.totalDistance,
      this.ctx.activeTravelRoute.distance,
    );
    const startVelocity = resolveTravelRouteVelocity(
      this.ctx.activeTravelRoute.route.path,
      this.ctx.activeTravelRoute.cumulativeDistances,
      this.ctx.activeTravelRoute.totalDistance,
      this.ctx.activeTravelRoute.distance,
      this.ctx.activeTravelRoute.speed,
    );
    this.ctx.ballBody.setTranslation(startPoint, true);
    this.ctx.ballBody.setLinvel(startVelocity, true);
  }

  private markRouteCaptureAccepted(): void {
    this.ctx.lastRouteCaptureDecision = "accepted";
    this.ctx.lastRouteCaptureRejectReason = null;
  }

  private markRouteCaptureRejected(reason: RouteCaptureRejectReason): void {
    this.ctx.lastRouteCaptureDecision = "rejected";
    this.ctx.lastRouteCaptureRejectReason = reason;
  }
}
