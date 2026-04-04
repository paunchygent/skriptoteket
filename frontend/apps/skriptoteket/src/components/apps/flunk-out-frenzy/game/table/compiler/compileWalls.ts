import {
  magnitude,
  midpoint,
  segmentAngle,
  sub,
  v,
} from "../pinballTableMath";
import type {
  TableColliderPlan,
  TableRenderNodePlan,
} from "../pinballTablePlanTypes";
import type { PinballTableSpec } from "../pinballTablePlanTypes";
import type { CompilerContext, CompilerOutput } from "./compilerTypes";

export function compileRails(
  rails: PinballTableSpec["rails"],
  context: CompilerContext,
): CompilerOutput {
  const colliders: TableColliderPlan[] = [];
  const renderNodes: TableRenderNodePlan[] = [];

  for (const rail of rails) {
    for (let index = 0; index < rail.path.length - 1; index += 1) {
      const from = rail.path[index];
      const to = rail.path[index + 1];
      if (
        railSegmentIntersectsPlayfieldContactZ(
          rail,
          index,
          context.ballRestZ,
        )
      ) {
        colliders.push({
          id: `${rail.id}:segment:${index}`,
          bodyId: context.staticBodyId,
          translation: midpoint(from, to),
          rotationRad: segmentAngle(from, to),
          shape: {
            kind: "thick-segment",
            halfLength: magnitude(sub(to, from)) * 0.5,
            radius: rail.radius,
          },
          sensor: false,
          surfaceId: rail.surfaceId ?? "wall",
        });
      }
    }

    if (rail.render !== false) {
      renderNodes.push({
        kind: "polyline",
        id: `${rail.id}:render`,
        layer: rail.renderLayer ?? "walls",
        points: rail.path,
        thickness: rail.radius * 2,
      });
    }
  }

  return { colliders, renderNodes };
}

export function compileWalls(
  walls: PinballTableSpec["walls"] = [],
  context: CompilerContext,
): CompilerOutput {
  const colliders: TableColliderPlan[] = [];
  const renderNodes: TableRenderNodePlan[] = [];

  for (const wall of walls) {
    if (wallIntersectsPlayfieldContactZ(wall, context.ballRestZ)) {
      colliders.push({
        id: `${wall.id}:segment`,
        bodyId: context.staticBodyId,
        translation: midpoint(wall.a, wall.b),
        rotationRad: segmentAngle(wall.a, wall.b),
        shape: {
          kind: "thick-segment",
          halfLength: magnitude(sub(wall.b, wall.a)) * 0.5,
          radius: wall.radius,
        },
        sensor: false,
        surfaceId: wall.surfaceId ?? "wall",
      });
    }

    renderNodes.push({
      kind: "polyline",
      id: `${wall.id}:render`,
      layer: wall.renderLayer ?? "walls",
      points: [wall.a, wall.b],
      thickness: wall.radius * 2,
    });
  }

  return { colliders, renderNodes };
}

export function compilePosts(
  posts: PinballTableSpec["posts"] = [],
  context: CompilerContext,
): CompilerOutput {
  const colliders: TableColliderPlan[] = [];
  const renderNodes: TableRenderNodePlan[] = [];

  for (const post of posts) {
    colliders.push({
      id: `${post.id}:collider`,
      bodyId: context.staticBodyId,
      translation: post.center,
      rotationRad: 0,
      shape: { kind: "circle", radius: post.radius },
      sensor: false,
      surfaceId: post.surfaceId ?? "post",
    });

    renderNodes.push({
      kind: "circle",
      id: `${post.id}:render`,
      layer: post.renderLayer ?? "posts",
      center: post.center,
      radius: post.radius,
    });
  }

  return { colliders, renderNodes };
}

export function compileSolids(
  solids: PinballTableSpec["solids"] = [],
  context: CompilerContext,
): CompilerOutput {
  const colliders: TableColliderPlan[] = [];
  const renderNodes: TableRenderNodePlan[] = [];

  for (const solid of solids) {
    if (solidIntersectsPlayfieldContactZ(solid, context.ballRestZ)) {
      colliders.push({
        id: `${solid.id}:body`,
        bodyId: context.staticBodyId,
        translation: v(0, 0),
        rotationRad: 0,
        shape: {
          kind: "convex-polygon",
          vertices: solid.points,
        },
        sensor: false,
        surfaceId: solid.surfaceId ?? "wall",
      });
    }

    renderNodes.push({
      kind: "polygon",
      id: `${solid.id}:render`,
      layer: solid.renderLayer ?? "walls",
      points: solid.points,
      fillColor: solid.fillColor,
      fillAlpha: solid.fillAlpha,
      strokeColor: solid.strokeColor,
      strokeAlpha: solid.strokeAlpha,
      strokeWidth: solid.strokeWidth,
    });
  }

  return { colliders, renderNodes };
}

function solidIntersectsPlayfieldContactZ(
  solid: Readonly<{
    heightBottom?: number;
    heightTop?: number;
  }>,
  playfieldContactZ: number,
): boolean {
  if (solid.heightBottom === undefined || solid.heightTop === undefined) {
    return true;
  }

  return solid.heightBottom <= playfieldContactZ && playfieldContactZ <= solid.heightTop;
}

function wallIntersectsPlayfieldContactZ(
  wall: Readonly<{
    physics?: boolean;
    heightBottom?: number;
    heightTop?: number;
  }>,
  playfieldContactZ: number,
): boolean {
  if (wall.physics === false) {
    return false;
  }

  return solidIntersectsPlayfieldContactZ(wall, playfieldContactZ);
}

function railSegmentIntersectsPlayfieldContactZ(
  rail: Readonly<{
    physics?: boolean;
    zPath?: readonly number[];
    heightBottom?: number;
    heightTop?: number;
  }>,
  segmentIndex: number,
  playfieldContactZ: number,
): boolean {
  if (rail.physics === false) {
    return false;
  }

  if (rail.zPath && rail.zPath.length > segmentIndex + 1) {
    const fromZ = rail.zPath[segmentIndex];
    const toZ = rail.zPath[segmentIndex + 1];
    const minZ = Math.min(fromZ, toZ);
    const maxZ = Math.max(fromZ, toZ);
    return minZ <= playfieldContactZ && playfieldContactZ <= maxZ;
  }

  return solidIntersectsPlayfieldContactZ(rail, playfieldContactZ);
}
