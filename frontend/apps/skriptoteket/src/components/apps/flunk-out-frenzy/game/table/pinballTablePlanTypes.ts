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
  TableCaptureDeviceDefinition,
  TableCaptureDeviceKind,
  TableDrainDefinition,
  TableFlipperDefinition,
  TableGateDefinition,
  TableLauncherCarrierKind,
  TableLauncherDefinition,
  TablePoint,
  TablePoint3D,
  TablePopupTargetDefinition,
  TableRolloverDefinition,
  TableSaveDeviceDefinition,
  TableSaveDeviceKind,
  TableSlingDefinition,
  TableStandupTargetDefinition,
  TableTriggerPhaseDefinition,
  TableTriggerShapeDefinition,
  TableTripwireDefinition,
} from "./tableDefinitionTypes";

export type {
  TableLauncherCarrierKind,
  TableLauncherCarrier3DDefinition,
  TableLauncherHandoffSeam3DDefinition,
  TableLauncherObservationSpine3DDefinition,
  TableLauncherPlunger3DDefinition,
  TableLauncherPhysicalCarrier3DDefinition,
  TableLauncherSensor3DDefinition,
  TablePoint3D,
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
  /**
   * Optional per-point donor z profile. If provided, this must match `path`
   * length so segment-level z bands can be preserved without inventing local
   * flattening seams.
   */
  zPath?: readonly number[];
  radius: number;
  /**
   * Optional donor elevation band for rails whose contact path lives above the
   * playfield contact plane.
   */
  heightBottom?: number;
  heightTop?: number;
  donorSourceId?: string;
  physics?: boolean;
  surfaceId?: string;
  renderLayer?: string;
  render?: boolean;
}

export interface TableWallSpec {
  id: string;
  a: TablePoint;
  b: TablePoint;
  radius: number;
  heightBottom?: number;
  heightTop?: number;
  donorSourceId?: string;
  physics?: boolean;
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

export interface TableSolidSpec {
  id: string;
  points: readonly TablePoint[];
  /**
   * Optional donor elevation range. When provided, the compiler only emits a
   * physical collider if the playfield ball-contact z intersects this band.
   * Render output is always emitted so elevated donor walls stay visible.
   */
  heightBottom?: number;
  heightTop?: number;
  surfaceId?: string;
  renderLayer?: string;
  fillColor?: number;
  fillAlpha?: number;
  strokeColor?: number;
  strokeAlpha?: number;
  strokeWidth?: number;
}

export type TableRenderSurfaceSpec =
  | Readonly<{
      kind: "polyline";
      id: string;
      points: readonly TablePoint[];
      thickness: number;
      layer?: string;
    }>
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
  captureDevices: readonly TableCaptureDeviceDefinition[];
  saveDevices: readonly TableSaveDeviceDefinition[];
  drain: TableDrainDefinition;
  spawns: readonly TableSpawnSpec[];
  rails: readonly TableRailSpec[];
  walls?: readonly TableWallSpec[];
  posts?: readonly TablePostSpec[];
  solids?: readonly TableSolidSpec[];
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
  | Readonly<{ kind: "convex-polygon"; vertices: readonly TablePoint[] }>
  | Readonly<{ kind: "triangle"; vertices: readonly [TablePoint, TablePoint, TablePoint] }>;

export type TriggerSemanticKind =
  | "bumper"
  | "sling"
  | "rollover"
  | "tripwire"
  | "gate"
  | "standup-target"
  | "popup-target"
  | "capture"
  | "save"
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
  captureDeviceKind?: TableCaptureDeviceKind;
  saveDeviceKind?: TableSaveDeviceKind;
  holdMs?: number;
  cooldownMs?: number;
  ejectImpulse?: TablePoint;
  saveImpulse?: TablePoint;
  trigger?: Readonly<{
    shape: TableTriggerShapeDefinition;
    phase: TableTriggerPhaseDefinition;
  }>;
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

export type CompiledLauncherWorldCarrierRole = Extract<
  TableLauncherCarrierKind,
  "support" | "guard" | "receiver"
>;

interface CompiledLauncherWorldAssemblyBase {
  id: string;
  role: CompiledLauncherWorldCarrierRole;
  ownerWorld: "launcher";
  donorSourceIds: readonly string[];
  sourceCarrierTags: readonly string[];
}

export interface CompiledLauncherWorldPrismHullAssemblyPlan
  extends CompiledLauncherWorldAssemblyBase {
  primitiveKind: "prism_hull";
  colliderIds: readonly [string];
  points: readonly TablePoint[];
  heightBottom: number;
  heightTop: number;
}

export interface CompiledLauncherWorldRoundConvexHullAssemblyPlan
  extends CompiledLauncherWorldAssemblyBase {
  primitiveKind: "round_convex_hull";
  colliderIds: readonly [string];
  points: readonly TablePoint3D[];
  borderRadius: number;
}

export interface CompiledLauncherWorldCuboidSegmentPathAssemblyPlan
  extends CompiledLauncherWorldAssemblyBase {
  primitiveKind: "cuboid_segment_path";
  colliderIds: readonly string[];
  path: readonly TablePoint3D[];
  halfWidth: number;
  halfHeight: number;
}

export interface CompiledLauncherWorldRoundCuboidSegmentPathAssemblyPlan
  extends CompiledLauncherWorldAssemblyBase {
  primitiveKind: "round_cuboid_segment_path";
  colliderIds: readonly string[];
  path: readonly TablePoint3D[];
  halfWidth: number;
  halfHeight: number;
  borderRadius: number;
}

export interface CompiledLauncherWorldCapsuleSegmentPathAssemblyPlan
  extends CompiledLauncherWorldAssemblyBase {
  primitiveKind: "capsule_segment_path";
  colliderIds: readonly string[];
  path: readonly TablePoint3D[];
  radius: number;
}

export type CompiledLauncherWorldAssemblyPlan =
  | CompiledLauncherWorldPrismHullAssemblyPlan
  | CompiledLauncherWorldRoundConvexHullAssemblyPlan
  | CompiledLauncherWorldCuboidSegmentPathAssemblyPlan
  | CompiledLauncherWorldRoundCuboidSegmentPathAssemblyPlan
  | CompiledLauncherWorldCapsuleSegmentPathAssemblyPlan;

export interface CompiledLauncherWorldOwnershipEntry {
  donorSourceId: string;
  colliderIds: readonly string[];
  role: CompiledLauncherWorldCarrierRole;
  ownerWorld: "launcher";
  assemblyIds: readonly string[];
}

export interface CompiledLauncherWorldPlan {
  assemblies: readonly CompiledLauncherWorldAssemblyPlan[];
  ownershipMatrix: readonly CompiledLauncherWorldOwnershipEntry[];
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
  captureDevices: readonly TableCaptureDeviceDefinition[];
  saveDevices: readonly TableSaveDeviceDefinition[];
  drain: TableDrainDefinition;
  surfaces: Readonly<Record<string, TableSurfaceSpec>>;
  launcherWorld: CompiledLauncherWorldPlan;
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
