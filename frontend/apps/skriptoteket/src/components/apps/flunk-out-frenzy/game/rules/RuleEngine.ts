/**
 * Prototype-alpha scoring and progression rules for Flunk-Out Frenzy.
 *
 * The rule engine translates semantic machine events into score, multiplier,
 * and ball-lifecycle outcomes. It stays independent from Rapier so the
 * simulation can remain a pure machine-facts layer.
 */

import type { MachineEvent } from "../physics/physicsTypes";
import { PROTOTYPE_ALPHA_LATE_TAGS, PROTOTYPE_ALPHA_TABLE } from "../table/prototypeAlphaTable";

export interface RuleSnapshot {
  score: number;
  ballsRemaining: number;
  multiplier: number;
  litLaneTags: string[];
  roundFinished: boolean;
}

export interface RuleStepResult {
  snapshot: RuleSnapshot;
  shouldRespawnBall: boolean;
}

const SCORE_VALUES = {
  bumper: 250,
  sling: 10,
  rollover: 50,
  lateBonus: 2000,
} as const;

export class RuleEngine {
  private score: number = 0;
  private ballsRemaining: number = PROTOTYPE_ALPHA_TABLE.ballsPerGame;
  private multiplier: number = 1;
  private roundFinished = false;
  private readonly litLaneTags = new Set<string>();

  startGame(): RuleSnapshot {
    this.score = 0;
    this.ballsRemaining = PROTOTYPE_ALPHA_TABLE.ballsPerGame;
    this.multiplier = 1;
    this.roundFinished = false;
    this.litLaneTags.clear();
    return this.currentSnapshot();
  }

  currentSnapshot(): RuleSnapshot {
    return {
      score: this.score,
      ballsRemaining: this.ballsRemaining,
      multiplier: this.multiplier,
      litLaneTags: [...this.litLaneTags],
      roundFinished: this.roundFinished,
    };
  }

  handleMachineEvents(events: MachineEvent[]): RuleStepResult {
    if (this.roundFinished) {
      return {
        snapshot: this.currentSnapshot(),
        shouldRespawnBall: false,
      };
    }

    let shouldRespawnBall = false;

    for (const event of events) {
      switch (event.type) {
        case "bumper-fired":
          this.award(SCORE_VALUES.bumper);
          break;
        case "sling-fired":
          this.award(SCORE_VALUES.sling);
          break;
        case "rollover-enter":
          this.handleRollover(event.tag);
          break;
        case "drain-enter":
          if (this.ballsRemaining > 0) {
            this.ballsRemaining -= 1;
          }
          this.multiplier = 1;
          this.litLaneTags.clear();
          shouldRespawnBall = this.ballsRemaining > 0;
          this.roundFinished = this.ballsRemaining === 0;
          break;
      }
    }

    return {
      snapshot: this.currentSnapshot(),
      shouldRespawnBall,
    };
  }

  private handleRollover(tag: string): void {
    if (this.litLaneTags.has(tag)) {
      return;
    }

    this.litLaneTags.add(tag);
    this.award(SCORE_VALUES.rollover);

    const allLanesLit = PROTOTYPE_ALPHA_LATE_TAGS.every((laneTag) => this.litLaneTags.has(laneTag));
    if (!allLanesLit) {
      return;
    }

    this.multiplier = Math.min(this.multiplier + 1, 5);
    this.score += SCORE_VALUES.lateBonus;
    this.litLaneTags.clear();
  }

  private award(points: number): void {
    this.score += points * this.multiplier;
  }
}
