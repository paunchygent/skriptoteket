/**
 * Shared runtime-core test doubles and proof helpers for Flunk-Out Frenzy.
 *
 * The spec entrypoint imports smaller case modules that all depend on these
 * fakes so the runtime suite stays behaviorally rich without a giant test file.
 */

import { vi } from "vitest";

import type { RuntimeEngine, RuntimeEngineState } from "./runtimeEngineTypes";
import type {
  GameHudSnapshot,
  GameLauncherDebugSnapshot,
  GameViewSnapshot,
  RuntimeCommand,
} from "./runtimeTypes";
import type { RuntimeAudioDirector } from "../audio/audioTypes";
import type { MachineEvent } from "../physics/physicsTypes";
import type { RuntimeRenderer } from "../render/renderTypes";

export class FakeRuntimeEngine implements RuntimeEngine {
  public readonly appliedCommands: RuntimeCommand[] = [];
  public readonly dispose = vi.fn();
  private score = 0;
  private ballsRemaining = 3;
  private multiplier = 1;
  private bonusPoints = 0;
  private jackpotPoints = 10_000;
  private jackpotLit = false;
  private shootAgainLit = false;
  private roundFinished = false;
  private leftAngle = 18;
  private rightAngle = 162;
  private ballVisible = false;

  startGame(): RuntimeEngineState {
    this.score = 0;
    this.ballsRemaining = 3;
    this.multiplier = 1;
    this.bonusPoints = 0;
    this.jackpotPoints = 10_000;
    this.jackpotLit = false;
    this.shootAgainLit = false;
    this.roundFinished = false;
    this.ballVisible = true;
    return {
      ...this.currentState(),
      effects: [{ type: "round-started" }, { type: "ball-spawned" }],
    };
  }

  restartGame(): RuntimeEngineState {
    return this.startGame();
  }

  applyCommand(command: RuntimeCommand): void {
    this.appliedCommands.push(command);

    if (command.type === "left-flip") {
      this.leftAngle = command.pressed ? -24 : 18;
    } else if (command.type === "right-flip") {
      this.rightAngle = command.pressed ? 204 : 162;
    }
  }

  step(_dtMs: number): RuntimeEngineState {
    this.score += 250;
    this.multiplier = 2;
    this.bonusPoints = 500;
    this.jackpotPoints = 12_500;
    this.jackpotLit = true;

    if (this.score >= 500) {
      this.roundFinished = true;
      this.ballsRemaining = 0;
      this.ballVisible = false;
    }

    return this.currentState();
  }

  currentState(): RuntimeEngineState {
    return {
      score: this.score,
      ballsRemaining: this.ballsRemaining,
      multiplier: this.multiplier,
      bonus: { points: this.bonusPoints, collectReady: this.bonusPoints > 0 },
      jackpot: { points: this.jackpotPoints, lit: this.jackpotLit },
      ballLifecycle: { shootAgainLit: this.shootAgainLit },
      roundFinished: this.roundFinished,
      effects: [],
      view: createViewSnapshot(this.leftAngle, this.rightAngle, this.ballVisible),
    };
  }

  injectMachineEventsForDebug(events: MachineEvent[]): RuntimeEngineState {
    for (const event of events) {
      if (event.type === "rollover-enter") {
        this.score += 50;
        this.bonusPoints += 250;
      }
      if (event.type === "drain-enter") {
        this.ballsRemaining = Math.max(this.ballsRemaining - 1, 0);
        this.ballVisible = this.ballsRemaining > 0;
        this.roundFinished = this.ballsRemaining === 0;
      }
    }

    return this.currentState();
  }
}

export class FakeRenderer implements RuntimeRenderer {
  public readonly attach = vi.fn();
  public readonly dispose = vi.fn();
  public readonly render = vi.fn();
}

export class FakeAudioDirector implements RuntimeAudioDirector {
  public readonly enabled = true;
  public readonly setMuted = vi.fn();
  public readonly consumeEffects = vi.fn();
  public readonly dispose = vi.fn();
}

export class DisabledAudioDirector implements RuntimeAudioDirector {
  public readonly enabled = false;
  public readonly setMuted = vi.fn();
  public readonly consumeEffects = vi.fn();
  public readonly dispose = vi.fn();
}

export function createViewSnapshot(
  leftAngle = 18,
  rightAngle = 162,
  ballVisible = false,
): GameViewSnapshot {
  return {
    board: { width: 600, height: 1200 },
    ball: ballVisible ? { x: 528, y: 1044, radius: 12 } : null,
    plunger: null,
    flippers: {
      left: { side: "left", pivotX: 220, pivotY: 1045, length: 96, thickness: 20, angleDeg: leftAngle },
      right: { side: "right", pivotX: 380, pivotY: 1045, length: 96, thickness: 20, angleDeg: rightAngle },
    },
    rollovers: [
      { tag: "lane/top-l", label: "L", x: 180, y: 150, lit: false },
      { tag: "lane/top-a", label: "A", x: 260, y: 130, lit: false },
      { tag: "lane/top-t", label: "T", x: 340, y: 130, lit: false },
      { tag: "lane/top-e", label: "E", x: 420, y: 150, lit: false },
    ],
    launcherTelemetry: {
      plunger: { currentY: 1065.5, targetY: 1065.5, chargeRatio: null, phase: "fed" },
      ball: {
        owner: ballVisible ? "launcher_chain" : "none",
        position: ballVisible ? { x: 528, y: 1044, z: 12 } : null,
        velocity: ballVisible ? { x: 0, y: 0, z: 0 } : null,
      },
      route: {
        pendingReleaseChargeRatio: null,
        activeRouteTag: null,
        captureWindowMsRemaining: 0,
        routeProgressDistancePx: 0,
      },
      routeCapture: { lastDecision: "none", lastRejectReason: null },
      sensors: { feedInside: ballVisible, exitInside: false, lastSw16ExitStep: null },
      contact: {
        plungerBallContactActive: false,
        contactEnteredThisStep: false,
        contactExitedThisStep: false,
        separationPx: 0.8,
        overlapPx: 0,
        relativeVyAtContact: null,
        lastContactAtStep: null,
        impulseTransferMarker: 0,
      },
      seamTransition: null,
    },
    launchTraceStep: {
      stepIndex: 0,
      dtMs: 0,
      phase: "feed_rest",
      ballOwner: ballVisible ? "launcher_chain" : "none",
      ballPosition: ballVisible ? { x: 528, y: 1044, z: 12 } : null,
      ballVelocity: ballVisible ? { x: 0, y: 0, z: 0 } : null,
      plunger: { currentY: 1065.5, targetY: 1065.5, chargeRatio: null, phase: "fed" },
      route: {
        pendingReleaseChargeRatio: null,
        activeRouteTag: null,
        captureWindowMsRemaining: 0,
        routeProgressDistancePx: 0,
      },
      routeCapture: { lastDecision: "none", lastRejectReason: null },
      sensors: { feedInside: ballVisible, exitInside: false, lastSw16ExitStep: null },
      contact: {
        plungerBallContactActive: false,
        contactEnteredThisStep: false,
        contactExitedThisStep: false,
        separationPx: 0.8,
        overlapPx: 0,
        relativeVyAtContact: null,
        lastContactAtStep: null,
        impulseTransferMarker: 0,
      },
      seamTransition: null,
      events: [],
      handoffToBoardStep: null,
      firstBoardCollisionStep: null,
      boardCollisionStartedThisStep: false,
    },
  };
}

export function lastHud(hudEvents: GameHudSnapshot[]): GameHudSnapshot {
  const hud = hudEvents.at(-1);
  if (!hud) {
    throw new Error("Expected at least one HUD event.");
  }
  return hud;
}

type LaunchProofStrikeClassification =
  | "no_effective_strike"
  | "post_strike_route_rejection"
  | "strike_and_route_accepted";

function classifyStrike(
  telemetry: NonNullable<GameLauncherDebugSnapshot["launcher"]>,
): LaunchProofStrikeClassification {
  const strikeEvidencePresent =
    telemetry.contact.overlapPx >= 0.5 ||
    (telemetry.contact.relativeVyAtContact ?? Number.POSITIVE_INFINITY) <= -5 ||
    telemetry.contact.impulseTransferMarker >= 0.1;
  if (!strikeEvidencePresent) {
    return "no_effective_strike";
  }
  if (telemetry.routeCapture.lastDecision === "accepted") {
    return "strike_and_route_accepted";
  }
  return "post_strike_route_rejection";
}

export function createLaunchProofCaseRecord(args: {
  caseId: string;
  inputMode: "keyboard" | "pointer";
  holdProfile: "rest" | "short" | "medium" | "full" | "relaunch";
  dtMs: number;
  holdMs: number;
  holdSteps: number;
  relaunchGapMs: number;
  relaunchGapSteps: number;
  observationSteps: number;
  plungerDelta: number;
  ballDisplacementMagnitude: number;
  maxVy: number;
  minVy: number;
  sw16ExitObserved: boolean;
  telemetry: GameLauncherDebugSnapshot;
}) {
  if (!args.telemetry.launcher) {
    throw new Error("Launcher telemetry is required to build proof records.");
  }
  const launcher = args.telemetry.launcher;
  return {
    case_id: args.caseId,
    input_mode: args.inputMode,
    hold_profile: args.holdProfile,
    dt_ms: args.dtMs,
    hold_ms: args.holdMs,
    hold_steps: args.holdSteps,
    relaunch_gap_ms: args.relaunchGapMs,
    relaunch_gap_steps: args.relaunchGapSteps,
    observation_steps: args.observationSteps,
    plunger_delta: args.plungerDelta,
    ball_displacement_magnitude: args.ballDisplacementMagnitude,
    max_vy: args.maxVy,
    min_vy: args.minVy,
    route_capture_decision: launcher.routeCapture.lastDecision,
    route_capture_reason: launcher.routeCapture.lastRejectReason,
    sw16_exit_observed: args.sw16ExitObserved,
    contact_diagnostics: {
      contactActive: launcher.contact.plungerBallContactActive,
      maxOverlapPx: launcher.contact.overlapPx,
      lastContactAtStep: launcher.contact.lastContactAtStep,
      impulseTransferMarker: launcher.contact.impulseTransferMarker,
    },
    strike_classification: classifyStrike(launcher),
  };
}

export const PR_0206_PROOF_MATRIX_CONTRACT = [
  { caseId: "K-REST-STEADY", holdProfile: "rest", holdSteps: 0, thresholdPx: 0, thresholdVy: 0 },
  { caseId: "K-SHORT-STEADY", holdProfile: "short", holdSteps: 8, thresholdPx: 2, thresholdVy: -8 },
  { caseId: "K-MEDIUM-STEADY", holdProfile: "medium", holdSteps: 26, thresholdPx: 4, thresholdVy: -20 },
  { caseId: "K-FULL-STEADY", holdProfile: "full", holdSteps: 56, thresholdPx: 8, thresholdVy: -40 },
  { caseId: "K-RELAUNCH-MEDIUM", holdProfile: "relaunch", holdSteps: 26, thresholdPx: 4, thresholdVy: -20 },
] as const;

export const PR_0206_ALLOWED_ROUTE_REJECT_REASONS = [
  "distance_xy",
  "distance_z",
  "vy_gate",
  "window_expired",
  "no_route",
] as const;
