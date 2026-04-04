import { degreesToRadians, v } from "../pinballTableMath";
import type {
  TableColliderPlan,
  TableRenderNodePlan,
} from "../pinballTablePlanTypes";
import type { PinballTableSpec } from "../pinballTablePlanTypes";
import type {
  TableGateDefinition,
  TablePoint,
  TableTripwireDefinition,
  TableTriggerShapeDefinition,
} from "../tableDefinitionTypes";
import type { CompilerContext, CompilerOutput } from "./compilerTypes";

export function compileRollovers(
  rollovers: PinballTableSpec["rollovers"],
  context: CompilerContext,
): CompilerOutput {
  const colliders: TableColliderPlan[] = [];

  for (const rollover of rollovers) {
    colliders.push({
      id: `${rollover.tag}:sensor`,
      bodyId: context.staticBodyId,
      translation: { x: rollover.x, y: rollover.y },
      rotationRad: 0,
      shape: {
        kind: "cuboid",
        halfExtents: v(rollover.width / 2, rollover.height / 2),
      },
      sensor: true,
      surfaceId: "sensor",
      semanticKind: "rollover",
      tag: rollover.tag,
    });
  }

  return { colliders, renderNodes: [] };
}

export function compileTripwires(
  tripwires: PinballTableSpec["tripwires"],
  context: CompilerContext,
): CompilerOutput {
  const colliders: TableColliderPlan[] = [];

  for (const tripwire of tripwires) {
    const triggerShape = resolveTriggerShapeDefinition(tripwire);
    const compiledShape = compileTriggerColliderGeometry(triggerShape);
    colliders.push({
      id: `${tripwire.tag}:sensor`,
      bodyId: context.staticBodyId,
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

  return { colliders, renderNodes: [] };
}

export function compileGates(
  gates: PinballTableSpec["gates"],
  context: CompilerContext,
): CompilerOutput {
  const colliders: TableColliderPlan[] = [];

  for (const gate of gates) {
    const triggerShape = resolveTriggerShapeDefinition(gate);
    const compiledShape = compileTriggerColliderGeometry(triggerShape);
    colliders.push({
      id: `${gate.tag}:sensor`,
      bodyId: context.staticBodyId,
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

  return { colliders, renderNodes: [] };
}

export function compileDrain(
  drain: PinballTableSpec["drain"],
  context: CompilerContext,
): CompilerOutput {
  const colliders: TableColliderPlan[] = [
    {
      id: `${drain.tag}:sensor`,
      bodyId: context.staticBodyId,
      translation: { x: drain.x, y: drain.y },
      rotationRad: 0,
      shape: { kind: "cuboid", halfExtents: v(drain.width / 2, drain.height / 2) },
      sensor: true,
      surfaceId: "sensor",
      semanticKind: "drain",
      tag: drain.tag,
    },
  ];

  const renderNodes: TableRenderNodePlan[] = [
    {
      kind: "rect",
      id: `${drain.tag}:render`,
      layer: "drain",
      center: { x: drain.x, y: drain.y },
      width: drain.width,
      height: drain.height,
      rotationRad: 0,
      fillColor: 0x250f16,
      fillAlpha: 1,
      strokeColor: 0xff96b7,
      strokeAlpha: 0.38,
      strokeWidth: 2,
    },
  ];

  return { colliders, renderNodes };
}

export function resolveTriggerShapeDefinition(
  definition: TableTripwireDefinition | TableGateDefinition,
): TableTriggerShapeDefinition {
  if ("shape" in definition) {
    return (definition as { shape: TableTriggerShapeDefinition }).shape;
  }

  return {
    kind: "rect",
    center: { x: definition.x, y: definition.y },
    width: definition.width,
    height: definition.height,
    angleDeg: definition.angleDeg,
  };
}

export function compileTriggerColliderGeometry(
  shape: TableTriggerShapeDefinition,
): Readonly<{
  translation: TablePoint;
  rotationRad: number;
  shape: TableColliderPlan["shape"];
}> {
  switch (shape.kind) {
    case "rect":
      return {
        translation: shape.center,
        rotationRad: degreesToRadians(shape.angleDeg ?? 0),
        shape: {
          kind: "cuboid",
          halfExtents: v(shape.width / 2, shape.height / 2),
        },
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
        shape: {
          kind: "thick-segment",
          halfLength: shape.length / 2,
          radius: shape.radius,
        },
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
