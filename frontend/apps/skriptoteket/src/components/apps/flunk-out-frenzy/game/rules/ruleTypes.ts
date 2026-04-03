/**
 * Shared rule-state contracts for Flunk-Out Frenzy.
 *
 * These types keep the pure rule layer explicit as `PR-0190` splits scoring,
 * bonus or jackpot, and ball-lifecycle handling into focused modules while
 * preserving a small engine-facing orchestration surface.
 */

import type {
  CaptureMachineEventKind,
  SaveMachineEventKind,
} from "../physics/physicsTypes";

export interface BonusRuleSnapshot {
  points: number;
  collectReady: boolean;
}

export interface JackpotRuleSnapshot {
  points: number;
  lit: boolean;
}

export interface BallLifecycleRuleSnapshot {
  ballsRemaining: number;
  roundFinished: boolean;
  shootAgainLit: boolean;
}

export interface RuleSnapshot {
  score: number;
  multiplier: number;
  litLaneTags: string[];
  bonus: BonusRuleSnapshot;
  jackpot: JackpotRuleSnapshot;
  ballLifecycle: BallLifecycleRuleSnapshot;
}

export type RuleEvent =
  | { type: "late-bank-complete"; multiplier: number }
  | { type: "bonus-awarded"; points: number }
  | { type: "jackpot-lit"; points: number }
  | { type: "jackpot-awarded"; points: number }
  | { type: "capture-awarded"; tag: string; deviceKind: CaptureMachineEventKind; points: number }
  | { type: "eject-awarded"; tag: string; deviceKind: CaptureMachineEventKind; points: number }
  | { type: "save-awarded"; tag: string; deviceKind: SaveMachineEventKind; points: number }
  | { type: "shoot-again-lit" };

export interface RuleStepResult {
  snapshot: RuleSnapshot;
  shouldRespawnBall: boolean;
  ruleEvents: RuleEvent[];
}
