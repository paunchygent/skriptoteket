/**
 * World-geometry helpers for the Flunk-Out Frenzy launcher chain.
 *
 * LauncherChain3D owns step orchestration while this module builds the Rapier
 * floor, donor walls, guide rails, plunger body, and board handoff plane.
 */

import RAPIER3D from "@dimforge/rapier3d-compat";

import { magnitude, midpoint, segmentAngle } from "../../table/pinballTableMath";
import type {
  TableLauncherDefinition,
  TablePoint,
} from "../../table/tableDefinitionTypes";
import type { LauncherContext } from "./LauncherContext";

export function createLauncherWorldFloor(world: RAPIER3D.World): void {
  world.createCollider(
    RAPIER3D.ColliderDesc.cuboid(1000, 2000, 2).setTranslation(0, 0, -2),
  );
}

export function createLauncherWorldWalls(
  world: RAPIER3D.World,
  launcher: TableLauncherDefinition,
): void {
  for (const wall of launcher.threeD.walls) {
    const collider = createExtrudedPolygonColliderDesc(
      wall.points,
      wall.heightBottom,
      wall.heightTop,
    );
    world.createCollider(collider);
  }

  for (const rail of launcher.threeD.guideRails) {
    const halfHeight = Math.max((rail.heightTop - rail.heightBottom) / 2, 0.5);
    const centerZ = rail.heightBottom + halfHeight;
    for (let index = 0; index < rail.path.length - 1; index += 1) {
      const from = rail.path[index];
      const to = rail.path[index + 1];
      world.createCollider(
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

export function createLauncherPlungerBody(ctx: LauncherContext): RAPIER3D.RigidBody {
  const plunger = ctx.launcher.threeD.plunger;
  const body = ctx.world.createRigidBody(
    RAPIER3D.RigidBodyDesc.kinematicPositionBased().setTranslation(
      plunger.center.x,
      plunger.center.y,
      plunger.center.z,
    ),
  );

  ctx.world.createCollider(
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

export function resolveReleasePlaneY(launcher: TableLauncherDefinition): number {
  const divider = launcher.threeD.walls.find((wall) => wall.tag === "launcher/wall34");
  if (!divider) {
    throw new Error("3D launcher chain is missing donor Wall34 for board handoff.");
  }

  return Math.min(...divider.points.map((point) => point.y));
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
