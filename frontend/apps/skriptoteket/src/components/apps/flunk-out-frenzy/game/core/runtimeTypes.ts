/**
 * Runtime core shared contracts for Flunk-Out Frenzy.
 *
 * These types define the command-driven seam between the runtime spine, input
 * adapters, and the Vue host component. They intentionally stay minimal in
 * `PR-0098` so later physics and rules slices can extend them without
 * rewriting the shell boundary.
 */

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

export interface GameViewSnapshot {
  board: GameBoardSnapshot;
  ball: GameBallSnapshot | null;
  plunger: GamePlungerSnapshot | null;
  flippers: {
    left: GameFlipperSnapshot;
    right: GameFlipperSnapshot;
  };
  rollovers: GameRolloverSnapshot[];
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
