/**
 * Shared typed table-definition contracts for Flunk-Out Frenzy.
 *
 * The authored prototype table stays in TypeScript for now, but these shared
 * shapes keep geometry and device semantics reusable across physics, rules, and
 * rendering as the local runtime grows beyond the first vertical slice.
 */

export interface TablePoint {
  x: number;
  y: number;
}

export interface TableWallDefinition {
  from: TablePoint;
  to: TablePoint;
}

export interface TableBumperDefinition {
  tag: string;
  x: number;
  y: number;
  radius: number;
  sensorRadius: number;
  impulse: number;
}

export interface TableSlingDefinition {
  tag: string;
  side: "left" | "right";
  vertices: [TablePoint, TablePoint, TablePoint];
  impulse: TablePoint;
}

export interface TableRolloverDefinition {
  tag: string;
  label: string;
  x: number;
  y: number;
  width: number;
  height: number;
  bankTag?: string;
}

export interface TableTripwireDefinition {
  tag: string;
  x: number;
  y: number;
  width: number;
  height: number;
  laneTag?: string;
}

export interface TableGateDefinition {
  tag: string;
  x: number;
  y: number;
  width: number;
  height: number;
  laneTag?: string;
}

export interface TableStandupTargetDefinition {
  tag: string;
  x: number;
  y: number;
  width: number;
  height: number;
  angleDeg?: number;
  bankTag?: string;
}

export interface TablePopupTargetDefinition {
  tag: string;
  x: number;
  y: number;
  radius: number;
  sensorRadius: number;
  bankTag?: string;
}

export interface TableFlipperDefinition {
  side: "left" | "right";
  pivot: TablePoint;
  length: number;
  thickness: number;
  restAngleDeg: number;
  activeAngleDeg: number;
  assistImpulse: TablePoint;
}
