/**
 * Static gameplay-board underlay for Flunk-Out Frenzy.
 *
 * The browser board should render from the compiled table plan, not from a
 * second bespoke sketch. This module draws the static field chrome plus the
 * compiled render nodes emitted by the pinball-table compiler.
 */

import { BlurFilter, Container, Graphics } from "pixi.js";

import type { TableRenderNodePlan } from "../table/pinballTablePlanTypes";
import { PROTOTYPE_ALPHA_TABLE } from "../table/prototypeAlphaTable";

const RENDER_LAYER_ORDER: Readonly<Record<string, number>> = Object.freeze({
  field: 10,
  lanes: 20,
  walls: 30,
  posts: 40,
  "bumper-halos": 50,
  bumpers: 60,
  slings: 70,
  targets: 80,
  "popup-target-halos": 90,
  "popup-targets": 100,
  drain: 110,
  debug: 999,
});

export function buildStaticBoardUnderlay(container: Container): void {
  const board = new Graphics();
  board.roundRect(0, 0, PROTOTYPE_ALPHA_TABLE.board.width, PROTOTYPE_ALPHA_TABLE.board.height, 42);
  board.fill({
    color: 0x0f1714,
  });
  board.stroke({
    color: 0x4c6b5e,
    alpha: 0.6,
    width: 4,
  });
  container.addChild(board);

  const boardGlow = new Graphics();
  boardGlow.roundRect(16, 16, PROTOTYPE_ALPHA_TABLE.board.width - 32, PROTOTYPE_ALPHA_TABLE.board.height - 32, 34);
  boardGlow.stroke({
    color: 0xa7dd9a,
    alpha: 0.12,
    width: 16,
  });
  boardGlow.filters = [new BlurFilter({ strength: 6 })];
  container.addChild(boardGlow);

  const field = new Graphics();
  field.roundRect(36, 82, PROTOTYPE_ALPHA_TABLE.board.width - 72, PROTOTYPE_ALPHA_TABLE.board.height - 156, 28);
  field.fill({
    color: 0x16231e,
  });
  field.stroke({
    color: 0x7dbf8a,
    alpha: 0.18,
    width: 2,
  });
  container.addChild(field);

  const renderNodes = [...PROTOTYPE_ALPHA_TABLE.render.nodes].sort(
    (left, right) => resolveLayerOrder(left.layer) - resolveLayerOrder(right.layer),
  );
  for (const node of renderNodes) {
    const graphic = new Graphics();
    drawRenderNode(graphic, node);
    container.addChild(graphic);
  }
}

function drawRenderNode(graphic: Graphics, node: TableRenderNodePlan): void {
  switch (node.kind) {
    case "polyline":
      drawPolyline(graphic, node);
      return;
    case "circle":
      drawCircle(graphic, node);
      return;
    case "polygon":
      drawPolygon(graphic, node);
      return;
    case "rect":
      drawRect(graphic, node);
      return;
  }
}

function drawPolyline(
  graphic: Graphics,
  node: Extract<TableRenderNodePlan, { kind: "polyline" }>,
): void {
  if (node.points.length === 0) {
    return;
  }

  graphic.moveTo(node.points[0].x, node.points[0].y);
  for (let index = 1; index < node.points.length; index += 1) {
    graphic.lineTo(node.points[index].x, node.points[index].y);
  }

  const style = resolvePolylineStyle(node.layer, node.thickness);
  graphic.stroke(style);
}

function drawCircle(
  graphic: Graphics,
  node: Extract<TableRenderNodePlan, { kind: "circle" }>,
): void {
  graphic.position.set(node.center.x, node.center.y);
  graphic.circle(0, 0, node.radius);

  const style = resolveCircleStyle(node.layer);
  if (style.fillColor !== undefined && style.fillAlpha > 0) {
    graphic.fill({
      color: style.fillColor,
      alpha: style.fillAlpha,
    });
  }

  if (style.strokeColor !== undefined && style.strokeWidth > 0) {
    graphic.stroke({
      color: style.strokeColor,
      alpha: style.strokeAlpha,
      width: style.strokeWidth,
    });
  }
}

function drawPolygon(
  graphic: Graphics,
  node: Extract<TableRenderNodePlan, { kind: "polygon" }>,
): void {
  graphic.poly([...node.points]);

  applyFillAndStroke(graphic, {
    fillColor: node.fillColor,
    fillAlpha: node.fillAlpha,
    strokeColor: node.strokeColor,
    strokeAlpha: node.strokeAlpha,
    strokeWidth: node.strokeWidth,
  });
}

function drawRect(
  graphic: Graphics,
  node: Extract<TableRenderNodePlan, { kind: "rect" }>,
): void {
  graphic.position.set(node.center.x, node.center.y);
  graphic.rotation = node.rotationRad;
  graphic.rect(-node.width / 2, -node.height / 2, node.width, node.height);

  applyFillAndStroke(graphic, {
    fillColor: node.fillColor,
    fillAlpha: node.fillAlpha,
    strokeColor: node.strokeColor,
    strokeAlpha: node.strokeAlpha,
    strokeWidth: node.strokeWidth,
  });
}

function applyFillAndStroke(
  graphic: Graphics,
  style: {
    fillColor?: number;
    fillAlpha?: number;
    strokeColor?: number;
    strokeAlpha?: number;
    strokeWidth?: number;
  },
): void {
  if (style.fillColor !== undefined && (style.fillAlpha ?? 0) > 0) {
    graphic.fill({
      color: style.fillColor,
      alpha: style.fillAlpha ?? 1,
    });
  }

  if (style.strokeColor !== undefined && (style.strokeWidth ?? 0) > 0) {
    graphic.stroke({
      color: style.strokeColor,
      alpha: style.strokeAlpha ?? 0.2,
      width: style.strokeWidth ?? 1,
      join: "round",
    });
  }
}

function resolveLayerOrder(layer: string): number {
  return RENDER_LAYER_ORDER[layer] ?? 500;
}

function resolvePolylineStyle(layer: string, thickness: number) {
  switch (layer) {
    case "walls":
      return {
        color: 0xf2fff6,
        alpha: 0.58,
        width: Math.max(thickness * 0.52, 2.4),
        cap: "round" as const,
        join: "round" as const,
      };
    default:
      return {
        color: 0xcfe9d7,
        alpha: 0.28,
        width: Math.max(thickness * 0.4, 1.6),
        cap: "round" as const,
        join: "round" as const,
      };
  }
}

function resolveCircleStyle(layer: string): {
  fillColor?: number;
  fillAlpha: number;
  strokeColor?: number;
  strokeAlpha: number;
  strokeWidth: number;
} {
  switch (layer) {
    case "bumper-halos":
      return {
        fillColor: 0x61ff7d,
        fillAlpha: 0.08,
        strokeAlpha: 0,
        strokeWidth: 0,
      };
    case "bumpers":
      return {
        fillColor: 0x244634,
        fillAlpha: 0.96,
        strokeColor: 0xc7ffe0,
        strokeAlpha: 0.7,
        strokeWidth: 2,
      };
    case "popup-target-halos":
      return {
        fillColor: 0xff8df0,
        fillAlpha: 0.08,
        strokeAlpha: 0,
        strokeWidth: 0,
      };
    case "popup-targets":
      return {
        fillColor: 0x44263f,
        fillAlpha: 0.96,
        strokeColor: 0xffd7f7,
        strokeAlpha: 0.68,
        strokeWidth: 2,
      };
    case "posts":
      return {
        fillColor: 0x14201c,
        fillAlpha: 0.96,
        strokeColor: 0xa9d9bf,
        strokeAlpha: 0.36,
        strokeWidth: 1.5,
      };
    default:
      return {
        fillColor: 0xcfe9d7,
        fillAlpha: 0.14,
        strokeColor: 0xe4fff0,
        strokeAlpha: 0.28,
        strokeWidth: 1.5,
      };
  }
}
