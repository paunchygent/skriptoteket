/**
 * Prototype-alpha scoring and progression rules for Flunk-Out Frenzy.
 *
 * The rule engine translates semantic machine events into score, bonus,
 * jackpot, and ball-lifecycle outcomes. `PR-0190` keeps this file as a thin
 * orchestrator over smaller pure rule helpers so the simulation can grow
 * without reintroducing a monolithic controller.
 */

import type { MachineEvent } from "../physics/physicsTypes";
import { PROTOTYPE_ALPHA_LATE_TAGS, PROTOTYPE_ALPHA_TABLE } from "../table/prototypeAlphaTable";
import {
  createInitialBallLifecycleState,
  lightShootAgain,
  resolveDrain,
} from "./ballLifecycleState";
import {
  createInitialCaptureAwardsState,
  handleCaptureAwardsMachineEvent,
  resetCaptureAwardsForNextBall,
  type CaptureAwardsMachineEvent,
} from "./captureAwardsState";
import {
  createInitialBonusJackpotState,
  currentBonusSnapshot,
  currentJackpotSnapshot,
  handleBonusJackpotMachineEvent,
  settleBonusJackpotOnDrain,
} from "./bonusJackpotState";
import {
  awardFlatPoints,
  awardScaledPoints,
  createInitialScoreState,
  handleLaneRollover,
  resetBallScopedScoreState,
} from "./scoreState";
import type {
  RuleEvent,
  RuleSnapshot,
  RuleStepResult,
} from "./ruleTypes";

const SCORE_VALUES = {
  bumper: 250,
  sling: 10,
  rollover: 50,
} as const;

export class RuleEngine {
  private scoreState = createInitialScoreState();
  private bonusJackpotState = createInitialBonusJackpotState();
  private captureAwardsState = createInitialCaptureAwardsState();
  private ballLifecycleState = createInitialBallLifecycleState(
    PROTOTYPE_ALPHA_TABLE.ballsPerGame,
  );

  startGame(): RuleSnapshot {
    this.scoreState = createInitialScoreState();
    this.bonusJackpotState = createInitialBonusJackpotState();
    this.captureAwardsState = createInitialCaptureAwardsState();
    this.ballLifecycleState = createInitialBallLifecycleState(
      PROTOTYPE_ALPHA_TABLE.ballsPerGame,
    );
    return this.currentSnapshot();
  }

  currentSnapshot(): RuleSnapshot {
    return {
      score: this.scoreState.score,
      multiplier: this.scoreState.multiplier,
      litLaneTags: [...this.scoreState.litLaneTags],
      bonus: currentBonusSnapshot(this.bonusJackpotState),
      jackpot: currentJackpotSnapshot(this.bonusJackpotState),
      ballLifecycle: this.ballLifecycleState,
    };
  }

  handleMachineEvents(events: MachineEvent[]): RuleStepResult {
    if (this.ballLifecycleState.roundFinished) {
      return {
        snapshot: this.currentSnapshot(),
        shouldRespawnBall: false,
        ruleEvents: [],
      };
    }

    let shouldRespawnBall = false;
    const ruleEvents: RuleEvent[] = [];

    for (const event of events) {
      switch (event.type) {
        case "bumper-fired":
          this.scoreState = awardScaledPoints(this.scoreState, SCORE_VALUES.bumper);
          break;
        case "sling-fired":
          this.scoreState = awardScaledPoints(this.scoreState, SCORE_VALUES.sling);
          break;
        case "rollover-enter":
          this.handleRollover(event.tag, ruleEvents);
          break;
        case "tripwire-crossed":
        case "standup-target-hit":
        case "popup-target-hit":
        case "gate-passed":
        case "launch-lane-enter":
        case "launcher-fed":
        case "launcher-charged":
        case "launcher-released":
          this.handleBonusJackpotEvent(event, ruleEvents);
          break;
        case "ball-captured":
        case "ball-ejected":
        case "ball-saved":
          this.handleCaptureAwardEvent(event, ruleEvents);
          break;
        case "drain-enter":
          shouldRespawnBall = this.handleDrain(ruleEvents);
          break;
      }
    }

    return {
      snapshot: this.currentSnapshot(),
      shouldRespawnBall,
      ruleEvents,
    };
  }

  private handleRollover(tag: string, ruleEvents: RuleEvent[]): void {
    const rolloverResult = handleLaneRollover(
      this.scoreState,
      tag,
      PROTOTYPE_ALPHA_LATE_TAGS,
      SCORE_VALUES.rollover,
    );
    this.scoreState = rolloverResult.nextState;

    if (rolloverResult.lateBankCompleted) {
      ruleEvents.push({
        type: "late-bank-complete",
        multiplier: this.scoreState.multiplier,
      });
    }

    if (rolloverResult.newlyLit) {
      this.handleBonusJackpotEvent({ type: "rollover-enter", tag }, ruleEvents);
    }
  }

  private handleBonusJackpotEvent(event: MachineEvent, ruleEvents: RuleEvent[]): void {
    const result = handleBonusJackpotMachineEvent(this.bonusJackpotState, event);
    this.bonusJackpotState = result.nextState;
    this.scoreState = awardFlatPoints(this.scoreState, result.awardedScore);
    ruleEvents.push(...result.ruleEvents);

    if (result.completedShootAgainBank && !this.ballLifecycleState.shootAgainLit) {
      this.ballLifecycleState = lightShootAgain(this.ballLifecycleState);
      ruleEvents.push({ type: "shoot-again-lit" });
    }
  }

  private handleCaptureAwardEvent(
    event: CaptureAwardsMachineEvent,
    ruleEvents: RuleEvent[],
  ): void {
    const result = handleCaptureAwardsMachineEvent(this.captureAwardsState, event);
    this.captureAwardsState = result.nextState;
    this.scoreState = awardFlatPoints(this.scoreState, result.awardedScore);
    ruleEvents.push(...result.ruleEvents);
  }

  private handleDrain(ruleEvents: RuleEvent[]): boolean {
    const drainSettlement = settleBonusJackpotOnDrain(this.bonusJackpotState);
    this.bonusJackpotState = drainSettlement.nextState;
    this.captureAwardsState = resetCaptureAwardsForNextBall(this.captureAwardsState);
    this.scoreState = awardFlatPoints(this.scoreState, drainSettlement.awardedScore);
    ruleEvents.push(...drainSettlement.ruleEvents);

    const drainResolution = resolveDrain(this.ballLifecycleState);
    this.ballLifecycleState = drainResolution.nextState;
    this.scoreState = resetBallScopedScoreState(this.scoreState);

    return drainResolution.shouldRespawnBall;
  }
}
