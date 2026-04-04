import { v } from "../pinballTableMath";
import type {
  TableColliderPlan,
  TableRenderNodePlan,
} from "../pinballTablePlanTypes";
import type { PinballTableSpec } from "../pinballTablePlanTypes";
import type { CompilerContext, CompilerOutput } from "./compilerTypes";

export function compileBumpers(
  bumpers: PinballTableSpec["bumpers"],
  context: CompilerContext,
): CompilerOutput {
  const colliders: TableColliderPlan[] = [];
  const renderNodes: TableRenderNodePlan[] = [];

  for (const bumper of bumpers) {
    colliders.push({
      id: `${bumper.tag}:body`,
      bodyId: context.staticBodyId,
      translation: { x: bumper.x, y: bumper.y },
      rotationRad: 0,
      shape: { kind: "circle", radius: bumper.radius },
      sensor: false,
      surfaceId: "bumper",
    });
    colliders.push({
      id: `${bumper.tag}:sensor`,
      bodyId: context.staticBodyId,
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

  return { colliders, renderNodes };
}

export function compileSlings(
  slings: PinballTableSpec["slings"],
  context: CompilerContext,
): CompilerOutput {
  const colliders: TableColliderPlan[] = [];
  const renderNodes: TableRenderNodePlan[] = [];

  for (const sling of slings) {
    colliders.push({
      id: `${sling.tag}:body`,
      bodyId: context.staticBodyId,
      translation: v(0, 0),
      rotationRad: 0,
      shape: { kind: "triangle", vertices: sling.vertices },
      sensor: false,
      surfaceId: "wall",
    });
    colliders.push({
      id: `${sling.tag}:sensor`,
      bodyId: context.staticBodyId,
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

  return { colliders, renderNodes };
}
