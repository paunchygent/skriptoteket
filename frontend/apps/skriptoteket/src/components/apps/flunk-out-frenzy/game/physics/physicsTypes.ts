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
  | { type: "launcher-fed"; tag: string }
  | { type: "launcher-charged"; tag: string }
  | { type: "launcher-released"; tag: string }
  | { type: "ball-captured"; tag: string; deviceKind: CaptureMachineEventKind }
  | { type: "ball-ejected"; tag: string; deviceKind: CaptureMachineEventKind }
  | { type: "ball-saved"; tag: string; deviceKind: SaveMachineEventKind };

export interface PhysicsBallSnapshot {
  x: number;
  y: number;
  radius: number;
}

export interface PhysicsPlungerSnapshot {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface PhysicsFlipperSnapshot {
  side: "left" | "right";
  pivotX: number;
  pivotY: number;
  length: number;
  thickness: number;
  angleDeg: number;
}

export type LauncherBallOwner = "launcher_chain" | "main_world" | "none";

export type LauncherRouteCaptureDecision = "accepted" | "rejected" | "none";

export type LauncherRouteCaptureRejectReason =
  | "distance_xy"
  | "distance_z"
  | "vy_gate"
  | "window_expired"
  | "no_route"
  | null;

export interface PhysicsLauncherPoint3DSnapshot {
  x: number;
  y: number;
  z: number;
}

export interface PhysicsLauncherVector3Snapshot {
  x: number;
  y: number;
  z: number;
}

export interface PhysicsLauncherTelemetrySnapshot {
  plunger: {
    currentY: number;
    targetY: number;
    chargeRatio: number | null;
    phase: "idle" | "feeding" | "fed" | "charging" | "released" | "relaunch";
  };
  ball: {
    owner: LauncherBallOwner;
    position: PhysicsLauncherPoint3DSnapshot | null;
    velocity: PhysicsLauncherVector3Snapshot | null;
  };
  route: {
    pendingReleaseChargeRatio: number | null;
    activeRouteTag: string | null;
    captureWindowMsRemaining: number;
    routeProgressDistancePx: number;
  };
  routeCapture: {
    lastDecision: LauncherRouteCaptureDecision;
    lastRejectReason: LauncherRouteCaptureRejectReason;
  };
  sensors: {
    feedInside: boolean;
    exitInside: boolean;
    lastSw16ExitStep: number | null;
  };
  contact: {
    plungerBallContactActive: boolean;
    contactEnteredThisStep: boolean;
    contactExitedThisStep: boolean;
    separationPx: number | null;
    overlapPx: number;
    relativeVyAtContact: number | null;
    lastContactAtStep: number | null;
    impulseTransferMarker: number;
  };
  seamTransition: PhysicsLauncherSeamTransitionSnapshot | null;
}

export interface PhysicsLauncherSeamTransitionSnapshot {
  fromRouteTag: string;
  toRouteTag: string;
  xyDeltaPx: number;
  zDeltaPx: number;
}

export type PhysicsLaunchToDropPhase =
  | "feed_rest"
  | "charge_pull"
  | "release_strike_window"
  | "route_overhead"
  | "route_endpoint_bridge"
  | "route_descent"
  | "handoff_to_board"
  | "board_drop_preimpact"
  | "board_drop_postimpact";

export interface PhysicsLaunchToDropTraceStep {
  stepIndex: number;
  dtMs: number;
  phase: PhysicsLaunchToDropPhase;
  ballOwner: LauncherBallOwner;
  ballPosition: PhysicsLauncherPoint3DSnapshot | null;
  ballVelocity: PhysicsLauncherVector3Snapshot | null;
  plunger: PhysicsLauncherTelemetrySnapshot["plunger"];
  route: PhysicsLauncherTelemetrySnapshot["route"];
  routeCapture: PhysicsLauncherTelemetrySnapshot["routeCapture"];
  sensors: PhysicsLauncherTelemetrySnapshot["sensors"];
  contact: PhysicsLauncherTelemetrySnapshot["contact"];
  seamTransition: PhysicsLauncherSeamTransitionSnapshot | null;
  events: MachineEvent[];
  handoffToBoardStep: number | null;
  firstBoardCollisionStep: number | null;
  boardCollisionStartedThisStep: boolean;
}

export interface PhysicsSnapshot {
  ball: PhysicsBallSnapshot | null;
  plunger: PhysicsPlungerSnapshot | null;
  flippers: {
    left: PhysicsFlipperSnapshot;
    right: PhysicsFlipperSnapshot;
  };
  launcherTelemetry: PhysicsLauncherTelemetrySnapshot | null;
  launchTraceStep: PhysicsLaunchToDropTraceStep | null;
}
