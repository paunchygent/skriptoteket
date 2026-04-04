/**
 * Compiled-world construction helpers for the Flunk-Out Frenzy physics world.
 *
 * PhysicsWorld owns runtime stepping while this module translates compiled
 * table plans into Rapier bodies, colliders, and semantic collider metadata.
 */

import RAPIER3D from "@dimforge/rapier3d-compat";

import type {
  TableBodyPlan,
  TableColliderPlan,
  TableColliderShapePlan,
} from "../../table/pinballTablePlanTypes";
import type { TablePoint } from "../../table/tableDefinitionTypes";
import type { ColliderMeta } from "../colliderMeta";
import type { PhysicsWorldContext } from "./PhysicsWorldContext";

const BOARD_COLLIDER_HALF_DEPTH = 24;

export function buildWorldFromPlan(
  ctx: Pick<PhysicsWorldContext, "world" | "table" | "colliderMetaByHandle">,
): Map<string, RAPIER3D.RigidBody> {
  const bodyById = new Map<string, RAPIER3D.RigidBody>();

  for (const bodyPlan of ctx.table.physics.bodies) {
    const rigidBody = ctx.world.createRigidBody(createRigidBodyDesc(bodyPlan));
    bodyById.set(bodyPlan.id, rigidBody);
  }

  for (const colliderPlan of ctx.table.physics.colliders) {
    const parentBody = requireBodyFromPlan(bodyById, colliderPlan.bodyId);
    const collider = ctx.world.createCollider(
      createColliderDesc(colliderPlan, ctx.table.surfaces),
      parentBody,
    );
    const meta = resolveColliderMeta(colliderPlan);
    if (meta) {
      ctx.colliderMetaByHandle.set(collider.handle, meta);
    }
  }

  return bodyById;
}

export function requireBodyFromPlan(
  bodyById: ReadonlyMap<string, RAPIER3D.RigidBody>,
  bodyId: string,
): RAPIER3D.RigidBody {
  const body = bodyById.get(bodyId);
  if (!body) {
    throw new Error(`Missing rigid body "${bodyId}" in compiled physics plan.`);
  }
  return body;
}

function createRigidBodyDesc(plan: TableBodyPlan): RAPIER3D.RigidBodyDesc {
  const desc =
    plan.type === "fixed"
      ? RAPIER3D.RigidBodyDesc.fixed()
      : RAPIER3D.RigidBodyDesc.kinematicPositionBased();

  return desc
    .setTranslation(plan.translation.x, plan.translation.y, 0)
    .setRotation(quaternionFromYaw(plan.rotationRad));
}

function createColliderDesc(
  plan: TableColliderPlan,
  surfaces: PhysicsWorldContext["table"]["surfaces"],
): RAPIER3D.ColliderDesc {
  const desc = createShapeDesc(plan.shape);
  const surface = surfaces[plan.surfaceId] ?? surfaces.wall;

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

function createShapeDesc(shape: TableColliderShapePlan): RAPIER3D.ColliderDesc {
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

function resolveColliderMeta(plan: TableColliderPlan): ColliderMeta | null {
  if (!plan.sensor || !plan.semanticKind || !plan.tag) {
    return null;
  }

  switch (plan.semanticKind) {
    case "bumper":
      if (!plan.center || plan.impulseMagnitude === undefined) {
        throw new Error(`Bumper collider "${plan.id}" is missing compiled impulse data.`);
      }
      return { kind: "bumper", tag: plan.tag, center: plan.center, impulse: plan.impulseMagnitude };
    case "sling":
      if (!plan.impulse || !plan.side) {
        throw new Error(`Sling collider "${plan.id}" is missing compiled sling data.`);
      }
      return { kind: "sling", tag: plan.tag, side: plan.side, impulse: plan.impulse };
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
      return { kind: "capture", tag: plan.tag, deviceKind: plan.captureDeviceKind };
    case "save":
      if (!plan.saveDeviceKind) {
        throw new Error(`Save collider "${plan.id}" is missing compiled device kind.`);
      }
      return { kind: "save", tag: plan.tag, deviceKind: plan.saveDeviceKind };
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
