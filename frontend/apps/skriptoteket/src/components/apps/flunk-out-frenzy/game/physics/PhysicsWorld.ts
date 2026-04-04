/**
 * Rapier-backed physics world for Flunk-Out Frenzy prototype alpha.
 */

import RAPIER3D from "@dimforge/rapier3d-compat";
import type { RuntimeCommand } from "../core/runtimeTypes";
import {
  PROTOTYPE_ALPHA_TABLE,
  type PrototypeAlphaTable,
} from "../table/prototypeAlphaTable";
import type { TablePoint } from "../table/tableDefinitionTypes";
import type { ColliderMeta } from "./colliderMeta";
import {
  applyCaptureLifecycleStep,
  createCaptureDeviceTagIndex,
  createInitialCaptureLifecycleState,
  createSaveDeviceTagIndex,
  resetCaptureLifecycleState,
} from "./captureDeviceLifecycle";
import {
  degreesToRadians,
  radiansToDegrees,
} from "./flipperActuation";
import { collectMachineEvents } from "./machineEventEmitter";
import type {
  MachineEvent,
  PhysicsSnapshot,
} from "./physicsTypes";
import { LauncherChain3D } from "./launcherChain3d";
import {
  createInitialPlungerLaneState,
  isPointInLauncherLaneRegion,
} from "./plungerLaneState";

// Sub-modules
import type { PhysicsWorldContext } from "./world/PhysicsWorldContext";
import { updateFlippers } from "./world/PhysicsWorldFlippers";
import {
  updateLauncherState,
  tryTransferMainWorldBallToLauncherChain,
} from "./world/PhysicsWorldLauncher";
import {
  buildWorldFromPlan,
  requireBodyFromPlan,
} from "./world/PhysicsWorldPlanBuilder";
import { buildLaunchToDropTraceStep } from "./world/PhysicsWorldTrace";

type MutablePhysicsWorldContext = {
  -readonly [K in keyof PhysicsWorldContext]: PhysicsWorldContext[K];
};

export class PhysicsWorld {
  private readonly ctx: PhysicsWorldContext;

  static async create(table: PrototypeAlphaTable = PROTOTYPE_ALPHA_TABLE): Promise<PhysicsWorld> {
    await RAPIER3D.init();
    return new PhysicsWorld(table);
  }

  private constructor(table: PrototypeAlphaTable = PROTOTYPE_ALPHA_TABLE) {
    this.ctx = {
      table,
      world: null as unknown as RAPIER3D.World,
      eventQueue: null as unknown as RAPIER3D.EventQueue,
      launcherChain: null,
      ballBody: null,
      ballColliderHandle: null,
      leftFlipper: null as unknown as RAPIER3D.RigidBody,
      rightFlipper: null as unknown as RAPIER3D.RigidBody,
      leftPressed: false,
      rightPressed: false,
      launchPressed: false,
      wasLeftPressed: false,
      wasRightPressed: false,
      leftFlipperAngleRad: 0,
      rightFlipperAngleRad: 0,
      plungerLaneState: createInitialPlungerLaneState(),
      currentPlungerCenterY: 0,
      traceStepIndex: 0,
      lastStepDtMs: 0,
      lastStepEvents: [],
      lastHandoffToBoardStep: null,
      firstBoardCollisionStep: null,
      boardCollisionStartedThisStep: false,
      cooldowns: new Map<string, number>(),
      captureDevicesByTag: createCaptureDeviceTagIndex(table.captureDevices),
      saveDevicesByTag: createSaveDeviceTagIndex(table.saveDevices),
      colliderMetaByHandle: new Map<number, ColliderMeta>(),
      captureLifecycleState: createInitialCaptureLifecycleState(),
    };
    this.reset();
  }

  reset(): void {
    this.ctx.launcherChain?.dispose();
    this.ctx.launcherChain = null;
    this.disposeWorld();

    const mutableCtx = this.ctx as MutablePhysicsWorldContext;
    mutableCtx.world = new RAPIER3D.World({
      x: this.ctx.table.gravity.x,
      y: this.ctx.table.gravity.y,
      z: 0,
    });
    mutableCtx.eventQueue = new RAPIER3D.EventQueue(true);

    this.ctx.leftPressed = false;
    this.ctx.rightPressed = false;
    this.ctx.launchPressed = false;
    this.ctx.wasLeftPressed = false;
    this.ctx.wasRightPressed = false;
    this.ctx.plungerLaneState = createInitialPlungerLaneState();
    this.ctx.cooldowns.clear();
    this.ctx.colliderMetaByHandle.clear();
    resetCaptureLifecycleState(this.ctx.captureLifecycleState);
    this.ctx.ballBody = null;
    this.ctx.ballColliderHandle = null;
    this.ctx.currentPlungerCenterY = this.ctx.table.launcher.threeD.plunger.center.y;
    this.ctx.traceStepIndex = 0;
    this.ctx.lastStepDtMs = 0;
    this.ctx.lastStepEvents = [];
    this.ctx.lastHandoffToBoardStep = null;
    this.ctx.firstBoardCollisionStep = null;
    this.ctx.boardCollisionStartedThisStep = false;
    this.ctx.leftFlipperAngleRad = degreesToRadians(this.ctx.table.flippers.left.restAngleDeg);
    this.ctx.rightFlipperAngleRad = degreesToRadians(this.ctx.table.flippers.right.restAngleDeg);
    this.ctx.launcherChain = new LauncherChain3D(this.ctx.table.launcher, this.ctx.table.ball);

    const bodyById = buildWorldFromPlan(this.ctx);
    this.ctx.leftFlipper = requireBodyFromPlan(bodyById, this.ctx.table.refs.flipperBodyIds.left);
    this.ctx.rightFlipper = requireBodyFromPlan(bodyById, this.ctx.table.refs.flipperBodyIds.right);
  }

  dispose(): void {
    this.ctx.launcherChain?.dispose();
    this.ctx.launcherChain = null;
    this.disposeWorld();
  }

  applyCommand(command: RuntimeCommand): void {
    if (command.type === "left-flip") {
      this.ctx.leftPressed = command.pressed;
      return;
    }

    if (command.type === "right-flip") {
      this.ctx.rightPressed = command.pressed;
      return;
    }

    this.ctx.launchPressed = command.pressed;
  }

  spawnBall(position?: TablePoint): void {
    this.removeBall();
    const spawn = this.resolveSpawn(position);
    const spawnPosition = position ?? spawn.position;
    if (
      this.ctx.launcherChain
      && isPointInLauncherLaneRegion(spawnPosition, this.ctx.table.launcher)
    ) {
      this.ctx.launcherChain.spawnBall(spawnPosition);
    } else {
      this.spawnBallInMainWorld(spawnPosition, spawn.launchVelocity);
    }
    this.ctx.plungerLaneState = createInitialPlungerLaneState();
    this.ctx.currentPlungerCenterY = this.ctx.table.launcher.threeD.plunger.center.y;
    this.ctx.traceStepIndex = 0;
    this.ctx.lastStepDtMs = 0;
    this.ctx.lastStepEvents = [];
    this.ctx.lastHandoffToBoardStep = null;
    this.ctx.firstBoardCollisionStep = null;
    this.ctx.boardCollisionStartedThisStep = false;
  }

  removeBall(): void {
    this.ctx.launcherChain?.removeBall();

    if (this.ctx.ballBody) {
      if (this.ctx.ballColliderHandle !== null) {
        this.ctx.colliderMetaByHandle.delete(this.ctx.ballColliderHandle);
      }
      this.ctx.world.removeRigidBody(this.ctx.ballBody);
      this.ctx.ballBody = null;
      this.ctx.ballColliderHandle = null;
    }

    this.ctx.plungerLaneState = createInitialPlungerLaneState();
    this.ctx.currentPlungerCenterY = this.ctx.table.launcher.threeD.plunger.center.y;
    resetCaptureLifecycleState(this.ctx.captureLifecycleState);
    this.ctx.lastStepEvents = [];
    this.ctx.boardCollisionStartedThisStep = false;
  }

  step(dtMs: number): MachineEvent[] {
    this.ctx.traceStepIndex += 1;
    this.ctx.lastStepDtMs = dtMs;
    this.ctx.lastStepEvents = [];
    this.ctx.boardCollisionStartedThisStep = false;
    const dtSeconds = dtMs / 1000;
    this.tickCooldowns(dtMs);
    updateFlippers(this.ctx, dtSeconds);
    tryTransferMainWorldBallToLauncherChain(this.ctx);
    const launcherStep = updateLauncherState(this.ctx, dtMs);
    const launcherPreStepEvents = [...launcherStep.machineEvents];
    let boardHandoffFromChain: { position: { x: number; y: number; z: number }; velocity: TablePoint } | null = null;

    if (this.ctx.launcherChain?.hasBall()) {
      const chainStep = this.ctx.launcherChain.step(
        dtMs,
        launcherStep.chargeRatio,
        launcherStep.releaseChargeRatio,
      );
      this.ctx.currentPlungerCenterY = this.ctx.launcherChain.currentPlungerSnapshot().y;
      launcherPreStepEvents.push(...chainStep.machineEvents);
      if (chainStep.releaseToBoard) {
        boardHandoffFromChain = chainStep.releaseToBoard;
      }
    }

    this.ctx.world.timestep = dtSeconds;
    this.ctx.world.step(this.ctx.eventQueue);

    const stepResult = collectMachineEvents({
      eventQueue: this.ctx.eventQueue,
      colliderMetaByHandle: this.ctx.colliderMetaByHandle,
      cooldowns: this.ctx.cooldowns,
      ballBody: this.ctx.ballBody,
      ballColliderHandle: this.ctx.ballColliderHandle,
      table: this.ctx.table,
    });
    this.ctx.boardCollisionStartedThisStep = stepResult.boardCollisionStarted;
    if (
      this.ctx.boardCollisionStartedThisStep
      && this.ctx.lastHandoffToBoardStep !== null
      && this.ctx.traceStepIndex > this.ctx.lastHandoffToBoardStep
      && this.ctx.firstBoardCollisionStep === null
    ) {
      this.ctx.firstBoardCollisionStep = this.ctx.traceStepIndex;
    }
    const captureLifecycleStep = applyCaptureLifecycleStep({
      state: this.ctx.captureLifecycleState,
      events: stepResult.events,
      dtMs,
      hasBall: this.ctx.ballBody !== null && !stepResult.shouldRemoveBall,
      captureDevicesByTag: this.ctx.captureDevicesByTag,
      saveDevicesByTag: this.ctx.saveDevicesByTag,
    });
    if (this.ctx.ballBody && !stepResult.shouldRemoveBall) {
      if (captureLifecycleStep.holdPosition) {
        const current = this.ctx.ballBody.translation();
        this.ctx.ballBody.setTranslation({
          x: captureLifecycleStep.holdPosition.x,
          y: captureLifecycleStep.holdPosition.y,
          z: current.z,
        }, true);
        this.ctx.ballBody.setLinvel({ x: 0, y: 0, z: 0 }, true);
        this.ctx.ballBody.setAngvel({ x: 0, y: 0, z: 0 }, true);
      }
      for (const impulse of captureLifecycleStep.impulses) {
        this.ctx.ballBody.applyImpulse({
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
      this.ctx.lastHandoffToBoardStep = this.ctx.traceStepIndex;
    }
    this.ctx.wasLeftPressed = this.ctx.leftPressed;
    this.ctx.wasRightPressed = this.ctx.rightPressed;
    const machineEvents = [
      ...launcherPreStepEvents,
      ...captureLifecycleStep.forwardedEvents,
      ...captureLifecycleStep.postStepEvents,
    ];
    this.ctx.lastStepEvents = machineEvents;
    return machineEvents;
  }

  private spawnBallInMainWorld(
    position: TablePoint,
    launchVelocity?: TablePoint,
    spawnZ: number = this.ctx.table.ball.radius,
  ): void {
    const bodyDesc = RAPIER3D.RigidBodyDesc.dynamic()
      .setTranslation(position.x, position.y, spawnZ)
      .setLinearDamping(0.06)
      .setAngularDamping(0.14)
      .setCanSleep(false)
      .setCcdEnabled(true)
      .enabledTranslations(true, true, false)
      .enabledRotations(false, false, true);

    this.ctx.ballBody = this.ctx.world.createRigidBody(bodyDesc);
    const ballCollider = this.ctx.world.createCollider(
      RAPIER3D.ColliderDesc.ball(this.ctx.table.ball.radius)
        .setMass(this.ctx.table.ball.mass)
        .setRestitution(0.55)
        .setFriction(0.18)
        .setActiveEvents(RAPIER3D.ActiveEvents.COLLISION_EVENTS),
      this.ctx.ballBody,
    );

    this.ctx.ballColliderHandle = ballCollider.handle;
    this.ctx.colliderMetaByHandle.set(ballCollider.handle, {
      kind: "ball",
      tag: "ball/main",
    });
    if (launchVelocity) {
      this.ctx.ballBody.setLinvel(
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
    const leftDef = this.ctx.table.flippers.left;
    const rightDef = this.ctx.table.flippers.right;
    const launcherPlunger = this.ctx.launcherChain?.currentPlungerSnapshot();
    const chainBall = this.ctx.launcherChain?.currentSnapshot() ?? null;
    const chainTelemetry = this.ctx.launcherChain?.currentTelemetrySnapshot() ?? null;
    const boardBall = this.ctx.ballBody
      ? {
          x: this.ctx.ballBody.translation().x,
          y: this.ctx.ballBody.translation().y,
          radius: this.ctx.table.ball.radius,
        }
      : null;
    const activeBall = boardBall ?? (chainBall
      ? {
          x: chainBall.position.x,
          y: chainBall.position.y,
          radius: this.ctx.table.ball.radius,
        }
      : null);
    const boardVelocity = this.ctx.ballBody?.linvel() ?? null;
    const launcherChargeRatio = this.ctx.plungerLaneState.phase === "charging"
      ? (this.ctx.table.launcher.chargeMsMax > 0
        ? Math.min(this.ctx.plungerLaneState.chargeMs / this.ctx.table.launcher.chargeMsMax, 1)
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
            phase: this.ctx.plungerLaneState.phase,
          },
          ball: {
            owner: ballOwner,
            position: boardBall
              ? {
                  x: boardBall.x,
                  y: boardBall.y,
                  z: this.ctx.table.ball.radius,
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
        x: launcherPlunger?.x ?? this.ctx.table.launcher.threeD.plunger.center.x,
        y: launcherPlunger?.y ?? this.ctx.currentPlungerCenterY,
        width: launcherPlunger?.width ?? this.ctx.table.launcher.threeD.plunger.width,
        height: launcherPlunger?.height ?? this.ctx.table.launcher.threeD.plunger.depth,
      },
      flippers: {
        left: {
          side: "left",
          pivotX: leftDef.pivot.x,
          pivotY: leftDef.pivot.y,
          length: leftDef.length,
          thickness: leftDef.thickness,
          angleDeg: radiansToDegrees(this.ctx.leftFlipperAngleRad),
        },
        right: {
          side: "right",
          pivotX: rightDef.pivot.x,
          pivotY: rightDef.pivot.y,
          length: rightDef.length,
          thickness: rightDef.thickness,
          angleDeg: radiansToDegrees(this.ctx.rightFlipperAngleRad),
        },
      },
      launcherTelemetry,
      launchTraceStep: buildLaunchToDropTraceStep(this.ctx, launcherTelemetry),
    };
  }

  private resolveSpawn(position: TablePoint | undefined) {
    if (position) {
      return {
        position,
        launchVelocity: undefined,
      };
    }

    return this.ctx.table.physics.spawns[0] ?? { position: this.ctx.table.ball.spawn };
  }

  private tickCooldowns(dtMs: number): void {
    for (const [tag, remainingMs] of [...this.ctx.cooldowns.entries()]) {
      const nextRemaining = remainingMs - dtMs;
      if (nextRemaining <= 0) {
        this.ctx.cooldowns.delete(tag);
        continue;
      }
      this.ctx.cooldowns.set(tag, nextRemaining);
    }
  }

  private disposeWorld(): void {
    this.ctx.eventQueue?.free();
    this.ctx.world?.free();
  }
}
