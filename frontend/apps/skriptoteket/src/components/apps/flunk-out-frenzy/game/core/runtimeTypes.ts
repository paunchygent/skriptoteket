/**
 * Runtime core shared contracts for Flunk-Out Frenzy.
 *
 * These types define the command-driven seam between the runtime spine, input
 * adapters, and the Vue host component. They intentionally stay minimal in
 * `PR-0098` so later physics and rules slices can extend them without
 * rewriting the shell boundary.
 */

import type { MachineEvent } from "../physics/physicsTypes";
import type { LaunchToDropTraceArtifactPayload } from "../physics/launchTraceContract";

export type GameSessionStatus = "ready" | "running" | "paused" | "game-over";

export interface GameHudBonusSnapshot {
  points: number;
  collectReady: boolean;
}

export interface GameHudJackpotSnapshot {
  points: number;
  lit: boolean;
}

export interface GameHudBallLifecycleSnapshot {
  shootAgainLit: boolean;
}

export interface GameHudSnapshot {
  score: number;
  ballsRemaining: number;
  multiplier: number;
  bonus: GameHudBonusSnapshot;
  jackpot: GameHudJackpotSnapshot;
  ballLifecycle: GameHudBallLifecycleSnapshot;
  status: GameSessionStatus;
  muted: boolean;
}

export interface GameBoardSnapshot {
  width: number;
  height: number;
}

export interface GameBallSnapshot {
  x: number;
  y: number;
  radius: number;
}

export interface GamePlungerSnapshot {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface GameFlipperSnapshot {
  side: "left" | "right";
  pivotX: number;
  pivotY: number;
  length: number;
  thickness: number;
  angleDeg: number;
}

export interface GameRolloverSnapshot {
  tag: string;
  label: string;
  x: number;
  y: number;
  lit: boolean;
}

export type GameLauncherBallOwner = "launcher_chain" | "main_world" | "none";

export type GameLauncherRouteCaptureDecision = "accepted" | "rejected" | "none";

export type GameLauncherRouteCaptureRejectReason =
  | "distance_xy"
  | "distance_z"
  | "vy_gate"
  | "window_expired"
  | "no_route"
  | null;

export interface GameLauncherTelemetrySnapshot {
  plunger: {
    currentY: number;
    targetY: number;
    chargeRatio: number | null;
    phase: "idle" | "feeding" | "fed" | "charging" | "released" | "relaunch";
  };
  ball: {
    owner: GameLauncherBallOwner;
    position: { x: number; y: number; z: number } | null;
    velocity: { x: number; y: number; z: number } | null;
  };
  route: {
    pendingReleaseChargeRatio: number | null;
    activeRouteTag: string | null;
    captureWindowMsRemaining: number;
    routeProgressDistancePx: number;
  };
  routeCapture: {
    lastDecision: GameLauncherRouteCaptureDecision;
    lastRejectReason: GameLauncherRouteCaptureRejectReason;
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
  seamTransition: GameLauncherSeamTransitionSnapshot | null;
}

export interface GameLauncherSeamTransitionSnapshot {
  fromRouteTag: string;
  toRouteTag: string;
  xyDeltaPx: number;
  zDeltaPx: number;
}

export type GameLaunchToDropPhase =
  | "feed_rest"
  | "charge_pull"
  | "release_strike_window"
  | "route_overhead"
  | "route_endpoint_bridge"
  | "route_descent"
  | "handoff_to_board"
  | "board_drop_preimpact"
  | "board_drop_postimpact";

export interface GameLaunchToDropTraceStep {
  stepIndex: number;
  dtMs: number;
  phase: GameLaunchToDropPhase;
  ballOwner: GameLauncherBallOwner;
  ballPosition: { x: number; y: number; z: number } | null;
  ballVelocity: { x: number; y: number; z: number } | null;
  plunger: GameLauncherTelemetrySnapshot["plunger"];
  route: GameLauncherTelemetrySnapshot["route"];
  routeCapture: GameLauncherTelemetrySnapshot["routeCapture"];
  sensors: GameLauncherTelemetrySnapshot["sensors"];
  contact: GameLauncherTelemetrySnapshot["contact"];
  seamTransition: GameLauncherSeamTransitionSnapshot | null;
  events: MachineEvent[];
  handoffToBoardStep: number | null;
  firstBoardCollisionStep: number | null;
  boardCollisionStartedThisStep: boolean;
}

export interface GameLauncherDebugSnapshot {
  input: {
    launchPressed: boolean;
    lastTransitionMs: number | null;
  };
  launcher: GameLauncherTelemetrySnapshot | null;
  launchToDropTraceStep: GameLaunchToDropTraceStep | null;
}

export type GameLaunchTraceArtifactDebugPayload = LaunchToDropTraceArtifactPayload;

export interface GameViewSnapshot {
  board: GameBoardSnapshot;
  ball: GameBallSnapshot | null;
  plunger: GamePlungerSnapshot | null;
  flippers: {
    left: GameFlipperSnapshot;
    right: GameFlipperSnapshot;
  };
  rollovers: GameRolloverSnapshot[];
  launcherTelemetry?: GameLauncherTelemetrySnapshot | null;
  launchTraceStep?: GameLaunchToDropTraceStep | null;
}

export type RuntimeCommand =
  | { type: "left-flip"; pressed: boolean }
  | { type: "right-flip"; pressed: boolean }
  | { type: "launch"; pressed: boolean };

export interface RuntimeInputState {
  leftFlipPressed: boolean;
  rightFlipPressed: boolean;
  launchPressed: boolean;
  lastCommandLabel: string;
}

export interface AnimationScheduler {
  now(): number;
  requestFrame(callback: FrameRequestCallback): number;
  cancelFrame(handle: number): void;
}

export function createInitialHudSnapshot(): GameHudSnapshot {
  return {
    score: 0,
    ballsRemaining: 3,
    multiplier: 1,
    bonus: {
      points: 0,
      collectReady: false,
    },
    jackpot: {
      points: 10_000,
      lit: false,
    },
    ballLifecycle: {
      shootAgainLit: false,
    },
    status: "ready",
    muted: false,
  };
}

export function createInitialInputState(): RuntimeInputState {
  return {
    leftFlipPressed: false,
    rightFlipPressed: false,
    launchPressed: false,
    lastCommandLabel: "Awaiting input",
  };
}

export function createBrowserAnimationScheduler(): AnimationScheduler {
  return {
    now: () => performance.now(),
    requestFrame: (callback) => window.requestAnimationFrame(callback),
    cancelFrame: (handle) => window.cancelAnimationFrame(handle),
  };
}

export function describeRuntimeCommand(command: RuntimeCommand): string {
  if (command.type === "left-flip") {
    return command.pressed ? "Vänster flipper ned" : "Vänster flipper upp";
  }
  if (command.type === "right-flip") {
    return command.pressed ? "Höger flipper ned" : "Höger flipper upp";
  }
  return command.pressed ? "Launch laddas" : "Launch släpps";
}
