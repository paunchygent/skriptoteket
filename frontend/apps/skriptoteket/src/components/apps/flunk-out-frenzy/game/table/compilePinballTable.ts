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
import type {
  TableGateDefinition,
  TablePoint,
  TableRegionShapeDefinition,
  TableTripwireDefinition,
  TableTriggerShapeDefinition,
} from "./tableDefinitionTypes";

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
      if (railSegmentIntersectsPlayfieldContactZ(rail, index, spec.launcher.threeD.ballRestZ)) {
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

  for (const wall of spec.walls ?? []) {
    if (wallIntersectsPlayfieldContactZ(wall, spec.launcher.threeD.ballRestZ)) {
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
    }

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

  for (const solid of spec.solids ?? []) {
    if (solidIntersectsPlayfieldContactZ(solid, spec.launcher.threeD.ballRestZ)) {
      colliders.push({
        id: `${solid.id}:body`,
        bodyId: staticBodyId,
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
    const triggerShape = resolveTriggerShapeDefinition(tripwire);
    const compiledShape = compileTriggerColliderGeometry(triggerShape);
    colliders.push({
      id: `${tripwire.tag}:sensor`,
      bodyId: staticBodyId,
      translation: compiledShape.translation,
      rotationRad: compiledShape.rotationRad,
      shape: compiledShape.shape,
      sensor: true,
      surfaceId: "sensor",
      semanticKind: "tripwire",
      tag: tripwire.tag,
      trigger: {
        shape: triggerShape,
        phase: tripwire.triggerPhase ?? "enter",
      },
    });
  }

  for (const gate of spec.gates) {
    const triggerShape = resolveTriggerShapeDefinition(gate);
    const compiledShape = compileTriggerColliderGeometry(triggerShape);
    colliders.push({
      id: `${gate.tag}:sensor`,
      bodyId: staticBodyId,
      translation: compiledShape.translation,
      rotationRad: compiledShape.rotationRad,
      shape: compiledShape.shape,
      sensor: true,
      surfaceId: "sensor",
      semanticKind: "gate",
      tag: gate.tag,
      trigger: {
        shape: triggerShape,
        phase: gate.triggerPhase ?? "enter",
      },
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

  for (const capture of spec.captureDevices) {
    colliders.push({
      id: `${capture.tag}:sensor`,
      bodyId: staticBodyId,
      translation: { x: capture.x, y: capture.y },
      rotationRad: 0,
      shape: { kind: "cuboid", halfExtents: v(capture.width / 2, capture.height / 2) },
      sensor: true,
      surfaceId: "sensor",
      semanticKind: "capture",
      tag: capture.tag,
      captureDeviceKind: capture.kind,
      holdMs: capture.holdMs,
      cooldownMs: capture.cooldownMs,
      ejectImpulse: capture.ejectImpulse,
    });

    renderNodes.push({
      kind: "rect",
      id: `${capture.tag}:render`,
      layer: "capture-devices",
      center: { x: capture.x, y: capture.y },
      width: capture.width,
      height: capture.height,
      rotationRad: 0,
      fillColor: 0x8dffcf,
      fillAlpha: 0.1,
      strokeColor: 0xc7ffe5,
      strokeAlpha: 0.4,
      strokeWidth: 2,
    });
  }

  for (const save of spec.saveDevices) {
    colliders.push({
      id: `${save.tag}:sensor`,
      bodyId: staticBodyId,
      translation: { x: save.x, y: save.y },
      rotationRad: 0,
      shape: { kind: "cuboid", halfExtents: v(save.width / 2, save.height / 2) },
      sensor: true,
      surfaceId: "sensor",
      semanticKind: "save",
      tag: save.tag,
      saveDeviceKind: save.kind,
      cooldownMs: save.cooldownMs,
      saveImpulse: save.saveImpulse,
    });

    renderNodes.push({
      kind: "rect",
      id: `${save.tag}:render`,
      layer: "save-devices",
      center: { x: save.x, y: save.y },
      width: save.width,
      height: save.height,
      rotationRad: 0,
      fillColor: 0x8db6ff,
      fillAlpha: 0.1,
      strokeColor: 0xdbe7ff,
      strokeAlpha: 0.42,
      strokeWidth: 2,
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
    if (surface.kind === "polyline") {
      renderNodes.push({
        kind: "polyline",
        id: surface.id,
        layer: surface.layer ?? "field",
        points: surface.points,
        thickness: surface.thickness,
      });
    } else if (surface.kind === "polygon") {
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
    captureDevices: spec.captureDevices,
    saveDevices: spec.saveDevices,
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

function resolveTriggerShapeDefinition(
  definition: TableTripwireDefinition | TableGateDefinition,
): TableTriggerShapeDefinition {
  if ("shape" in definition) {
    return definition.shape;
  }

  return {
    kind: "rect",
    center: { x: definition.x, y: definition.y },
    width: definition.width,
    height: definition.height,
    angleDeg: definition.angleDeg,
  };
}

function compileTriggerColliderGeometry(shape: TableTriggerShapeDefinition): Readonly<{
  translation: TablePoint;
  rotationRad: number;
  shape: TableColliderPlan["shape"];
}> {
  switch (shape.kind) {
    case "rect":
      return {
        translation: shape.center,
        rotationRad: degreesToRadians(shape.angleDeg ?? 0),
        shape: { kind: "cuboid", halfExtents: v(shape.width / 2, shape.height / 2) },
      };
    case "circle":
      return {
        translation: shape.center,
        rotationRad: 0,
        shape: { kind: "circle", radius: shape.radius },
      };
    case "polygon":
      return {
        translation: v(0, 0),
        rotationRad: 0,
        shape: { kind: "convex-polygon", vertices: shape.points },
      };
    case "capsule":
      return {
        translation: shape.center,
        rotationRad: degreesToRadians(shape.angleDeg ?? 0),
        shape: { kind: "thick-segment", halfLength: shape.length / 2, radius: shape.radius },
      };
    case "donor-wire-rollover":
      return {
        translation: shape.center,
        rotationRad: degreesToRadians(shape.angleDeg ?? 0),
        shape: {
          kind: "thick-segment",
          halfLength: shape.wireLength / 2,
          radius: shape.wireRadius,
        },
      };
  }
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
    if (rail.zPath && rail.zPath.length !== rail.path.length) {
      throw new Error(`Rail "${rail.id}" zPath length must match path length.`);
    }
    if ((rail.heightBottom === undefined) !== (rail.heightTop === undefined)) {
      throw new Error(
        `Rail "${rail.id}" must declare both heightBottom and heightTop when using elevation bounds.`,
      );
    }
    if (rail.heightBottom !== undefined && rail.heightTop !== undefined
      && rail.heightTop < rail.heightBottom) {
      throw new Error(`Rail "${rail.id}" must not invert height bounds.`);
    }
  }
  for (const wall of spec.walls ?? []) {
    registerId(wall.id, "wall");
    if ((wall.heightBottom === undefined) !== (wall.heightTop === undefined)) {
      throw new Error(
        `Wall "${wall.id}" must declare both heightBottom and heightTop when using elevation bounds.`,
      );
    }
    if (wall.heightBottom !== undefined && wall.heightTop !== undefined
      && wall.heightTop < wall.heightBottom) {
      throw new Error(`Wall "${wall.id}" must not invert height bounds.`);
    }
  }
  for (const post of spec.posts ?? []) registerId(post.id, "post");
  for (const solid of spec.solids ?? []) {
    registerId(solid.id, "solid");
    if (solid.points.length < 3) {
      throw new Error(`Solid "${solid.id}" must have at least three points.`);
    }
    if ((solid.heightBottom === undefined) !== (solid.heightTop === undefined)) {
      throw new Error(
        `Solid "${solid.id}" must declare both heightBottom and heightTop when using elevation bounds.`,
      );
    }
    if (solid.heightBottom !== undefined && solid.heightTop !== undefined
      && solid.heightTop < solid.heightBottom) {
      throw new Error(`Solid "${solid.id}" must not invert height bounds.`);
    }
  }
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
  for (const capture of spec.captureDevices) registerSemanticTag(capture.tag, "capture device");
  for (const save of spec.saveDevices) registerSemanticTag(save.tag, "save device");
  registerSemanticTag(spec.drain.tag, "drain");

  if (spec.board.width <= 0 || spec.board.height <= 0) {
    throw new Error("Table board dimensions must be positive.");
  }

  if (spec.launcher.laneRegions.length === 0) {
    throw new Error('Launcher "launcher/main" must declare at least one lane region.');
  }

  if (spec.launcher.threeD.walls.length === 0) {
    throw new Error('Launcher "launcher/main" must declare at least one 3D wall section.');
  }

  if (spec.launcher.threeD.sensors.length === 0) {
    throw new Error('Launcher "launcher/main" must declare at least one 3D launcher sensor.');
  }

  if (spec.launcher.threeD.guideRails.length === 0) {
    throw new Error('Launcher "launcher/main" must declare at least one 3D launcher guide rail.');
  }

  for (const [index, region] of spec.launcher.laneRegions.entries()) {
    assertValidLauncherRegionDefinition(`${spec.launcher.tag}[${index}]`, region);
  }

  for (const wall of spec.launcher.threeD.walls) {
    if (wall.points.length < 3) {
      throw new Error(`Launcher 3D wall "${wall.tag}" must have at least three points.`);
    }
    if (wall.heightTop < wall.heightBottom) {
      throw new Error(`Launcher 3D wall "${wall.tag}" must not invert height bounds.`);
    }
  }

  for (const rail of spec.launcher.threeD.guideRails) {
    if (rail.path.length < 2) {
      throw new Error(`Launcher 3D guide rail "${rail.tag}" must have at least two points.`);
    }
    if (rail.radius <= 0) {
      throw new Error(`Launcher 3D guide rail "${rail.tag}" must have a positive radius.`);
    }
    if (rail.heightTop < rail.heightBottom) {
      throw new Error(`Launcher 3D guide rail "${rail.tag}" must not invert height bounds.`);
    }
  }

  for (const sensor of spec.launcher.threeD.sensors) {
    assertValidTriggerDefinition(sensor.tag, sensor.shape);
  }

  if (spec.launcher.threeD.plunger.width <= 0
    || spec.launcher.threeD.plunger.depth <= 0
    || spec.launcher.threeD.plunger.height <= 0
    || spec.launcher.threeD.plunger.stroke <= 0) {
    throw new Error('Launcher 3D plunger must declare positive width/depth/height/stroke.');
  }

  for (const tripwire of spec.tripwires) {
    assertValidTriggerDefinition(tripwire.tag, resolveTriggerShapeDefinition(tripwire));
  }

  for (const gate of spec.gates) {
    assertValidTriggerDefinition(gate.tag, resolveTriggerShapeDefinition(gate));
  }

  for (const capture of spec.captureDevices) {
    if (capture.width <= 0 || capture.height <= 0) {
      throw new Error(`Capture device "${capture.tag}" must have positive bounds.`);
    }
    if (capture.holdMs < 0) {
      throw new Error(`Capture device "${capture.tag}" holdMs must be >= 0.`);
    }
    if (capture.cooldownMs < 0) {
      throw new Error(`Capture device "${capture.tag}" cooldownMs must be >= 0.`);
    }
    if (magnitude(capture.ejectImpulse) <= 0) {
      throw new Error(`Capture device "${capture.tag}" must have a non-zero eject impulse.`);
    }
  }

  for (const save of spec.saveDevices) {
    if (save.width <= 0 || save.height <= 0) {
      throw new Error(`Save device "${save.tag}" must have positive bounds.`);
    }
    if (save.cooldownMs < 0) {
      throw new Error(`Save device "${save.tag}" cooldownMs must be >= 0.`);
    }
    if (magnitude(save.saveImpulse) <= 0) {
      throw new Error(`Save device "${save.tag}" must have a non-zero save impulse.`);
    }
  }
}

function assertValidTriggerDefinition(tag: string, shape: TableTriggerShapeDefinition): void {
  switch (shape.kind) {
    case "rect":
      if (shape.width <= 0 || shape.height <= 0) {
        throw new Error(`Trigger "${tag}" rect shape must have positive bounds.`);
      }
      return;
    case "circle":
      if (shape.radius <= 0) {
        throw new Error(`Trigger "${tag}" circle shape must have a positive radius.`);
      }
      return;
    case "polygon":
      if (shape.points.length < 3) {
        throw new Error(`Trigger "${tag}" polygon shape must have at least three points.`);
      }
      return;
    case "capsule":
      if (shape.length <= 0 || shape.radius <= 0) {
        throw new Error(`Trigger "${tag}" capsule shape must have positive length and radius.`);
      }
      return;
    case "donor-wire-rollover":
      if (shape.wireLength <= 0 || shape.wireRadius <= 0) {
        throw new Error(
          `Trigger "${tag}" donor wire-rollover shape must have positive wire length and radius.`,
        );
      }
      return;
  }
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

function assertValidLauncherRegionDefinition(
  label: string,
  shape: TableRegionShapeDefinition,
): void {
  switch (shape.kind) {
    case "rect":
      if (shape.width <= 0 || shape.height <= 0) {
        throw new Error(`Launcher region "${label}" rect shape must have positive bounds.`);
      }
      return;
    case "circle":
      if (shape.radius <= 0) {
        throw new Error(`Launcher region "${label}" circle shape must have a positive radius.`);
      }
      return;
    case "polygon":
      if (shape.points.length < 3) {
        throw new Error(`Launcher region "${label}" polygon shape must have at least three points.`);
      }
      return;
    case "capsule":
      if (shape.length <= 0 || shape.radius <= 0) {
        throw new Error(
          `Launcher region "${label}" capsule shape must have positive length and radius.`,
        );
      }
      return;
    case "donor-corridor":
      if (shape.leftBoundary.length < 2 || shape.rightBoundary.length < 2) {
        throw new Error(
          `Launcher region "${label}" donor corridor must have at least two points per boundary.`,
        );
      }
      return;
  }
}
