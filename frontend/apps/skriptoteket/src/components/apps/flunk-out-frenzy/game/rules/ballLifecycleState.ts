/**
 * Ball-lifecycle state helpers for Flunk-Out Frenzy.
 *
 * This module owns only ball-count progression and `shootAgain` entitlement
 * consumption so the rule engine can keep drain settlement separate from
 * score, bonus, and jackpot bookkeeping.
 */

import type { BallLifecycleRuleSnapshot } from "./ruleTypes";

export interface DrainResolution {
  nextState: BallLifecycleRuleSnapshot;
  shouldRespawnBall: boolean;
}

export function createInitialBallLifecycleState(
  ballsPerGame: number,
): BallLifecycleRuleSnapshot {
  return {
    ballsRemaining: ballsPerGame,
    roundFinished: false,
    shootAgainLit: false,
  };
}

export function lightShootAgain(
  state: BallLifecycleRuleSnapshot,
): BallLifecycleRuleSnapshot {
  return {
    ...state,
    shootAgainLit: true,
  };
}

export function resolveDrain(
  state: BallLifecycleRuleSnapshot,
): DrainResolution {
  if (state.shootAgainLit) {
    return {
      nextState: {
        ...state,
        shootAgainLit: false,
      },
      shouldRespawnBall: true,
    };
  }

  const ballsRemaining = Math.max(state.ballsRemaining - 1, 0);

  return {
    nextState: {
      ballsRemaining,
      roundFinished: ballsRemaining === 0,
      shootAgainLit: false,
    },
    shouldRespawnBall: ballsRemaining > 0,
  };
}
