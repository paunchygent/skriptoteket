/**
 * Rapier-backed physics world for Flunk-Out Frenzy prototype alpha.
 *
 * This module owns Rapier rigid bodies, colliders, sensor events, and the
 * compiled pinball-table plans that drive simulation. It emits stable semantic
 * machine events so rules never touch raw collider handles or engine-specific
 * details.
 */

import RAPIER from "@dimforge/rapier2d-compat";

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
  TableFlipperDefinition,
  TablePoint,
} from "../table/tableDefinitionTypes";
import type { ColliderMeta } from "./colliderMeta";
import { resolveFlipperContactImpulse } from "./flipperContactModel";
import { collectMachineEvents } from "./machineEventEmitter";
import type { MachineEvent, PhysicsSnapshot } from "./physicsTypes";
import {
  createInitialPlungerLaneState,
  stepPlungerLaneState,
  type PlungerLaneBallSnapshot,
  type PlungerLaneState,
} from "./plungerLaneState";

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
  private wasLeftPressed = false;
  private wasRightPressed = false;
  private plungerLaneState: PlungerLaneState = createInitialPlungerLaneState();
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
    this.wasLeftPressed = false;
    this.wasRightPressed = false;
    this.plungerLaneState = createInitialPlungerLaneState();
    this.cooldowns.clear();
    this.colliderMetaByHandle.clear();
    this.ballBody = null;
    this.ballColliderHandle = null;
    this.leftFlipperAngleRad = degreesToRadians(this.table.flippers.left.restAngleDeg);
    this.rightFlipperAngleRad = degreesToRadians(this.table.flippers.right.restAngleDeg);

    const bodyById = this.buildWorldFromPlan();
    this.leftFlipper = this.requireBody(bodyById, this.table.refs.flipperBodyIds.left);
    this.rightFlipper = this.requireBody(bodyById, this.table.refs.flipperBodyIds.right);
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

  spawnBall(position?: TablePoint): void {
    if (this.ballBody) {
      this.removeBall();
    }

    const spawn = this.resolveSpawn(position);
    const spawnPosition = position ?? spawn.position;

    const bodyDesc = RAPIER.RigidBodyDesc.dynamic()
      .setTranslation(spawnPosition.x, spawnPosition.y)
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
    if (spawn.launchVelocity) {
      this.ballBody.setLinvel(spawn.launchVelocity, true);
    }
    this.plungerLaneState = createInitialPlungerLaneState();
  }

  removeBall(): void {
    if (!this.ballBody) {
      return;
    }

    if (this.ballColliderHandle !== null) {
      this.colliderMetaByHandle.delete(this.ballColliderHandle);
    }
    this.world.removeRigidBody(this.ballBody);
    this.ballBody = null;
    this.ballColliderHandle = null;
    this.plungerLaneState = createInitialPlungerLaneState();
  }

  step(dtMs: number): MachineEvent[] {
    const dtSeconds = dtMs / 1000;
    this.tickCooldowns(dtMs);
    this.updateFlippers(dtSeconds);
    const launcherPreStepEvents = this.updateLauncherState(dtMs);
    this.world.timestep = dtSeconds;
    this.world.step(this.eventQueue);

    const stepResult = collectMachineEvents({
      eventQueue: this.eventQueue,
      colliderMetaByHandle: this.colliderMetaByHandle,
      cooldowns: this.cooldowns,
      ballBody: this.ballBody,
      table: this.table,
    });
    const launcherPostStepEvents = this.updateLauncherState(0);
    if (stepResult.shouldRemoveBall) {
      this.removeBall();
    }
    this.wasLeftPressed = this.leftPressed;
    this.wasRightPressed = this.rightPressed;
    return [
      ...launcherPreStepEvents,
      ...stepResult.events,
      ...launcherPostStepEvents,
    ];
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

  private buildWorldFromPlan(): Map<string, RAPIER.RigidBody> {
    const bodyById = new Map<string, RAPIER.RigidBody>();

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

  private createRigidBodyDesc(plan: TableBodyPlan): RAPIER.RigidBodyDesc {
    const desc =
      plan.type === "fixed"
        ? RAPIER.RigidBodyDesc.fixed()
        : RAPIER.RigidBodyDesc.kinematicPositionBased();

    return desc
      .setTranslation(plan.translation.x, plan.translation.y)
      .setRotation(plan.rotationRad);
  }

  private createColliderDesc(plan: TableColliderPlan): RAPIER.ColliderDesc {
    const desc = this.createShapeDesc(plan.shape);
    const surface = this.table.surfaces[plan.surfaceId] ?? this.table.surfaces.wall;

    desc
      .setTranslation(plan.translation.x, plan.translation.y)
      .setRotation(plan.rotationRad)
      .setRestitution(surface.restitution)
      .setFriction(surface.friction);

    if (plan.sensor) {
      desc
        .setSensor(true)
        .setActiveEvents(RAPIER.ActiveEvents.COLLISION_EVENTS);
    }

    return desc;
  }

  private createShapeDesc(shape: TableColliderShapePlan): RAPIER.ColliderDesc {
    switch (shape.kind) {
      case "thick-segment":
        return RAPIER.ColliderDesc.cuboid(shape.halfLength, shape.radius);
      case "circle":
        return RAPIER.ColliderDesc.ball(shape.radius);
      case "cuboid":
        return RAPIER.ColliderDesc.cuboid(shape.halfExtents.x, shape.halfExtents.y);
      case "triangle":
        return RAPIER.ColliderDesc.triangle(...shape.vertices);
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
        return { kind: "tripwire", tag: plan.tag };
      case "gate":
        return { kind: "gate", tag: plan.tag };
      case "standup-target":
        return { kind: "standup-target", tag: plan.tag };
      case "popup-target":
        return { kind: "popup-target", tag: plan.tag };
      case "drain":
        return { kind: "drain", tag: plan.tag };
    }
  }

  private requireBody(
    bodyById: ReadonlyMap<string, RAPIER.RigidBody>,
    bodyId: string,
  ): RAPIER.RigidBody {
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
      this.applyFlipperContact(this.table.flippers.left, this.leftFlipperAngleRad);
    }
    if (this.rightPressed && !this.wasRightPressed) {
      this.applyFlipperContact(this.table.flippers.right, this.rightFlipperAngleRad);
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

  private applyFlipperContact(flipper: TableFlipperDefinition, angleRad: number): void {
    if (!this.ballBody) {
      return;
    }

    const contactImpulse = resolveFlipperContactImpulse({
      ball: {
        x: this.ballBody.translation().x,
        y: this.ballBody.translation().y,
        radius: this.table.ball.radius,
      },
      flipper,
      angleRad,
    });
    if (!contactImpulse) {
      return;
    }

    this.ballBody.applyImpulseAtPoint(contactImpulse.impulse, contactImpulse.point, true);
  }

  private updateLauncherState(dtMs: number): MachineEvent[] {
    const result = stepPlungerLaneState({
      state: this.plungerLaneState,
      ball: this.currentPlungerBallSnapshot(),
      launchPressed: this.launchPressed,
      launcher: this.table.launcher,
      dtMs,
    });
    this.plungerLaneState = result.nextState;

    if (this.ballBody && result.releaseImpulse) {
      this.ballBody.applyImpulse(result.releaseImpulse, true);
    }

    return result.machineEvents;
  }

  private currentPlungerBallSnapshot(): PlungerLaneBallSnapshot | null {
    if (!this.ballBody) {
      return null;
    }

    const position = this.ballBody.translation();
    const velocity = this.ballBody.linvel();

    return {
      position: {
        x: position.x,
        y: position.y,
      },
      velocity: {
        x: velocity.x,
        y: velocity.y,
      },
    };
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
