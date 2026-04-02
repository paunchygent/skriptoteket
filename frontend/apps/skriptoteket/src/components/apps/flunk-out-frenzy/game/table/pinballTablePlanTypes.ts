/**
 * Authored and compiled pinball table planning contracts.
 *
 * The prototype table is authored as a readable spec and compiled into an
 * explicit physics/render plan so simulation and presentation consume the same
 * source of truth without relying on hand-maintained wall lists.
 */

import type {
  TableBallDefinition,
  TableBoardDefinition,
  TableBumperDefinition,
  TableDrainDefinition,
  TableFlipperDefinition,
  TableGateDefinition,
  TableLauncherDefinition,
  TablePoint,
  TablePopupTargetDefinition,
  TableRolloverDefinition,
  TableSlingDefinition,
  TableStandupTargetDefinition,
  TableTripwireDefinition,
} from "./tableDefinitionTypes";

export interface TableSurfaceSpec {
  id: string;
  friction: number;
  restitution: number;
  density?: number;
  linearDamping?: number;
  angularDamping?: number;
}

export interface TableSpawnSpec {
  id: string;
  position: TablePoint;
  launchVelocity?: TablePoint;
  tags?: readonly string[];
}

export interface TableRailSpec {
  id: string;
  path: readonly TablePoint[];
  radius: number;
  surfaceId?: string;
  renderLayer?: string;
}

export interface TableWallSpec {
  id: string;
  a: TablePoint;
  b: TablePoint;
  radius: number;
  surfaceId?: string;
  renderLayer?: string;
}

export interface TablePostSpec {
  id: string;
  center: TablePoint;
  radius: number;
  surfaceId?: string;
  renderLayer?: string;
}

export type TableRenderSurfaceSpec =
  | Readonly<{
      kind: "polygon";
      id: string;
      points: readonly TablePoint[];
      fillColor: number;
      fillAlpha: number;
      strokeColor?: number;
      strokeAlpha?: number;
      strokeWidth?: number;
      layer?: string;
    }>
  | Readonly<{
      kind: "rect";
      id: string;
      center: TablePoint;
      width: number;
      height: number;
      angleDeg?: number;
      fillColor: number;
      fillAlpha: number;
      strokeColor?: number;
      strokeAlpha?: number;
      strokeWidth?: number;
      layer?: string;
    }>;

export interface PinballTableSpec {
  id: string;
  name: string;
  version: number;
  board: TableBoardDefinition;
  ballsPerGame: number;
  gravity: TablePoint;
  ball: TableBallDefinition;
  launcher: TableLauncherDefinition;
  flippers: Record<"left" | "right", TableFlipperDefinition>;
  bumpers: readonly TableBumperDefinition[];
  slings: readonly TableSlingDefinition[];
  rollovers: readonly TableRolloverDefinition[];
  tripwires: readonly TableTripwireDefinition[];
  gates: readonly TableGateDefinition[];
  standupTargets: readonly TableStandupTargetDefinition[];
  popupTargets: readonly TablePopupTargetDefinition[];
  drain: TableDrainDefinition;
  spawns: readonly TableSpawnSpec[];
  rails: readonly TableRailSpec[];
  walls?: readonly TableWallSpec[];
  posts?: readonly TablePostSpec[];
  renderSurfaces?: readonly TableRenderSurfaceSpec[];
  surfaces?: readonly TableSurfaceSpec[];
}

export interface TableBodyPlan {
  id: string;
  type: "fixed" | "kinematic-position";
  translation: TablePoint;
  rotationRad: number;
}

export type TableColliderShapePlan =
  | Readonly<{ kind: "thick-segment"; halfLength: number; radius: number }>
  | Readonly<{ kind: "circle"; radius: number }>
  | Readonly<{ kind: "cuboid"; halfExtents: TablePoint }>
  | Readonly<{ kind: "triangle"; vertices: readonly [TablePoint, TablePoint, TablePoint] }>;

export type TriggerSemanticKind =
  | "bumper"
  | "sling"
  | "rollover"
  | "tripwire"
  | "gate"
  | "standup-target"
  | "popup-target"
  | "drain";

export interface TableColliderPlan {
  id: string;
  bodyId: string;
  translation: TablePoint;
  rotationRad: number;
  shape: TableColliderShapePlan;
  sensor: boolean;
  surfaceId: string;
  semanticKind?: TriggerSemanticKind;
  tag?: string;
  center?: TablePoint;
  impulse?: TablePoint;
  impulseMagnitude?: number;
  side?: "left" | "right";
}

export type TableRenderNodePlan =
  | Readonly<{
      kind: "polyline";
      id: string;
      layer: string;
      points: readonly TablePoint[];
      thickness: number;
    }>
  | Readonly<{
      kind: "circle";
      id: string;
      layer: string;
      center: TablePoint;
      radius: number;
    }>
  | Readonly<{
      kind: "polygon";
      id: string;
      layer: string;
      points: readonly TablePoint[];
      fillColor?: number;
      fillAlpha?: number;
      strokeColor?: number;
      strokeAlpha?: number;
      strokeWidth?: number;
    }>
  | Readonly<{
      kind: "rect";
      id: string;
      layer: string;
      center: TablePoint;
      width: number;
      height: number;
      rotationRad: number;
      fillColor?: number;
      fillAlpha?: number;
      strokeColor?: number;
      strokeAlpha?: number;
      strokeWidth?: number;
    }>;

export interface CompiledPhysicsPlan {
  bodies: readonly TableBodyPlan[];
  colliders: readonly TableColliderPlan[];
  spawns: readonly TableSpawnSpec[];
}

export interface CompiledRenderPlan {
  nodes: readonly TableRenderNodePlan[];
}

export interface CompiledPinballTable {
  id: string;
  name: string;
  version: number;
  board: TableBoardDefinition;
  ballsPerGame: number;
  gravity: TablePoint;
  ball: TableBallDefinition;
  launcher: TableLauncherDefinition;
  flippers: Record<"left" | "right", TableFlipperDefinition>;
  bumpers: readonly TableBumperDefinition[];
  slings: readonly TableSlingDefinition[];
  rollovers: readonly TableRolloverDefinition[];
  tripwires: readonly TableTripwireDefinition[];
  gates: readonly TableGateDefinition[];
  standupTargets: readonly TableStandupTargetDefinition[];
  popupTargets: readonly TablePopupTargetDefinition[];
  drain: TableDrainDefinition;
  surfaces: Readonly<Record<string, TableSurfaceSpec>>;
  physics: CompiledPhysicsPlan;
  render: CompiledRenderPlan;
  refs: Readonly<{
    staticBodyId: string;
    flipperBodyIds: Readonly<Record<"left" | "right", string>>;
  }>;
}

export const DEFAULT_TABLE_SURFACES: Readonly<Record<string, TableSurfaceSpec>> = Object.freeze({
  wall: Object.freeze({
    id: "wall",
    friction: 0.04,
    restitution: 0.08,
  }),
  post: Object.freeze({
    id: "post",
    friction: 0.03,
    restitution: 0.18,
  }),
  bumper: Object.freeze({
    id: "bumper",
    friction: 0.02,
    restitution: 0.85,
  }),
  flipper: Object.freeze({
    id: "flipper",
    friction: 0.06,
    restitution: 0.18,
    angularDamping: 2.0,
  }),
  sensor: Object.freeze({
    id: "sensor",
    friction: 0,
    restitution: 0,
  }),
});
