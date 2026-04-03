/**
 * Rapier-backed physics world for Flunk-Out Frenzy prototype alpha.
 *
 * This module owns Rapier rigid bodies, colliders, sensor events, and the
 * compiled pinball-table plans that drive simulation. It emits stable semantic
 * machine events so rules never touch raw collider handles or engine-specific
 * details.
 */

import RAPIER3D from "@dimforge/rapier3d-compat";
import type { RuntimeCommand } from "../core/runtimeTypes";
import type {
  TableBodyPlan,
  TableColliderPlan,
  TableColliderShapePlan,
} from "../table/pinballTablePlanTypes";
import {
  PROTOTYPE_ALPHA_TABLE,
  type PrototypeAlphaTable,
} from "../table/prototypeAlphaTable";
import type {
  TableCaptureDeviceDefinition,
  TablePoint,
  TableSaveDeviceDefinition,
} from "../table/tableDefinitionTypes";
import type { ColliderMeta } from "./colliderMeta";
import {
  applyCaptureLifecycleStep,
  createCaptureDeviceTagIndex,
  createInitialCaptureLifecycleState,
  createSaveDeviceTagIndex,
  resetCaptureLifecycleState,
} from "./captureDeviceLifecycle";
import {
  applyFlipperContactImpulse,
  degreesToRadians,
  driveFlipperKinematic,
  radiansToDegrees,
} from "./flipperActuation";
import { collectMachineEvents } from "./machineEventEmitter";
import type {
  MachineEvent,
  PhysicsLaunchToDropPhase,
  PhysicsLaunchToDropTraceStep,
  PhysicsLauncherTelemetrySnapshot,
  PhysicsSnapshot,
} from "./physicsTypes";
import { LauncherChain3D } from "./launcherChain3d";
import {
  createInitialPlungerLaneState,
  isPointInLauncherLaneRegion,
  stepPlungerLaneState,
  type PlungerLaneBallSnapshot,
  type PlungerLaneState,
} from "./plungerLaneState";

const BOARD_COLLIDER_HALF_DEPTH = 24;

interface LauncherStateStep {
  machineEvents: MachineEvent[];
  chargeRatio: number | null;
  releaseChargeRatio: number | null;
}

export class PhysicsWorld {
  private world!: RAPIER3D.World;
  private eventQueue!: RAPIER3D.EventQueue;
  private launcherChain: LauncherChain3D | null = null;
  private ballBody: RAPIER3D.RigidBody | null = null;
  private ballColliderHandle: number | null = null;
  private leftFlipper!: RAPIER3D.RigidBody;
  private rightFlipper!: RAPIER3D.RigidBody;
  private leftFlipperAngleRad = 0;
  private rightFlipperAngleRad = 0;
  private leftPressed = false;
  private rightPressed = false;
  private launchPressed = false;
  private wasLeftPressed = false;
  private wasRightPressed = false;
  private plungerLaneState: PlungerLaneState = createInitialPlungerLaneState();
  private readonly cooldowns = new Map<string, number>();
  private readonly captureDevicesByTag: ReadonlyMap<string, TableCaptureDeviceDefinition>;
  private readonly saveDevicesByTag: ReadonlyMap<string, TableSaveDeviceDefinition>;
  private readonly colliderMetaByHandle = new Map<number, ColliderMeta>();
  private readonly captureLifecycleState = createInitialCaptureLifecycleState();
  private currentPlungerCenterY = 0;
  private traceStepIndex = 0;
  private lastStepDtMs = 0;
  private lastStepEvents: MachineEvent[] = [];
  private lastHandoffToBoardStep: number | null = null;
  private firstBoardCollisionStep: number | null = null;
  private boardCollisionStartedThisStep = false;

  static async create(table: PrototypeAlphaTable = PROTOTYPE_ALPHA_TABLE): Promise<PhysicsWorld> {
    await RAPIER3D.init();
    return new PhysicsWorld(table);
  }

  private constructor(private readonly table: PrototypeAlphaTable = PROTOTYPE_ALPHA_TABLE) {
    this.captureDevicesByTag = createCaptureDeviceTagIndex(this.table.captureDevices);
    this.saveDevicesByTag = createSaveDeviceTagIndex(this.table.saveDevices);
    this.reset();
  }
  reset(): void {
    this.launcherChain?.dispose();
    this.launcherChain = null;
    this.disposeWorld();

    this.world = new RAPIER3D.World({
      x: this.table.gravity.x,
      y: this.table.gravity.y,
      z: 0,
    });
    this.eventQueue = new RAPIER3D.EventQueue(true);

    this.leftPressed = false;
    this.rightPressed = false;
    this.launchPressed = false;
    this.wasLeftPressed = false;
    this.wasRightPressed = false;
    this.plungerLaneState = createInitialPlungerLaneState();
    this.cooldowns.clear();
    this.colliderMetaByHandle.clear();
    resetCaptureLifecycleState(this.captureLifecycleState);
    this.ballBody = null;
    this.ballColliderHandle = null;
    this.currentPlungerCenterY = this.table.launcher.threeD.plunger.center.y;
    this.traceStepIndex = 0;
    this.lastStepDtMs = 0;
    this.lastStepEvents = [];
    this.lastHandoffToBoardStep = null;
    this.firstBoardCollisionStep = null;
    this.boardCollisionStartedThisStep = false;
    this.leftFlipperAngleRad = degreesToRadians(this.table.flippers.left.restAngleDeg);
    this.rightFlipperAngleRad = degreesToRadians(this.table.flippers.right.restAngleDeg);
    this.launcherChain = new LauncherChain3D(this.table.launcher, this.table.ball);

    const bodyById = this.buildWorldFromPlan();
    this.leftFlipper = this.requireBody(bodyById, this.table.refs.flipperBodyIds.left);
    this.rightFlipper = this.requireBody(bodyById, this.table.refs.flipperBodyIds.right);
  }

  dispose(): void {
    this.launcherChain?.dispose();
    this.launcherChain = null;
    this.disposeWorld();
  }

  applyCommand(command: RuntimeCommand): void {
    if (command.type === "left-flip") {
      this.leftPressed = command.pressed;
      return;
    }

    if (command.type === "right-flip") {
      this.rightPressed = command.pressed;
      return;
    }

    this.launchPressed = command.pressed;
  }

  spawnBall(position?: TablePoint): void {
    this.removeBall();
    const spawn = this.resolveSpawn(position);
    const spawnPosition = position ?? spawn.position;
    if (
      this.launcherChain
      && isPointInLauncherLaneRegion(spawnPosition, this.table.launcher)
    ) {
      this.launcherChain.spawnBall(spawnPosition);
    } else {
      this.spawnBallInMainWorld(spawnPosition, spawn.launchVelocity);
    }
    this.plungerLaneState = createInitialPlungerLaneState();
    this.currentPlungerCenterY = this.table.launcher.threeD.plunger.center.y;
    this.traceStepIndex = 0;
    this.lastStepDtMs = 0;
    this.lastStepEvents = [];
    this.lastHandoffToBoardStep = null;
    this.firstBoardCollisionStep = null;
    this.boardCollisionStartedThisStep = false;
  }

  removeBall(): void {
    this.launcherChain?.removeBall();

    if (this.ballBody) {
      if (this.ballColliderHandle !== null) {
        this.colliderMetaByHandle.delete(this.ballColliderHandle);
      }
      this.world.removeRigidBody(this.ballBody);
      this.ballBody = null;
      this.ballColliderHandle = null;
    }

    this.plungerLaneState = createInitialPlungerLaneState();
    this.currentPlungerCenterY = this.table.launcher.threeD.plunger.center.y;
    resetCaptureLifecycleState(this.captureLifecycleState);
    this.lastStepEvents = [];
    this.boardCollisionStartedThisStep = false;
  }

  step(dtMs: number): MachineEvent[] {
    this.traceStepIndex += 1;
    this.lastStepDtMs = dtMs;
    this.lastStepEvents = [];
    this.boardCollisionStartedThisStep = false;
    const dtSeconds = dtMs / 1000;
    this.tickCooldowns(dtMs);
    this.updateFlippers(dtSeconds);
    this.tryTransferMainWorldBallToLauncherChain();
    const launcherStep = this.updateLauncherState(dtMs);
    const launcherPreStepEvents = [...launcherStep.machineEvents];
    let boardHandoffFromChain: { position: { x: number; y: number; z: number }; velocity: TablePoint } | null = null;

    if (this.launcherChain?.hasBall()) {
      const chainStep = this.launcherChain.step(
        dtMs,
        launcherStep.chargeRatio,
        launcherStep.releaseChargeRatio,
      );
      this.currentPlungerCenterY = this.launcherChain.currentPlungerSnapshot().y;
      launcherPreStepEvents.push(...chainStep.machineEvents);
      if (chainStep.releaseToBoard) {
        boardHandoffFromChain = chainStep.releaseToBoard;
      }
    }

    this.world.timestep = dtSeconds;
    this.world.step(this.eventQueue);

    const stepResult = collectMachineEvents({
      eventQueue: this.eventQueue,
      colliderMetaByHandle: this.colliderMetaByHandle,
      cooldowns: this.cooldowns,
      ballBody: this.ballBody,
      ballColliderHandle: this.ballColliderHandle,
      table: this.table,
    });
    this.boardCollisionStartedThisStep = stepResult.boardCollisionStarted;
    if (
      this.boardCollisionStartedThisStep
      && this.lastHandoffToBoardStep !== null
      && this.traceStepIndex > this.lastHandoffToBoardStep
      && this.firstBoardCollisionStep === null
    ) {
      this.firstBoardCollisionStep = this.traceStepIndex;
    }
    const captureLifecycleStep = applyCaptureLifecycleStep({
      state: this.captureLifecycleState,
      events: stepResult.events,
      dtMs,
      hasBall: this.ballBody !== null && !stepResult.shouldRemoveBall,
      captureDevicesByTag: this.captureDevicesByTag,
      saveDevicesByTag: this.saveDevicesByTag,
    });
    if (this.ballBody && !stepResult.shouldRemoveBall) {
      if (captureLifecycleStep.holdPosition) {
        const current = this.ballBody.translation();
        this.ballBody.setTranslation({
          x: captureLifecycleStep.holdPosition.x,
          y: captureLifecycleStep.holdPosition.y,
          z: current.z,
        }, true);
        this.ballBody.setLinvel({ x: 0, y: 0, z: 0 }, true);
        this.ballBody.setAngvel({ x: 0, y: 0, z: 0 }, true);
      }
      for (const impulse of captureLifecycleStep.impulses) {
        this.ballBody.applyImpulse({
          x: impulse.x,
          y: impulse.y,
          z: 0,
        }, true);
      }
    }
    if (stepResult.shouldRemoveBall) {
      this.removeBall();
    }
    if (boardHandoffFromChain) {
      this.spawnBallInMainWorld(
        boardHandoffFromChain.position,
        boardHandoffFromChain.velocity,
        boardHandoffFromChain.position.z,
      );
      this.lastHandoffToBoardStep = this.traceStepIndex;
    }
    this.wasLeftPressed = this.leftPressed;
    this.wasRightPressed = this.rightPressed;
    const machineEvents = [
      ...launcherPreStepEvents,
      ...captureLifecycleStep.forwardedEvents,
      ...captureLifecycleStep.postStepEvents,
    ];
    this.lastStepEvents = machineEvents;
    return machineEvents;
  }

  private spawnBallInMainWorld(
    position: TablePoint,
    launchVelocity?: TablePoint,
    spawnZ: number = this.table.ball.radius,
  ): void {
    const bodyDesc = RAPIER3D.RigidBodyDesc.dynamic()
      .setTranslation(position.x, position.y, spawnZ)
      .setLinearDamping(0.06)
      .setAngularDamping(0.14)
      .setCanSleep(false)
      .setCcdEnabled(true)
      .enabledTranslations(true, true, false)
      .enabledRotations(false, false, true);

    this.ballBody = this.world.createRigidBody(bodyDesc);
    const ballCollider = this.world.createCollider(
      RAPIER3D.ColliderDesc.ball(this.table.ball.radius)
        .setMass(this.table.ball.mass)
        .setRestitution(0.55)
        .setFriction(0.18)
        .setActiveEvents(RAPIER3D.ActiveEvents.COLLISION_EVENTS),
      this.ballBody,
    );

    this.ballColliderHandle = ballCollider.handle;
    this.colliderMetaByHandle.set(ballCollider.handle, {
      kind: "ball",
      tag: "ball/main",
    });
    if (launchVelocity) {
      this.ballBody.setLinvel(
        {
          x: launchVelocity.x,
          y: launchVelocity.y,
          z: 0,
        },
        true,
      );
    }
  }

  currentSnapshot(): PhysicsSnapshot {
    const leftDef = this.table.flippers.left;
    const rightDef = this.table.flippers.right;
    const launcherPlunger = this.launcherChain?.currentPlungerSnapshot();
    const chainBall = this.launcherChain?.currentSnapshot() ?? null;
    const chainTelemetry = this.launcherChain?.currentTelemetrySnapshot() ?? null;
    const boardBall = this.ballBody
      ? {
          x: this.ballBody.translation().x,
          y: this.ballBody.translation().y,
          radius: this.table.ball.radius,
        }
      : null;
    const activeBall = boardBall ?? (chainBall
      ? {
          x: chainBall.position.x,
          y: chainBall.position.y,
          radius: this.table.ball.radius,
        }
      : null);
    const boardVelocity = this.ballBody?.linvel() ?? null;
    const launcherChargeRatio = this.plungerLaneState.phase === "charging"
      ? (this.table.launcher.chargeMsMax > 0
        ? Math.min(this.plungerLaneState.chargeMs / this.table.launcher.chargeMsMax, 1)
        : 1)
      : null;
    const launcherTelemetry = chainTelemetry
      ? (() => {
          const ballOwner: "main_world" | "launcher_chain" | "none" = boardBall
            ? "main_world"
            : (chainBall ? "launcher_chain" : "none");
          return {
          ...chainTelemetry,
          plunger: {
            ...chainTelemetry.plunger,
            chargeRatio: launcherChargeRatio,
            phase: this.plungerLaneState.phase,
          },
          ball: {
            owner: ballOwner,
            position: boardBall
              ? {
                  x: boardBall.x,
                  y: boardBall.y,
                  z: this.table.ball.radius,
                }
              : chainTelemetry.ball.position,
            velocity: boardVelocity
              ? {
                  x: boardVelocity.x,
                  y: boardVelocity.y,
                  z: boardVelocity.z,
                }
              : chainTelemetry.ball.velocity,
          },
        };
      })()
      : null;

    return {
      ball: activeBall,
      plunger: {
        x: launcherPlunger?.x ?? this.table.launcher.threeD.plunger.center.x,
        y: launcherPlunger?.y ?? this.currentPlungerCenterY,
        width: launcherPlunger?.width ?? this.table.launcher.threeD.plunger.width,
        height: launcherPlunger?.height ?? this.table.launcher.threeD.plunger.depth,
      },
      flippers: {
        left: {
          side: "left",
          pivotX: leftDef.pivot.x,
          pivotY: leftDef.pivot.y,
          length: leftDef.length,
          thickness: leftDef.thickness,
          angleDeg: radiansToDegrees(this.leftFlipperAngleRad),
        },
        right: {
          side: "right",
          pivotX: rightDef.pivot.x,
          pivotY: rightDef.pivot.y,
          length: rightDef.length,
          thickness: rightDef.thickness,
          angleDeg: radiansToDegrees(this.rightFlipperAngleRad),
        },
      },
      launcherTelemetry,
      launchTraceStep: this.buildLaunchToDropTraceStep(launcherTelemetry),
    };
  }

  private buildWorldFromPlan(): Map<string, RAPIER3D.RigidBody> {
    const bodyById = new Map<string, RAPIER3D.RigidBody>();

    for (const bodyPlan of this.table.physics.bodies) {
      const rigidBody = this.world.createRigidBody(this.createRigidBodyDesc(bodyPlan));
      bodyById.set(bodyPlan.id, rigidBody);
    }

    for (const colliderPlan of this.table.physics.colliders) {
      const parentBody = this.requireBody(bodyById, colliderPlan.bodyId);
      const collider = this.world.createCollider(
        this.createColliderDesc(colliderPlan),
        parentBody,
      );
      const meta = this.resolveColliderMeta(colliderPlan);
      if (meta) {
        this.colliderMetaByHandle.set(collider.handle, meta);
      }
    }

    return bodyById;
  }

  private createRigidBodyDesc(plan: TableBodyPlan): RAPIER3D.RigidBodyDesc {
    const desc =
      plan.type === "fixed"
        ? RAPIER3D.RigidBodyDesc.fixed()
        : RAPIER3D.RigidBodyDesc.kinematicPositionBased();

    return desc
      .setTranslation(plan.translation.x, plan.translation.y, 0)
      .setRotation(quaternionFromYaw(plan.rotationRad));
  }

  private createColliderDesc(plan: TableColliderPlan): RAPIER3D.ColliderDesc {
    const desc = this.createShapeDesc(plan.shape);
    const surface = this.table.surfaces[plan.surfaceId] ?? this.table.surfaces.wall;

    desc
      .setTranslation(plan.translation.x, plan.translation.y, 0)
      .setRotation(quaternionFromYaw(plan.rotationRad))
      .setRestitution(surface.restitution)
      .setFriction(surface.friction);

    if (plan.sensor) {
      desc
        .setSensor(true)
        .setActiveEvents(RAPIER3D.ActiveEvents.COLLISION_EVENTS);
    }

    return desc;
  }

  private createShapeDesc(shape: TableColliderShapePlan): RAPIER3D.ColliderDesc {
    switch (shape.kind) {
      case "thick-segment":
        return createRoundedThickSegmentColliderDesc(shape.halfLength, shape.radius);
      case "circle":
        return RAPIER3D.ColliderDesc.ball(shape.radius);
      case "cuboid":
        return RAPIER3D.ColliderDesc.cuboid(
          shape.halfExtents.x,
          shape.halfExtents.y,
          BOARD_COLLIDER_HALF_DEPTH,
        );
      case "convex-polygon":
        return createConvexPolygonColliderDesc(shape.vertices);
      case "triangle":
        return createConvexPolygonColliderDesc(shape.vertices);
    }
  }

  private resolveColliderMeta(plan: TableColliderPlan): ColliderMeta | null {
    if (!plan.sensor || !plan.semanticKind || !plan.tag) {
      return null;
    }

    switch (plan.semanticKind) {
      case "bumper":
        if (!plan.center || plan.impulseMagnitude === undefined) {
          throw new Error(`Bumper collider "${plan.id}" is missing compiled impulse data.`);
        }
        return {
          kind: "bumper",
          tag: plan.tag,
          center: plan.center,
          impulse: plan.impulseMagnitude,
        };
      case "sling":
        if (!plan.impulse || !plan.side) {
          throw new Error(`Sling collider "${plan.id}" is missing compiled sling data.`);
        }
        return {
          kind: "sling",
          tag: plan.tag,
          side: plan.side,
          impulse: plan.impulse,
        };
      case "rollover":
        return { kind: "rollover", tag: plan.tag };
      case "tripwire":
        return {
          kind: "tripwire",
          tag: plan.tag,
          triggerPhase: plan.trigger?.phase ?? "enter",
          triggerShapeKind: plan.trigger?.shape.kind ?? "rect",
        };
      case "gate":
        return {
          kind: "gate",
          tag: plan.tag,
          triggerPhase: plan.trigger?.phase ?? "enter",
          triggerShapeKind: plan.trigger?.shape.kind ?? "rect",
        };
      case "standup-target":
        return { kind: "standup-target", tag: plan.tag };
      case "popup-target":
        return { kind: "popup-target", tag: plan.tag };
      case "drain":
        return { kind: "drain", tag: plan.tag };
      case "capture":
        if (!plan.captureDeviceKind) {
          throw new Error(`Capture collider "${plan.id}" is missing compiled device kind.`);
        }
        return {
          kind: "capture",
          tag: plan.tag,
          deviceKind: plan.captureDeviceKind,
        };
      case "save":
        if (!plan.saveDeviceKind) {
          throw new Error(`Save collider "${plan.id}" is missing compiled device kind.`);
        }
        return {
          kind: "save",
          tag: plan.tag,
          deviceKind: plan.saveDeviceKind,
        };
    }
  }

  private requireBody(
    bodyById: ReadonlyMap<string, RAPIER3D.RigidBody>,
    bodyId: string,
  ): RAPIER3D.RigidBody {
    const body = bodyById.get(bodyId);
    if (!body) {
      throw new Error(`Missing rigid body "${bodyId}" in compiled physics plan.`);
    }

    return body;
  }

  private resolveSpawn(position: TablePoint | undefined) {
    if (position) {
      return {
        position,
        launchVelocity: undefined,
      };
    }

    return this.table.physics.spawns[0] ?? { position: this.table.ball.spawn };
  }

  private updateFlippers(dtSeconds: number): void {
    this.leftFlipperAngleRad = driveFlipperKinematic(
      this.leftFlipper,
      this.table.flippers.left,
      this.leftPressed,
      dtSeconds,
      this.leftFlipperAngleRad,
    );
    this.rightFlipperAngleRad = driveFlipperKinematic(
      this.rightFlipper,
      this.table.flippers.right,
      this.rightPressed,
      dtSeconds,
      this.rightFlipperAngleRad,
    );

    if (this.leftPressed && !this.wasLeftPressed) {
      this.applyFlipperContact(this.table.flippers.left, this.leftFlipperAngleRad);
    }
    if (this.rightPressed && !this.wasRightPressed) {
      this.applyFlipperContact(this.table.flippers.right, this.rightFlipperAngleRad);
    }
  }

  private applyFlipperContact(
    flipper: PrototypeAlphaTable["flippers"]["left"],
    angleRad: number,
  ): void {
    if (!this.ballBody) {
      return;
    }

    applyFlipperContactImpulse({
      ballBody: this.ballBody,
      ball: {
        x: this.ballBody.translation().x,
        y: this.ballBody.translation().y,
        radius: this.table.ball.radius,
      },
      flipper,
      angleRad,
    });
  }

  private updateLauncherState(dtMs: number): LauncherStateStep {
    const result = stepPlungerLaneState({
      state: this.plungerLaneState,
      ball: this.currentPlungerBallSnapshot(),
      launchPressed: this.launchPressed,
      launcher: this.table.launcher,
      dtMs,
    });
    this.plungerLaneState = result.nextState;
    if (!this.launcherChain?.hasBall()) {
      this.syncPlunger(dtMs, result.chargeRatio);
    }

    return {
      machineEvents: [...result.machineEvents],
      chargeRatio: result.chargeRatio,
      releaseChargeRatio: result.releaseChargeRatio,
    };
  }

  private currentPlungerBallSnapshot(): PlungerLaneBallSnapshot | null {
    const launcherBall = this.launcherChain?.currentSnapshot();
    if (launcherBall) {
      return {
        position: launcherBall.position,
        velocity: launcherBall.velocity,
      };
    }
    return null;
  }

  private syncPlunger(dtMs: number, chargeRatio: number | null): void {
    const plunger = this.table.launcher.threeD.plunger;
    const dtSeconds = dtMs / 1000;
    const targetCenterY = chargeRatio !== null
      ? plunger.center.y + plunger.stroke * chargeRatio
      : plunger.center.y;
    const maxTravel = chargeRatio !== null
      ? plunger.speedPull * dtMs
      : plunger.speedFire * dtSeconds;
    const delta = targetCenterY - this.currentPlungerCenterY;
    const travel = Math.abs(delta) <= maxTravel
      ? delta
      : Math.sign(delta) * maxTravel;
    this.currentPlungerCenterY += travel;
  }

  private tickCooldowns(dtMs: number): void {
    for (const [tag, remainingMs] of [...this.cooldowns.entries()]) {
      const nextRemaining = remainingMs - dtMs;
      if (nextRemaining <= 0) {
        this.cooldowns.delete(tag);
        continue;
      }
      this.cooldowns.set(tag, nextRemaining);
    }
  }

  private disposeWorld(): void {
    this.eventQueue?.free();
    this.world?.free();
  }

  private tryTransferMainWorldBallToLauncherChain(): void {
    if (!this.ballBody || !this.launcherChain || this.launcherChain.hasBall()) {
      return;
    }

    const translation = this.ballBody.translation();
    const position = {
      x: translation.x,
      y: translation.y,
    };
    if (!isPointInLauncherLaneRegion(position, this.table.launcher)) {
      return;
    }

    const velocity = this.ballBody.linvel();
    const speed = Math.hypot(velocity.x, velocity.y);
    if (speed > this.table.launcher.feedSettledSpeedMax) {
      return;
    }

    this.removeMainWorldBall();
    this.launcherChain.spawnBall(position);
  }

  private removeMainWorldBall(): void {
    if (!this.ballBody) {
      return;
    }

    if (this.ballColliderHandle !== null) {
      this.colliderMetaByHandle.delete(this.ballColliderHandle);
    }
    this.world.removeRigidBody(this.ballBody);
    this.ballBody = null;
    this.ballColliderHandle = null;
    resetCaptureLifecycleState(this.captureLifecycleState);
  }

  private buildLaunchToDropTraceStep(
    launcherTelemetry: PhysicsLauncherTelemetrySnapshot | null,
  ): PhysicsLaunchToDropTraceStep | null {
    if (!launcherTelemetry) {
      return null;
    }

    return {
      stepIndex: this.traceStepIndex,
      dtMs: this.lastStepDtMs,
      phase: this.resolveLaunchToDropPhase(launcherTelemetry),
      ballOwner: launcherTelemetry.ball.owner,
      ballPosition: launcherTelemetry.ball.position,
      ballVelocity: launcherTelemetry.ball.velocity,
      plunger: launcherTelemetry.plunger,
      route: launcherTelemetry.route,
      routeCapture: launcherTelemetry.routeCapture,
      sensors: launcherTelemetry.sensors,
      contact: launcherTelemetry.contact,
      seamTransition: launcherTelemetry.seamTransition,
      events: [...this.lastStepEvents],
      handoffToBoardStep: this.lastHandoffToBoardStep,
      firstBoardCollisionStep: this.firstBoardCollisionStep,
      boardCollisionStartedThisStep: this.boardCollisionStartedThisStep,
    };
  }

  private resolveLaunchToDropPhase(
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
      if (this.lastHandoffToBoardStep !== null && this.traceStepIndex === this.lastHandoffToBoardStep) {
        return "handoff_to_board";
      }
      if (this.firstBoardCollisionStep !== null && this.traceStepIndex > this.firstBoardCollisionStep) {
        return "board_drop_postimpact";
      }
      return "board_drop_preimpact";
    }

    if (launcherTelemetry.plunger.phase === "charging") {
      return "charge_pull";
    }
    if (
      launcherTelemetry.plunger.phase === "released"
      && launcherTelemetry.ball.owner === "launcher_chain"
    ) {
      return "release_strike_window";
    }

    return "feed_rest";
  }
}

function createConvexPolygonColliderDesc(vertices: readonly TablePoint[]): RAPIER3D.ColliderDesc {
  const flatVertices = new Float32Array(
    vertices.flatMap((vertex) => [
      vertex.x,
      vertex.y,
      -BOARD_COLLIDER_HALF_DEPTH,
      vertex.x,
      vertex.y,
      BOARD_COLLIDER_HALF_DEPTH,
    ]),
  );
  const colliderDesc = RAPIER3D.ColliderDesc.convexHull(flatVertices);

  if (!colliderDesc) {
    throw new Error("Failed to compile convex polygon collider from authored donor vertices.");
  }

  return colliderDesc;
}

function quaternionFromYaw(angleRad: number): RAPIER3D.Rotation {
  return {
    x: 0,
    y: 0,
    z: Math.sin(angleRad / 2),
    w: Math.cos(angleRad / 2),
  };
}

function createRoundedThickSegmentColliderDesc(
  halfLength: number,
  radius: number,
): RAPIER3D.ColliderDesc {
  const borderRadius = Math.max(
    0,
    Math.min(radius, halfLength, BOARD_COLLIDER_HALF_DEPTH) - 1e-4,
  );
  if (borderRadius <= 0) {
    return RAPIER3D.ColliderDesc.cuboid(halfLength, radius, BOARD_COLLIDER_HALF_DEPTH);
  }

  return RAPIER3D.ColliderDesc.roundCuboid(
    Math.max(halfLength - borderRadius, 1e-4),
    Math.max(radius - borderRadius, 1e-4),
    Math.max(BOARD_COLLIDER_HALF_DEPTH - borderRadius, 1e-4),
    borderRadius,
  );
}
