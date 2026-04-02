/**
 * Bonus, jackpot, and award-arm state helpers for Flunk-Out Frenzy.
 *
 * The local prototype keeps these mechanics intentionally small: semantic
 * table events build bonus, light and collect jackpot, and complete the first
 * standup-target bank that can earn a `shootAgain` entitlement.
 */

import type { MachineEvent } from "../physics/physicsTypes";
import { PROTOTYPE_ALPHA_TABLE } from "../table/prototypeAlphaTable";
import type {
  BonusRuleSnapshot,
  JackpotRuleSnapshot,
  RuleEvent,
} from "./ruleTypes";

const JACKPOT_BASE_POINTS = 10_000;

const BONUS_POINTS = {
  rollover: 250,
  standupTarget: 1_000,
  popupTarget: 1_500,
  tripwire: 750,
  gate: 500,
} as const;

const JACKPOT_POINTS = {
  standupTarget: 2_500,
  popupTarget: 5_000,
} as const;

const JOCK_BANK_TARGET_TAGS = PROTOTYPE_ALPHA_TABLE.standupTargets
  .filter((target) => target.bankTag === "bank/jocks")
  .map((target) => target.tag);

export interface BonusJackpotState {
  bonusPoints: number;
  jackpotPoints: number;
  jackpotLit: boolean;
  completedStandupTargetTags: string[];
}

export interface BonusJackpotEventResult {
  nextState: BonusJackpotState;
  awardedScore: number;
  ruleEvents: RuleEvent[];
  completedShootAgainBank: boolean;
}

export interface DrainSettlementResult {
  nextState: BonusJackpotState;
  awardedScore: number;
  ruleEvents: RuleEvent[];
}

export function createInitialBonusJackpotState(): BonusJackpotState {
  return {
    bonusPoints: 0,
    jackpotPoints: JACKPOT_BASE_POINTS,
    jackpotLit: false,
    completedStandupTargetTags: [],
  };
}

export function currentBonusSnapshot(state: BonusJackpotState): BonusRuleSnapshot {
  return {
    points: state.bonusPoints,
    collectReady: state.bonusPoints > 0,
  };
}

export function currentJackpotSnapshot(state: BonusJackpotState): JackpotRuleSnapshot {
  return {
    points: state.jackpotPoints,
    lit: state.jackpotLit,
  };
}

export function handleBonusJackpotMachineEvent(
  state: BonusJackpotState,
  event: MachineEvent,
): BonusJackpotEventResult {
  switch (event.type) {
    case "rollover-enter":
      return {
        nextState: {
          ...state,
          bonusPoints: state.bonusPoints + BONUS_POINTS.rollover,
        },
        awardedScore: 0,
        ruleEvents: [],
        completedShootAgainBank: false,
      };
    case "standup-target-hit":
      return handleStandupTargetHit(state, event.tag);
    case "popup-target-hit":
      return handlePopupTargetHit(state);
    case "tripwire-crossed":
      return handleTripwireCrossed(state);
    case "gate-passed":
      return {
        nextState: {
          ...state,
          bonusPoints: state.bonusPoints + BONUS_POINTS.gate,
        },
        awardedScore: 0,
        ruleEvents: [],
        completedShootAgainBank: false,
      };
    case "bumper-fired":
    case "sling-fired":
    case "drain-enter":
    case "launch-lane-enter":
    case "launcher-fed":
    case "launcher-charged":
    case "launcher-released":
    case "ball-captured":
    case "ball-ejected":
    case "ball-saved":
      return {
        nextState: state,
        awardedScore: 0,
        ruleEvents: [],
        completedShootAgainBank: false,
      };
  }
}

export function settleBonusJackpotOnDrain(
  state: BonusJackpotState,
): DrainSettlementResult {
  const ruleEvents: RuleEvent[] = [];
  const awardedScore = state.bonusPoints;

  if (awardedScore > 0) {
    ruleEvents.push({ type: "bonus-awarded", points: awardedScore });
  }

  return {
    nextState: createInitialBonusJackpotState(),
    awardedScore,
    ruleEvents,
  };
}

function handleStandupTargetHit(
  state: BonusJackpotState,
  tag: string,
): BonusJackpotEventResult {
  const completedStandupTargetTags = state.completedStandupTargetTags.includes(tag)
    ? state.completedStandupTargetTags
    : [...state.completedStandupTargetTags, tag];
  const completedShootAgainBank = JOCK_BANK_TARGET_TAGS.length > 0
    && JOCK_BANK_TARGET_TAGS.every((targetTag) => completedStandupTargetTags.includes(targetTag));

  return {
    nextState: {
      bonusPoints: state.bonusPoints + BONUS_POINTS.standupTarget,
      jackpotPoints: state.jackpotPoints + JACKPOT_POINTS.standupTarget,
      jackpotLit: state.jackpotLit,
      completedStandupTargetTags: completedShootAgainBank ? [] : completedStandupTargetTags,
    },
    awardedScore: 0,
    ruleEvents: [],
    completedShootAgainBank,
  };
}

function handlePopupTargetHit(state: BonusJackpotState): BonusJackpotEventResult {
  const nextState: BonusJackpotState = {
    ...state,
    bonusPoints: state.bonusPoints + BONUS_POINTS.popupTarget,
    jackpotPoints: state.jackpotPoints + JACKPOT_POINTS.popupTarget,
    jackpotLit: true,
  };
  const ruleEvents: RuleEvent[] = [];

  if (!state.jackpotLit) {
    ruleEvents.push({ type: "jackpot-lit", points: nextState.jackpotPoints });
  }

  return {
    nextState,
    awardedScore: 0,
    ruleEvents,
    completedShootAgainBank: false,
  };
}

function handleTripwireCrossed(state: BonusJackpotState): BonusJackpotEventResult {
  const nextState: BonusJackpotState = {
    ...state,
    bonusPoints: state.bonusPoints + BONUS_POINTS.tripwire,
  };

  if (!state.jackpotLit) {
    return {
      nextState,
      awardedScore: 0,
      ruleEvents: [],
      completedShootAgainBank: false,
    };
  }

  return {
    nextState: {
      ...nextState,
      jackpotPoints: JACKPOT_BASE_POINTS,
      jackpotLit: false,
    },
    awardedScore: state.jackpotPoints,
    ruleEvents: [{ type: "jackpot-awarded", points: state.jackpotPoints }],
    completedShootAgainBank: false,
  };
}
