/**
 * Rapier-backed physics world for Flunk-Out Frenzy prototype alpha.
 *
 * This module owns Rapier rigid bodies, colliders, sensor events, and
 * authored impulses. It emits stable semantic machine events so rules never
 * touch raw collider handles or engine-specific details.
 */

import RAPIER from "@dimforge/rapier2d-compat";

import type { RuntimeCommand } from "../core/runtimeTypes";
import {
  PROTOTYPE_ALPHA_TABLE,
  type PrototypeAlphaTable,
} from "../table/prototypeAlphaTable";
import type {
  TableBumperDefinition,
  TableFlipperDefinition,
  TablePoint,
  TableSlingDefinition,
} from "../table/tableDefinitionTypes";
import type { ColliderMeta } from "./colliderMeta";
import { createLaneDevices } from "./createLaneDevices";
import { createTargetDevices } from "./createTargetDevices";
import { collectMachineEvents } from "./machineEventEmitter";
import type { MachineEvent, PhysicsSnapshot } from "./physicsTypes";

export class PhysicsWorld {
  private world!: RAPIER.World;
  private eventQueue!: RAPIER.EventQueue;
  private ballBody: RAPIER.RigidBody | null = null;
  private ballColliderHandle: number | null = null;
  private leftFlipper!: RAPIER.RigidBody;
  private rightFlipper!: RAPIER.RigidBody;
  private leftFlipperAngleRad = 0;
  private rightFlipperAngleRad = 0;
  private leftPressed = false;
  private rightPressed = false;
  private launchPressed = false;
  private launchChargeMs = 0;
  private wasLaunchPressed = false;
  private wasLeftPressed = false;
  private wasRightPressed = false;
  private readonly cooldowns = new Map<string, number>();
  private readonly colliderMetaByHandle = new Map<number, ColliderMeta>();

  static async create(table: PrototypeAlphaTable = PROTOTYPE_ALPHA_TABLE): Promise<PhysicsWorld> {
    await RAPIER.init();
    return new PhysicsWorld(table);
  }

  private constructor(private readonly table: PrototypeAlphaTable = PROTOTYPE_ALPHA_TABLE) {
    this.reset();
  }

  reset(): void {
    this.disposeWorld();

    this.world = new RAPIER.World(this.table.gravity);
    this.eventQueue = new RAPIER.EventQueue(true);
    this.world.lengthUnit = 100;

    this.leftPressed = false;
    this.rightPressed = false;
    this.launchPressed = false;
    this.launchChargeMs = 0;
    this.wasLaunchPressed = false;
    this.wasLeftPressed = false;
    this.wasRightPressed = false;
    this.cooldowns.clear();
    this.colliderMetaByHandle.clear();
    this.ballBody = null;
    this.ballColliderHandle = null;
    this.leftFlipperAngleRad = degreesToRadians(this.table.flippers.left.restAngleDeg);
    this.rightFlipperAngleRad = degreesToRadians(this.table.flippers.right.restAngleDeg);

    this.buildStaticWorld();
    this.leftFlipper = this.createFlipper(this.table.flippers.left);
    this.rightFlipper = this.createFlipper(this.table.flippers.right);
  }

  dispose(): void {
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

  spawnBall(position: TablePoint = this.table.ball.spawn): void {
    if (this.ballBody) {
      this.world.removeRigidBody(this.ballBody);
    }

    const bodyDesc = RAPIER.RigidBodyDesc.dynamic()
      .setTranslation(position.x, position.y)
      .setLinearDamping(0.06)
      .setAngularDamping(0.14)
      .setCanSleep(false)
      .setCcdEnabled(true)
      .setAdditionalMass(this.table.ball.mass);

    this.ballBody = this.world.createRigidBody(bodyDesc);
    const ballCollider = this.world.createCollider(
      RAPIER.ColliderDesc.ball(this.table.ball.radius)
        .setMass(this.table.ball.mass)
        .setRestitution(0.55)
        .setFriction(0.18)
        .setActiveEvents(RAPIER.ActiveEvents.COLLISION_EVENTS),
      this.ballBody,
    );

    this.ballColliderHandle = ballCollider.handle;
    this.colliderMetaByHandle.set(ballCollider.handle, {
      kind: "ball",
      tag: "ball/main",
    });
    this.launchChargeMs = 0;
    this.wasLaunchPressed = false;
  }

  removeBall(): void {
    if (!this.ballBody) {
      return;
    }

    this.world.removeRigidBody(this.ballBody);
    this.ballBody = null;
    this.ballColliderHandle = null;
    this.launchChargeMs = 0;
  }

  step(dtMs: number): MachineEvent[] {
    const dtSeconds = dtMs / 1000;
    this.tickCooldowns(dtMs);
    this.updateFlippers(dtSeconds);
    this.updateLauncher(dtMs);
    this.world.timestep = dtSeconds;
    this.world.step(this.eventQueue);

    const stepResult = collectMachineEvents({
      eventQueue: this.eventQueue,
      colliderMetaByHandle: this.colliderMetaByHandle,
      cooldowns: this.cooldowns,
      ballBody: this.ballBody,
      table: this.table,
    });
    if (stepResult.shouldRemoveBall) {
      this.removeBall();
    }
    this.wasLaunchPressed = this.launchPressed;
    this.wasLeftPressed = this.leftPressed;
    this.wasRightPressed = this.rightPressed;
    return stepResult.events;
  }

  currentSnapshot(): PhysicsSnapshot {
    const leftDef = this.table.flippers.left;
    const rightDef = this.table.flippers.right;

    return {
      ball: this.ballBody
        ? {
            x: this.ballBody.translation().x,
            y: this.ballBody.translation().y,
            radius: this.table.ball.radius,
          }
        : null,
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
    };
  }

  private buildStaticWorld(): void {
    for (const wall of this.table.walls) {
      this.world.createCollider(
        RAPIER.ColliderDesc.segment(wall.from, wall.to)
          .setRestitution(0.34)
          .setFriction(0.16),
      );
    }

    for (const bumper of this.table.bumpers) {
      this.buildBumper(bumper);
    }

    for (const sling of this.table.slings) {
      this.buildSling(sling);
    }

    createLaneDevices({
      world: this.world,
      colliderMetaByHandle: this.colliderMetaByHandle,
      rollovers: this.table.rollovers,
      tripwires: this.table.tripwires,
      gates: this.table.gates,
    });

    createTargetDevices({
      world: this.world,
      colliderMetaByHandle: this.colliderMetaByHandle,
      standupTargets: this.table.standupTargets,
      popupTargets: this.table.popupTargets,
    });

    const drain = this.world.createCollider(
      RAPIER.ColliderDesc.cuboid(this.table.drain.width / 2, this.table.drain.height / 2)
        .setTranslation(this.table.drain.x, this.table.drain.y)
        .setSensor(true)
        .setActiveEvents(RAPIER.ActiveEvents.COLLISION_EVENTS),
    );
    this.colliderMetaByHandle.set(drain.handle, {
      kind: "drain",
      tag: this.table.drain.tag,
    });
  }

  private buildBumper(bumper: TableBumperDefinition): void {
    this.world.createCollider(
      RAPIER.ColliderDesc.ball(bumper.radius)
        .setTranslation(bumper.x, bumper.y)
        .setRestitution(0.92)
        .setFriction(0.08),
    );

    const sensor = this.world.createCollider(
      RAPIER.ColliderDesc.ball(bumper.sensorRadius)
        .setTranslation(bumper.x, bumper.y)
        .setSensor(true)
        .setActiveEvents(RAPIER.ActiveEvents.COLLISION_EVENTS),
    );
    this.colliderMetaByHandle.set(sensor.handle, {
      kind: "bumper",
      tag: bumper.tag,
      center: { x: bumper.x, y: bumper.y },
      impulse: bumper.impulse,
    });
  }

  private buildSling(sling: TableSlingDefinition): void {
    this.world.createCollider(
      RAPIER.ColliderDesc.triangle(...sling.vertices)
        .setRestitution(0.72)
        .setFriction(0.14),
    );

    const sensor = this.world.createCollider(
      RAPIER.ColliderDesc.triangle(...sling.vertices)
        .setSensor(true)
        .setActiveEvents(RAPIER.ActiveEvents.COLLISION_EVENTS),
    );
    this.colliderMetaByHandle.set(sensor.handle, {
      kind: "sling",
      tag: sling.tag,
      side: sling.side,
      impulse: sling.impulse,
    });
  }

  private createFlipper(flipper: TableFlipperDefinition): RAPIER.RigidBody {
    const body = this.world.createRigidBody(
      RAPIER.RigidBodyDesc.kinematicPositionBased()
        .setTranslation(flipper.pivot.x, flipper.pivot.y)
        .setRotation(degreesToRadians(flipper.restAngleDeg)),
    );

    const xOffset = flipper.side === "left" ? flipper.length / 2 : -flipper.length / 2;
    this.world.createCollider(
      RAPIER.ColliderDesc.cuboid(flipper.length / 2, flipper.thickness / 2)
        .setTranslation(xOffset, 0)
        .setRestitution(0.28)
        .setFriction(0.68),
      body,
    );

    return body;
  }

  private updateFlippers(dtSeconds: number): void {
    this.leftFlipperAngleRad = this.driveFlipper(
      this.leftFlipper,
      this.table.flippers.left,
      this.leftPressed,
      dtSeconds,
      this.leftFlipperAngleRad,
    );
    this.rightFlipperAngleRad = this.driveFlipper(
      this.rightFlipper,
      this.table.flippers.right,
      this.rightPressed,
      dtSeconds,
      this.rightFlipperAngleRad,
    );

    if (this.leftPressed && !this.wasLeftPressed) {
      this.assistFlipper(this.table.flippers.left);
    }
    if (this.rightPressed && !this.wasRightPressed) {
      this.assistFlipper(this.table.flippers.right);
    }
  }

  private driveFlipper(
    body: RAPIER.RigidBody,
    flipper: TableFlipperDefinition,
    pressed: boolean,
    dtSeconds: number,
    currentAngle: number,
  ): number {
    const targetAngle = degreesToRadians(
      pressed ? flipper.activeAngleDeg : flipper.restAngleDeg,
    );
    const maxDelta = dtSeconds * 18;
    const nextAngle = approachAngle(currentAngle, targetAngle, maxDelta);
    body.setNextKinematicRotation(nextAngle);
    return nextAngle;
  }

  private assistFlipper(flipper: TableFlipperDefinition): void {
    if (!this.ballBody) {
      return;
    }

    const ballPosition = this.ballBody.translation();
    const distance = Math.hypot(ballPosition.x - flipper.pivot.x, ballPosition.y - flipper.pivot.y);
    if (distance > flipper.length * 1.25 || ballPosition.y > flipper.pivot.y + 36) {
      return;
    }

    this.ballBody.applyImpulse(flipper.assistImpulse, true);
  }

  private updateLauncher(dtMs: number): void {
    if (!this.ballBody) {
      this.launchChargeMs = 0;
      return;
    }

    if (this.launchPressed) {
      this.launchChargeMs = Math.min(this.launchChargeMs + dtMs, 900);
      return;
    }

    if (this.wasLaunchPressed && this.launchChargeMs > 0 && this.ballIsInLaunchLane()) {
      const chargeRatio = this.launchChargeMs / 900;
      const impulse = this.table.ball.launchImpulseMin +
        (this.table.ball.launchImpulseMax - this.table.ball.launchImpulseMin) * chargeRatio;

      this.ballBody.applyImpulse(
        {
          x: this.table.ball.launchAssistX,
          y: -impulse,
        },
        true,
      );
    }

    this.launchChargeMs = 0;
  }

  private ballIsInLaunchLane(): boolean {
    if (!this.ballBody) {
      return false;
    }

    const position = this.ballBody.translation();
    return position.x > 485 && position.y > 860;
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
}

function approachAngle(current: number, target: number, maxDelta: number): number {
  if (Math.abs(target - current) <= maxDelta) {
    return target;
  }
  return current + Math.sign(target - current) * maxDelta;
}

function degreesToRadians(deg: number): number {
  return (deg * Math.PI) / 180;
}

function radiansToDegrees(rad: number): number {
  return (rad * 180) / Math.PI;
}
