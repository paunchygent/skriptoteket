/**
 * Score and multiplier state helpers for Flunk-Out Frenzy.
 *
 * This module owns only direct score arithmetic plus the `L-A-T-E` rollover
 * bank progression so the top-level rule engine can stay focused on event
 * orchestration rather than bookkeeping.
 */

export interface ScoreState {
  score: number;
  multiplier: number;
  litLaneTags: string[];
}

export interface RolloverProgressResult {
  nextState: ScoreState;
  newlyLit: boolean;
  lateBankCompleted: boolean;
}

const MAX_MULTIPLIER = 5;
const LATE_BANK_BONUS = 2_000;

export function createInitialScoreState(): ScoreState {
  return {
    score: 0,
    multiplier: 1,
    litLaneTags: [],
  };
}

export function awardScaledPoints(state: ScoreState, points: number): ScoreState {
  return {
    ...state,
    score: state.score + points * state.multiplier,
  };
}

export function awardFlatPoints(state: ScoreState, points: number): ScoreState {
  return {
    ...state,
    score: state.score + points,
  };
}

export function handleLaneRollover(
  state: ScoreState,
  tag: string,
  laneTags: readonly string[],
  rolloverPoints: number,
): RolloverProgressResult {
  if (state.litLaneTags.includes(tag)) {
    return {
      nextState: state,
      newlyLit: false,
      lateBankCompleted: false,
    };
  }

  let nextState = awardScaledPoints(
    {
      ...state,
      litLaneTags: [...state.litLaneTags, tag],
    },
    rolloverPoints,
  );

  const lateBankCompleted = laneTags.every((laneTag) => nextState.litLaneTags.includes(laneTag));
  if (!lateBankCompleted) {
    return {
      nextState,
      newlyLit: true,
      lateBankCompleted: false,
    };
  }

  nextState = {
    score: nextState.score + LATE_BANK_BONUS,
    multiplier: Math.min(nextState.multiplier + 1, MAX_MULTIPLIER),
    litLaneTags: [],
  };

  return {
    nextState,
    newlyLit: true,
    lateBankCompleted: true,
  };
}

export function resetBallScopedScoreState(state: ScoreState): ScoreState {
  return {
    ...state,
    multiplier: 1,
    litLaneTags: [],
  };
}
