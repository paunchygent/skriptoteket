/**
 * Physics contracts for Flunk-Out Frenzy.
 *
 * Rapier stays entirely behind this boundary. The runtime and rules engine only
 * consume semantic machine events plus a render-friendly physics snapshot.
 */

export type CaptureMachineEventKind = "hole" | "kickout" | "sink";
export type SaveMachineEventKind = "kickback" | "save-post";

export type MachineEvent =
  | { type: "bumper-fired"; tag: string }
  | { type: "sling-fired"; tag: string; side: "left" | "right" }
  | { type: "rollover-enter"; tag: string }
  | { type: "drain-enter"; tag: string }
  | { type: "tripwire-crossed"; tag: string }
  | { type: "standup-target-hit"; tag: string }
  | { type: "popup-target-hit"; tag: string }
  | { type: "gate-passed"; tag: string }
  | { type: "launch-lane-enter"; tag: string }
  | { type: "ball-captured"; tag: string; deviceKind: CaptureMachineEventKind }
  | { type: "ball-ejected"; tag: string; deviceKind: CaptureMachineEventKind }
  | { type: "ball-saved"; tag: string; deviceKind: SaveMachineEventKind };

export interface PhysicsBallSnapshot {
  x: number;
  y: number;
  radius: number;
}

export interface PhysicsFlipperSnapshot {
  side: "left" | "right";
  pivotX: number;
  pivotY: number;
  length: number;
  thickness: number;
  angleDeg: number;
}

export interface PhysicsSnapshot {
  ball: PhysicsBallSnapshot | null;
  flippers: {
    left: PhysicsFlipperSnapshot;
    right: PhysicsFlipperSnapshot;
  };
}
