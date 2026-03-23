/**
 * Physics contracts for Flunk-Out Frenzy.
 *
 * Rapier stays entirely behind this boundary. The runtime and rules engine only
 * consume semantic machine events plus a render-friendly physics snapshot.
 */

export type MachineEvent =
  | { type: "bumper-fired"; tag: string }
  | { type: "sling-fired"; tag: string; side: "left" | "right" }
  | { type: "rollover-enter"; tag: string }
  | { type: "drain-enter"; tag: string };

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
