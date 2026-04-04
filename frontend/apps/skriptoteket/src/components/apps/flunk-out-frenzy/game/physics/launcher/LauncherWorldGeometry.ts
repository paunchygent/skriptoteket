/**
 * World-geometry helpers for the Flunk-Out Frenzy launcher chain.
 *
 * LauncherChain3D owns step orchestration while this module builds the Rapier
 * floor, compiled launcher-world carrier colliders, plunger body, and board
 * handoff plane.
 */

import RAPIER3D from "@dimforge/rapier3d-compat";

import type {
  CompiledLauncherWorldAssemblyPlan,
  CompiledLauncherWorldPlan,
} from "../../table/pinballTablePlanTypes";
import type {
  TableLauncherDefinition,
  TablePoint,
  TablePoint3D,
} from "../../table/tableDefinitionTypes";
import type { LauncherContext } from "./LauncherContext";

export function createLauncherWorldFloor(world: RAPIER3D.World): void {
  world.createCollider(
    RAPIER3D.ColliderDesc.cuboid(1000, 2000, 2).setTranslation(0, 0, -2),
  );
}

export function createLauncherWorldWalls(
  world: RAPIER3D.World,
  launcherWorld: CompiledLauncherWorldPlan,
): void {
  for (const assembly of launcherWorld.assemblies) {
    createAssemblyColliders(world, assembly);
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
  const divider = resolveExtrudedPhysicalCarrierByTag(
    launcher,
    "launcher/wall34",
  );
  if (!divider) {
    throw new Error("3D launcher chain is missing donor Wall34 for board handoff.");
  }

  return Math.min(...divider.points.map((point) => point.y));
}

function createAssemblyColliders(
  world: RAPIER3D.World,
  assembly: CompiledLauncherWorldAssemblyPlan,
): void {
  switch (assembly.primitiveKind) {
    case "prism_hull":
      world.createCollider(
        createPrismHullColliderDesc(
          assembly.points,
          assembly.heightBottom,
          assembly.heightTop,
        ),
      );
      return;
    case "round_convex_hull":
      world.createCollider(
        createRoundConvexHullColliderDesc(assembly.points, assembly.borderRadius),
      );
      return;
    case "cuboid_segment_path":
      createSegmentPathColliders(world, assembly.path, (halfLength, midpoint, rotation) => {
        return RAPIER3D.ColliderDesc.cuboid(
          assembly.halfWidth,
          halfLength,
          assembly.halfHeight,
        )
          .setTranslation(midpoint.x, midpoint.y, midpoint.z)
          .setRotation(rotation);
      });
      return;
    case "round_cuboid_segment_path":
      createSegmentPathColliders(world, assembly.path, (halfLength, midpoint, rotation) => {
        return RAPIER3D.ColliderDesc.roundCuboid(
          assembly.halfWidth,
          halfLength,
          assembly.halfHeight,
          assembly.borderRadius,
        )
          .setTranslation(midpoint.x, midpoint.y, midpoint.z)
          .setRotation(rotation);
      });
      return;
    case "capsule_segment_path":
      createSegmentPathColliders(world, assembly.path, (halfLength, midpoint, rotation) => {
        return RAPIER3D.ColliderDesc.capsule(halfLength, assembly.radius)
          .setTranslation(midpoint.x, midpoint.y, midpoint.z)
          .setRotation(rotation);
      });
      return;
  }
}

function createPrismHullColliderDesc(
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

function createRoundConvexHullColliderDesc(
  points: readonly TablePoint3D[],
  borderRadius: number,
): RAPIER3D.ColliderDesc {
  const collider = RAPIER3D.ColliderDesc.roundConvexHull(
    new Float32Array(points.flatMap((point) => [point.x, point.y, point.z])),
    borderRadius,
  );
  if (!collider) {
    throw new Error("Failed to compile 3D launcher-world round convex hull.");
  }
  return collider;
}

function createSegmentPathColliders(
  world: RAPIER3D.World,
  path: readonly TablePoint3D[],
  createColliderDesc: (
    halfLength: number,
    midpoint: TablePoint3D,
    rotation: RAPIER3D.Rotation,
  ) => RAPIER3D.ColliderDesc,
): void {
  for (let index = 0; index < path.length - 1; index += 1) {
    const from = path[index];
    const to = path[index + 1];
    const segment = {
      x: to.x - from.x,
      y: to.y - from.y,
      z: to.z - from.z,
    };
    const length = Math.hypot(segment.x, segment.y, segment.z);
    if (length <= 1e-6) {
      continue;
    }
    world.createCollider(
      createColliderDesc(
        length / 2,
        midpoint3D(from, to),
        quaternionFromUnitYToSegment(segment),
      ),
    );
  }
}

function quaternionFromUnitYToSegment(
  segment: Readonly<{ x: number; y: number; z: number }>,
): RAPIER3D.Rotation {
  const from = { x: 0, y: 1, z: 0 };
  const length = Math.hypot(segment.x, segment.y, segment.z);
  if (length <= 1e-6) {
    return { x: 0, y: 0, z: 0, w: 1 };
  }
  const to = {
    x: segment.x / length,
    y: segment.y / length,
    z: segment.z / length,
  };
  const dot = from.x * to.x + from.y * to.y + from.z * to.z;
  if (dot <= -0.999999) {
    return quaternionFromAxisAngle({ x: 1, y: 0, z: 0 }, Math.PI);
  }

  const cross = {
    x: from.y * to.z - from.z * to.y,
    y: from.z * to.x - from.x * to.z,
    z: from.x * to.y - from.y * to.x,
  };
  return normalizeQuaternion({
    x: cross.x,
    y: cross.y,
    z: cross.z,
    w: 1 + dot,
  });
}

function quaternionFromAxisAngle(
  axis: Readonly<{ x: number; y: number; z: number }>,
  angleRad: number,
): RAPIER3D.Rotation {
  const halfAngle = angleRad / 2;
  const sinHalfAngle = Math.sin(halfAngle);
  return {
    x: axis.x * sinHalfAngle,
    y: axis.y * sinHalfAngle,
    z: axis.z * sinHalfAngle,
    w: Math.cos(halfAngle),
  };
}

function normalizeQuaternion(
  rotation: RAPIER3D.Rotation,
): RAPIER3D.Rotation {
  const magnitude = Math.hypot(
    rotation.x,
    rotation.y,
    rotation.z,
    rotation.w,
  );
  if (magnitude <= 1e-6) {
    return { x: 0, y: 0, z: 0, w: 1 };
  }
  return {
    x: rotation.x / magnitude,
    y: rotation.y / magnitude,
    z: rotation.z / magnitude,
    w: rotation.w / magnitude,
  };
}

function midpoint3D(
  from: TablePoint3D,
  to: TablePoint3D,
): TablePoint3D {
  return {
    x: (from.x + to.x) / 2,
    y: (from.y + to.y) / 2,
    z: (from.z + to.z) / 2,
  };
}

function resolveExtrudedPhysicalCarrierByTag(
  launcher: TableLauncherDefinition,
  tag: string,
): Extract<
  TableLauncherDefinition["threeD"]["carriers"][number],
  { compileRole: "physical"; geometryKind: "extruded_polygon" }
> | null {
  const carrier = launcher.threeD.carriers.find((candidate) => {
    return candidate.tag === tag && candidate.compileRole === "physical";
  });
  if (
    !carrier ||
    carrier.compileRole !== "physical" ||
    carrier.geometryKind !== "extruded_polygon"
  ) {
    return null;
  }
  return carrier;
}
