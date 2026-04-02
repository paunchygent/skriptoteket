/**
 * Compiler from authored pinball table specs to explicit runtime plans.
 *
 * The compiled table keeps semantic device metadata alongside physics collider
 * plans and render nodes so runtime, rules, and presentation stay synchronized.
 */

import type {
  CompiledPinballTable,
  PinballTableSpec,
  TableBodyPlan,
  TableColliderPlan,
  TableRenderNodePlan,
  TableSurfaceSpec,
} from "./pinballTablePlanTypes";
import { DEFAULT_TABLE_SURFACES } from "./pinballTablePlanTypes";
import { degreesToRadians, magnitude, midpoint, segmentAngle, sub, v } from "./pinballTableMath";

export function compilePinballTable(spec: PinballTableSpec): CompiledPinballTable {
  assertValidTableSpec(spec);

  const surfaces = mergeSurfaceIndex(spec.surfaces);
  const staticBodyId = `${spec.id}:static`;
  const flipperBodyIds = {
    left: `${spec.id}:flipper-left`,
    right: `${spec.id}:flipper-right`,
  } as const;

  const bodies: TableBodyPlan[] = [
    {
      id: staticBodyId,
      type: "fixed",
      translation: v(0, 0),
      rotationRad: 0,
    },
    {
      id: flipperBodyIds.left,
      type: "kinematic-position",
      translation: spec.flippers.left.pivot,
      rotationRad: degreesToRadians(spec.flippers.left.restAngleDeg),
    },
    {
      id: flipperBodyIds.right,
      type: "kinematic-position",
      translation: spec.flippers.right.pivot,
      rotationRad: degreesToRadians(spec.flippers.right.restAngleDeg),
    },
  ];

  const colliders: TableColliderPlan[] = [];
  const renderNodes: TableRenderNodePlan[] = [];

  for (const rail of spec.rails) {
    for (let index = 0; index < rail.path.length - 1; index += 1) {
      const from = rail.path[index];
      const to = rail.path[index + 1];
      colliders.push({
        id: `${rail.id}:segment:${index}`,
        bodyId: staticBodyId,
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

    renderNodes.push({
      kind: "polyline",
      id: `${rail.id}:render`,
      layer: rail.renderLayer ?? "walls",
      points: rail.path,
      thickness: rail.radius * 2,
    });
  }

  for (const wall of spec.walls ?? []) {
    colliders.push({
      id: `${wall.id}:segment`,
      bodyId: staticBodyId,
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

    renderNodes.push({
      kind: "polyline",
      id: `${wall.id}:render`,
      layer: wall.renderLayer ?? "walls",
      points: [wall.a, wall.b],
      thickness: wall.radius * 2,
    });
  }

  for (const post of spec.posts ?? []) {
    colliders.push({
      id: `${post.id}:collider`,
      bodyId: staticBodyId,
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

  for (const bumper of spec.bumpers) {
    colliders.push({
      id: `${bumper.tag}:body`,
      bodyId: staticBodyId,
      translation: { x: bumper.x, y: bumper.y },
      rotationRad: 0,
      shape: { kind: "circle", radius: bumper.radius },
      sensor: false,
      surfaceId: "bumper",
    });
    colliders.push({
      id: `${bumper.tag}:sensor`,
      bodyId: staticBodyId,
      translation: { x: bumper.x, y: bumper.y },
      rotationRad: 0,
      shape: { kind: "circle", radius: bumper.sensorRadius },
      sensor: true,
      surfaceId: "sensor",
      semanticKind: "bumper",
      tag: bumper.tag,
      center: { x: bumper.x, y: bumper.y },
      impulseMagnitude: bumper.impulse,
    });

    renderNodes.push({
      kind: "circle",
      id: `${bumper.tag}:halo`,
      layer: "bumper-halos",
      center: { x: bumper.x, y: bumper.y },
      radius: bumper.sensorRadius,
    });
    renderNodes.push({
      kind: "circle",
      id: `${bumper.tag}:render`,
      layer: "bumpers",
      center: { x: bumper.x, y: bumper.y },
      radius: bumper.radius,
    });
  }

  for (const sling of spec.slings) {
    colliders.push({
      id: `${sling.tag}:body`,
      bodyId: staticBodyId,
      translation: v(0, 0),
      rotationRad: 0,
      shape: { kind: "triangle", vertices: sling.vertices },
      sensor: false,
      surfaceId: "wall",
    });
    colliders.push({
      id: `${sling.tag}:sensor`,
      bodyId: staticBodyId,
      translation: v(0, 0),
      rotationRad: 0,
      shape: { kind: "triangle", vertices: sling.vertices },
      sensor: true,
      surfaceId: "sensor",
      semanticKind: "sling",
      tag: sling.tag,
      impulse: sling.impulse,
      side: sling.side,
    });

    renderNodes.push({
      kind: "polygon",
      id: `${sling.tag}:render`,
      layer: "slings",
      points: sling.vertices,
      fillColor: sling.side === "left" ? 0xff7ca8 : 0xff8a6f,
      fillAlpha: 0.18,
      strokeColor: 0xffd1df,
      strokeAlpha: 0.54,
      strokeWidth: 2,
    });
  }

  for (const rollover of spec.rollovers) {
    colliders.push({
      id: `${rollover.tag}:sensor`,
      bodyId: staticBodyId,
      translation: { x: rollover.x, y: rollover.y },
      rotationRad: 0,
      shape: { kind: "cuboid", halfExtents: v(rollover.width / 2, rollover.height / 2) },
      sensor: true,
      surfaceId: "sensor",
      semanticKind: "rollover",
      tag: rollover.tag,
    });
  }

  for (const tripwire of spec.tripwires) {
    colliders.push({
      id: `${tripwire.tag}:sensor`,
      bodyId: staticBodyId,
      translation: { x: tripwire.x, y: tripwire.y },
      rotationRad: 0,
      shape: { kind: "cuboid", halfExtents: v(tripwire.width / 2, tripwire.height / 2) },
      sensor: true,
      surfaceId: "sensor",
      semanticKind: "tripwire",
      tag: tripwire.tag,
    });
  }

  for (const gate of spec.gates) {
    colliders.push({
      id: `${gate.tag}:sensor`,
      bodyId: staticBodyId,
      translation: { x: gate.x, y: gate.y },
      rotationRad: 0,
      shape: { kind: "cuboid", halfExtents: v(gate.width / 2, gate.height / 2) },
      sensor: true,
      surfaceId: "sensor",
      semanticKind: "gate",
      tag: gate.tag,
    });
  }

  for (const target of spec.standupTargets) {
    const rotationRad = degreesToRadians(target.angleDeg ?? 0);
    colliders.push({
      id: `${target.tag}:body`,
      bodyId: staticBodyId,
      translation: { x: target.x, y: target.y },
      rotationRad,
      shape: { kind: "cuboid", halfExtents: v(target.width / 2, target.height / 2) },
      sensor: false,
      surfaceId: "wall",
    });
    colliders.push({
      id: `${target.tag}:sensor`,
      bodyId: staticBodyId,
      translation: { x: target.x, y: target.y },
      rotationRad,
      shape: { kind: "cuboid", halfExtents: v(target.width / 2 + 2, target.height / 2 + 2) },
      sensor: true,
      surfaceId: "sensor",
      semanticKind: "standup-target",
      tag: target.tag,
    });

    renderNodes.push({
      kind: "rect",
      id: `${target.tag}:render`,
      layer: "targets",
      center: { x: target.x, y: target.y },
      width: target.width,
      height: target.height,
      rotationRad,
      fillColor: 0xffd26f,
      fillAlpha: 0.18,
      strokeColor: 0xffebba,
      strokeAlpha: 0.64,
      strokeWidth: 2,
    });
  }

  for (const target of spec.popupTargets) {
    colliders.push({
      id: `${target.tag}:body`,
      bodyId: staticBodyId,
      translation: { x: target.x, y: target.y },
      rotationRad: 0,
      shape: { kind: "circle", radius: target.radius },
      sensor: false,
      surfaceId: "wall",
    });
    colliders.push({
      id: `${target.tag}:sensor`,
      bodyId: staticBodyId,
      translation: { x: target.x, y: target.y },
      rotationRad: 0,
      shape: { kind: "circle", radius: target.sensorRadius },
      sensor: true,
      surfaceId: "sensor",
      semanticKind: "popup-target",
      tag: target.tag,
    });

    renderNodes.push({
      kind: "circle",
      id: `${target.tag}:halo`,
      layer: "popup-target-halos",
      center: { x: target.x, y: target.y },
      radius: target.sensorRadius,
    });
    renderNodes.push({
      kind: "circle",
      id: `${target.tag}:render`,
      layer: "popup-targets",
      center: { x: target.x, y: target.y },
      radius: target.radius,
    });
  }

  colliders.push({
    id: `${spec.drain.tag}:sensor`,
    bodyId: staticBodyId,
    translation: { x: spec.drain.x, y: spec.drain.y },
    rotationRad: 0,
    shape: { kind: "cuboid", halfExtents: v(spec.drain.width / 2, spec.drain.height / 2) },
    sensor: true,
    surfaceId: "sensor",
    semanticKind: "drain",
    tag: spec.drain.tag,
  });
  renderNodes.push({
    kind: "rect",
    id: `${spec.drain.tag}:render`,
    layer: "drain",
    center: { x: spec.drain.x, y: spec.drain.y },
    width: spec.drain.width,
    height: spec.drain.height,
    rotationRad: 0,
    fillColor: 0x250f16,
    fillAlpha: 1,
    strokeColor: 0xff96b7,
    strokeAlpha: 0.38,
    strokeWidth: 2,
  });

  for (const surface of spec.renderSurfaces ?? []) {
    if (surface.kind === "polygon") {
      renderNodes.push({
        kind: "polygon",
        id: surface.id,
        layer: surface.layer ?? "field",
        points: surface.points,
        fillColor: surface.fillColor,
        fillAlpha: surface.fillAlpha,
        strokeColor: surface.strokeColor,
        strokeAlpha: surface.strokeAlpha,
        strokeWidth: surface.strokeWidth,
      });
    } else {
      renderNodes.push({
        kind: "rect",
        id: surface.id,
        layer: surface.layer ?? "field",
        center: surface.center,
        width: surface.width,
        height: surface.height,
        rotationRad: degreesToRadians(surface.angleDeg ?? 0),
        fillColor: surface.fillColor,
        fillAlpha: surface.fillAlpha,
        strokeColor: surface.strokeColor,
        strokeAlpha: surface.strokeAlpha,
        strokeWidth: surface.strokeWidth,
      });
    }
  }

  colliders.push(
    compileFlipperCollider(spec.flippers.left, flipperBodyIds.left),
    compileFlipperCollider(spec.flippers.right, flipperBodyIds.right),
  );

  return {
    id: spec.id,
    name: spec.name,
    version: spec.version,
    board: spec.board,
    ballsPerGame: spec.ballsPerGame,
    gravity: spec.gravity,
    ball: spec.ball,
    launcher: spec.launcher,
    flippers: spec.flippers,
    bumpers: spec.bumpers,
    slings: spec.slings,
    rollovers: spec.rollovers,
    tripwires: spec.tripwires,
    gates: spec.gates,
    standupTargets: spec.standupTargets,
    popupTargets: spec.popupTargets,
    drain: spec.drain,
    surfaces,
    physics: {
      bodies,
      colliders,
      spawns: spec.spawns,
    },
    render: {
      nodes: renderNodes,
    },
    refs: {
      staticBodyId,
      flipperBodyIds,
    },
  };
}

function compileFlipperCollider(
  flipper: PinballTableSpec["flippers"]["left"],
  bodyId: string,
): TableColliderPlan {
  const halfLength = flipper.length / 2;
  const xOffset = flipper.side === "left" ? halfLength : -halfLength;

  return {
    id: `${bodyId}:collider`,
    bodyId,
    translation: v(xOffset, 0),
    rotationRad: 0,
    shape: { kind: "cuboid", halfExtents: v(halfLength, flipper.thickness / 2) },
    sensor: false,
    surfaceId: "flipper",
  };
}

function mergeSurfaceIndex(
  userSurfaces: readonly TableSurfaceSpec[] | undefined,
): Readonly<Record<string, TableSurfaceSpec>> {
  const out: Record<string, TableSurfaceSpec> = { ...DEFAULT_TABLE_SURFACES };
  for (const surface of userSurfaces ?? []) {
    out[surface.id] = surface;
  }
  return out;
}

function assertValidTableSpec(spec: PinballTableSpec): void {
  const seenIds = new Set<string>();
  const registerId = (id: string, kind: string) => {
    if (seenIds.has(id)) {
      throw new Error(`Duplicate ${kind} id "${id}".`);
    }
    seenIds.add(id);
  };

  registerId(spec.id, "table");
  for (const spawn of spec.spawns) registerId(spawn.id, "spawn");
  for (const rail of spec.rails) {
    registerId(rail.id, "rail");
    if (rail.path.length < 2) {
      throw new Error(`Rail "${rail.id}" must have at least two points.`);
    }
  }
  for (const wall of spec.walls ?? []) registerId(wall.id, "wall");
  for (const post of spec.posts ?? []) registerId(post.id, "post");
  for (const surface of spec.renderSurfaces ?? []) registerId(surface.id, "render surface");

  const seenSemanticTags = new Set<string>();
  const registerSemanticTag = (tag: string, kind: string) => {
    if (seenSemanticTags.has(tag)) {
      throw new Error(`Duplicate ${kind} tag "${tag}".`);
    }
    seenSemanticTags.add(tag);
  };

  for (const bumper of spec.bumpers) registerSemanticTag(bumper.tag, "bumper");
  for (const sling of spec.slings) registerSemanticTag(sling.tag, "sling");
  for (const rollover of spec.rollovers) registerSemanticTag(rollover.tag, "rollover");
  for (const tripwire of spec.tripwires) registerSemanticTag(tripwire.tag, "tripwire");
  for (const gate of spec.gates) registerSemanticTag(gate.tag, "gate");
  for (const target of spec.standupTargets) registerSemanticTag(target.tag, "standup target");
  for (const target of spec.popupTargets) registerSemanticTag(target.tag, "popup target");
  registerSemanticTag(spec.drain.tag, "drain");

  if (spec.board.width <= 0 || spec.board.height <= 0) {
    throw new Error("Table board dimensions must be positive.");
  }
}
