import { degreesToRadians, v } from "../pinballTableMath";
import type {
  TableColliderPlan,
  TableRenderNodePlan,
} from "../pinballTablePlanTypes";
import type { PinballTableSpec } from "../pinballTablePlanTypes";
import type { CompilerContext, CompilerOutput } from "./compilerTypes";

export function compileStandupTargets(
  targets: PinballTableSpec["standupTargets"],
  context: CompilerContext,
): CompilerOutput {
  const colliders: TableColliderPlan[] = [];
  const renderNodes: TableRenderNodePlan[] = [];

  for (const target of targets) {
    const rotationRad = degreesToRadians(target.angleDeg ?? 0);
    colliders.push({
      id: `${target.tag}:body`,
      bodyId: context.staticBodyId,
      translation: { x: target.x, y: target.y },
      rotationRad,
      shape: {
        kind: "cuboid",
        halfExtents: v(target.width / 2, target.height / 2),
      },
      sensor: false,
      surfaceId: "wall",
    });
    colliders.push({
      id: `${target.tag}:sensor`,
      bodyId: context.staticBodyId,
      translation: { x: target.x, y: target.y },
      rotationRad,
      shape: {
        kind: "cuboid",
        halfExtents: v(target.width / 2 + 2, target.height / 2 + 2),
      },
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

  return { colliders, renderNodes };
}

export function compilePopupTargets(
  targets: PinballTableSpec["popupTargets"],
  context: CompilerContext,
): CompilerOutput {
  const colliders: TableColliderPlan[] = [];
  const renderNodes: TableRenderNodePlan[] = [];

  for (const target of targets) {
    colliders.push({
      id: `${target.tag}:body`,
      bodyId: context.staticBodyId,
      translation: { x: target.x, y: target.y },
      rotationRad: 0,
      shape: { kind: "circle", radius: target.radius },
      sensor: false,
      surfaceId: "wall",
    });
    colliders.push({
      id: `${target.tag}:sensor`,
      bodyId: context.staticBodyId,
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

  return { colliders, renderNodes };
}

export function compileCaptureDevices(
  captureDevices: PinballTableSpec["captureDevices"],
  context: CompilerContext,
): CompilerOutput {
  const colliders: TableColliderPlan[] = [];
  const renderNodes: TableRenderNodePlan[] = [];

  for (const capture of captureDevices) {
    colliders.push({
      id: `${capture.tag}:sensor`,
      bodyId: context.staticBodyId,
      translation: { x: capture.x, y: capture.y },
      rotationRad: 0,
      shape: {
        kind: "cuboid",
        halfExtents: v(capture.width / 2, capture.height / 2),
      },
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

  return { colliders, renderNodes };
}

export function compileSaveDevices(
  saveDevices: PinballTableSpec["saveDevices"],
  context: CompilerContext,
): CompilerOutput {
  const colliders: TableColliderPlan[] = [];
  const renderNodes: TableRenderNodePlan[] = [];

  for (const save of saveDevices) {
    colliders.push({
      id: `${save.tag}:sensor`,
      bodyId: context.staticBodyId,
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

  return { colliders, renderNodes };
}

export function compileRenderSurfaces(
  surfaces: PinballTableSpec["renderSurfaces"] = [],
): CompilerOutput {
  const renderNodes: TableRenderNodePlan[] = [];

  for (const surface of surfaces) {
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

  return { colliders: [], renderNodes };
}
