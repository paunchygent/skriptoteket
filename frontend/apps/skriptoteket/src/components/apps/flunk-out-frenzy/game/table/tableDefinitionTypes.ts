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

export interface TablePoint3D {
  x: number;
  y: number;
  z: number;
}

export interface TableBoardDefinition {
  width: number;
  height: number;
  displayAspectRatio: number;
}

export interface TableBallDefinition {
  radius: number;
  spawn: TablePoint;
  mass: number;
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

export type TableTriggerPhaseDefinition = "enter" | "exit" | "both";

export interface TableRectTriggerShapeDefinition {
  kind: "rect";
  center: TablePoint;
  width: number;
  height: number;
  angleDeg?: number;
}

export interface TableCircleTriggerShapeDefinition {
  kind: "circle";
  center: TablePoint;
  radius: number;
}

export interface TablePolygonTriggerShapeDefinition {
  kind: "polygon";
  points: readonly TablePoint[];
}

export interface TableCapsuleTriggerShapeDefinition {
  kind: "capsule";
  center: TablePoint;
  length: number;
  radius: number;
  angleDeg?: number;
}

export interface TableCorridorRegionShapeDefinition {
  kind: "donor-corridor";
  leftBoundary: readonly TablePoint[];
  rightBoundary: readonly TablePoint[];
}

export interface TableDonorWireRolloverTriggerShapeDefinition {
  kind: "donor-wire-rollover";
  center: TablePoint;
  wireLength: number;
  wireRadius: number;
  angleDeg?: number;
  donorSourceId?: string;
}

export type TableTriggerShapeDefinition =
  | TableRectTriggerShapeDefinition
  | TableCircleTriggerShapeDefinition
  | TablePolygonTriggerShapeDefinition
  | TableCapsuleTriggerShapeDefinition
  | TableDonorWireRolloverTriggerShapeDefinition;

export type TableRegionShapeDefinition =
  | TableRectTriggerShapeDefinition
  | TableCircleTriggerShapeDefinition
  | TablePolygonTriggerShapeDefinition
  | TableCapsuleTriggerShapeDefinition
  | TableCorridorRegionShapeDefinition;

interface TableLegacyRectTriggerBoundsDefinition {
  x: number;
  y: number;
  width: number;
  height: number;
  angleDeg?: number;
}

interface TableTriggerDeviceDefinitionBase {
  tag: string;
  laneTag?: string;
  triggerPhase?: TableTriggerPhaseDefinition;
}

type TableTriggerDefinition =
  | (TableTriggerDeviceDefinitionBase & TableLegacyRectTriggerBoundsDefinition)
  | (TableTriggerDeviceDefinitionBase & { shape: TableTriggerShapeDefinition });

export type TableTripwireDefinition = TableTriggerDefinition;

export type TableGateDefinition = TableTriggerDefinition;

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

export type TableCaptureDeviceKind = "hole" | "kickout" | "sink";
export type TableSaveDeviceKind = "kickback" | "save-post";

export interface TableCaptureDeviceDefinition {
  tag: string;
  kind: TableCaptureDeviceKind;
  x: number;
  y: number;
  width: number;
  height: number;
  holdMs: number;
  cooldownMs: number;
  ejectImpulse: TablePoint;
}

export interface TableSaveDeviceDefinition {
  tag: string;
  kind: TableSaveDeviceKind;
  x: number;
  y: number;
  width: number;
  height: number;
  cooldownMs: number;
  saveImpulse: TablePoint;
}

export interface TableFlipperContactModelDefinition {
  minImpulse: number;
  maxImpulse: number;
  maxContactDistance: number;
  minContactRatio: number;
  maxContactRatio: number;
  liftBias: number;
  lateralBias: number;
}

export interface TableFlipperDefinition {
  side: "left" | "right";
  pivot: TablePoint;
  length: number;
  thickness: number;
  restAngleDeg: number;
  activeAngleDeg: number;
  contactModel: TableFlipperContactModelDefinition;
}

export type TableLauncherCarrierCompileRole =
  | "physical"
  | "observation"
  | "terminal_seam";

export type TableLauncherCarrierOwnerWorld = "launcher" | "board";

export type TableLauncherCarrierKind =
  | "support"
  | "guard"
  | "receiver"
  | "observation_spine"
  | "handoff_seam";

export type TableLauncherObservationEntryMode = "release" | "chain";

interface TableLauncherCarrierBaseDefinition {
  tag: string;
  kind: TableLauncherCarrierKind;
  compileRole: TableLauncherCarrierCompileRole;
  ownerWorld: TableLauncherCarrierOwnerWorld;
  donorSourceIds: readonly string[];
}

interface TableLauncherPhysicalCarrier3DBaseDefinition
  extends TableLauncherCarrierBaseDefinition {
  kind: "support" | "guard" | "receiver";
  compileRole: "physical";
  ownerWorld: "launcher";
  ownedDonorSpanIds: readonly string[];
  heightBottom: number;
  heightTop: number;
}

export interface TableLauncherExtrudedPolygonCarrier3DDefinition
  extends TableLauncherPhysicalCarrier3DBaseDefinition {
  geometryKind: "extruded_polygon";
  points: readonly TablePoint[];
}

export interface TableLauncherSegmentPathCarrier3DDefinition
  extends TableLauncherPhysicalCarrier3DBaseDefinition {
  geometryKind: "segment_path";
  path: readonly TablePoint[];
  radius: number;
}

export type TableLauncherPhysicalCarrier3DDefinition =
  | TableLauncherExtrudedPolygonCarrier3DDefinition
  | TableLauncherSegmentPathCarrier3DDefinition;

export interface TableLauncherSensor3DDefinition {
  tag: string;
  donorSourceIds: readonly string[];
  shape: TableTriggerShapeDefinition;
  triggerPhase: TableTriggerPhaseDefinition;
  semanticRole: "feed" | "exit";
}

export interface TableLauncherObservationSpine3DDefinition
  extends TableLauncherCarrierBaseDefinition {
  kind: "observation_spine";
  compileRole: "observation";
  ownerWorld: "launcher";
  path: readonly TablePoint3D[];
  entryMode?: TableLauncherObservationEntryMode;
  minChargeRatio: number;
  nextCarrierTag: string;
}

export interface TableLauncherHandoffSeam3DDefinition
  extends TableLauncherCarrierBaseDefinition {
  kind: "handoff_seam";
  compileRole: "terminal_seam";
  ownerWorld: "launcher";
  anchor: TablePoint3D;
  targetWorld: "board";
  handoffVelocity: TablePoint;
  handoffZ: number;
  ownedDonorSpanIds: readonly string[];
}

export type TableLauncherCarrier3DDefinition =
  | TableLauncherPhysicalCarrier3DDefinition
  | TableLauncherObservationSpine3DDefinition
  | TableLauncherHandoffSeam3DDefinition;

export interface TableLauncherPlunger3DDefinition {
  tag: string;
  donorSourceId: string;
  center: TablePoint3D;
  width: number;
  depth: number;
  height: number;
  stroke: number;
  speedPull: number;
  speedFire: number;
  parkPosition: number;
  momentumTransfer: number;
}

export interface TableLauncher3DDefinition {
  plunger: TableLauncherPlunger3DDefinition;
  carriers: readonly TableLauncherCarrier3DDefinition[];
  sensors: readonly TableLauncherSensor3DDefinition[];
  ballRestZ: number;
}

export interface TableLauncherDefinition {
  tag: string;
  laneRegions: readonly TableRegionShapeDefinition[];
  feedSettledSpeedMax: number;
  chargeMsMin: number;
  chargeMsMax: number;
  relaunchCooldownMs: number;
  launchImpulseMin: number;
  launchImpulseMax: number;
  launchAssistX: number;
  threeD: TableLauncher3DDefinition;
}

export interface TableDrainDefinition {
  tag: string;
  x: number;
  y: number;
  width: number;
  height: number;
}
