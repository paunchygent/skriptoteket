/**
 * Collider metadata contracts for Flunk-Out Frenzy physics.
 *
 * `PhysicsWorld` registers authored collider semantics here, while
 * `machineEventEmitter` consumes the metadata to translate Rapier contacts into
 * stable machine events for the rules and runtime layers.
 */

import type {
  TablePoint,
  TableTriggerPhaseDefinition,
  TableTriggerShapeDefinition,
} from "../table/tableDefinitionTypes";

export type CaptureDeviceKind = "hole" | "kickout" | "sink";
export type SaveDeviceKind = "kickback" | "save-post";
export type TriggerShapeKind = TableTriggerShapeDefinition["kind"];

interface TriggerSensorMeta {
  tag: string;
  triggerPhase: TableTriggerPhaseDefinition;
  triggerShapeKind: TriggerShapeKind;
}

export type ColliderMeta =
  | { kind: "ball"; tag: "ball/main" }
  | { kind: "bumper"; tag: string; center: TablePoint; impulse: number }
  | { kind: "sling"; tag: string; side: "left" | "right"; impulse: TablePoint }
  | { kind: "rollover"; tag: string }
  | { kind: "drain"; tag: string }
  | ({ kind: "tripwire" } & TriggerSensorMeta)
  | { kind: "standup-target"; tag: string }
  | { kind: "popup-target"; tag: string }
  | ({ kind: "gate" } & TriggerSensorMeta)
  | { kind: "launch-lane"; tag: string }
  | { kind: "capture"; tag: string; deviceKind: CaptureDeviceKind }
  | { kind: "save"; tag: string; deviceKind: SaveDeviceKind };

export type MachineColliderMeta = Exclude<ColliderMeta, { kind: "ball" }>;

export function resolveMachineColliderMeta(
  metaOne: ColliderMeta | undefined,
  metaTwo: ColliderMeta | undefined,
): MachineColliderMeta | null {
  if (metaOne?.kind === "ball" && metaTwo && metaTwo.kind !== "ball") {
    return metaTwo;
  }

  if (metaTwo?.kind === "ball" && metaOne && metaOne.kind !== "ball") {
    return metaOne;
  }

  return null;
}
