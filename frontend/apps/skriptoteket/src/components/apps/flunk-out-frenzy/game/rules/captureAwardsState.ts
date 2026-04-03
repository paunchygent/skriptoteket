/**
 * Capture/eject/save award helpers for Flunk-Out Frenzy.
 *
 * This module keeps capture-device scoring and armed-capture lifecycle state
 * outside `RuleEngine.ts`. The engine only orchestrates machine events while
 * this helper decides when capture transitions should award points.
 */

import type {
  CaptureMachineEventKind,
  MachineEvent,
  SaveMachineEventKind,
} from "../physics/physicsTypes";
import type { RuleEvent } from "./ruleTypes";

const CAPTURE_AWARD_POINTS: Readonly<Record<CaptureMachineEventKind, number>> = Object.freeze({
  hole: 1_000,
  kickout: 1_500,
  sink: 2_000,
});

const EJECT_AWARD_POINTS: Readonly<Record<CaptureMachineEventKind, number>> = Object.freeze({
  hole: 750,
  kickout: 1_000,
  sink: 1_250,
});

const SAVE_AWARD_POINTS: Readonly<Record<SaveMachineEventKind, number>> = Object.freeze({
  kickback: 1_250,
  "save-post": 900,
});

export type CaptureAwardsMachineEvent = Extract<
  MachineEvent,
  { type: "ball-captured" | "ball-ejected" | "ball-saved" }
>;

export interface CaptureAwardsState {
  armedCaptureTags: string[];
}

export interface CaptureAwardResult {
  nextState: CaptureAwardsState;
  awardedScore: number;
  ruleEvents: RuleEvent[];
}

export function createInitialCaptureAwardsState(): CaptureAwardsState {
  return {
    armedCaptureTags: [],
  };
}

export function resetCaptureAwardsForNextBall(
  state: CaptureAwardsState,
): CaptureAwardsState {
  if (state.armedCaptureTags.length === 0) {
    return state;
  }

  return {
    ...state,
    armedCaptureTags: [],
  };
}

export function handleCaptureAwardsMachineEvent(
  state: CaptureAwardsState,
  event: CaptureAwardsMachineEvent,
): CaptureAwardResult {
  switch (event.type) {
    case "ball-captured":
      return handleCaptured(state, event.tag, event.deviceKind);
    case "ball-ejected":
      return handleEjected(state, event.tag, event.deviceKind);
    case "ball-saved":
      return {
        nextState: state,
        awardedScore: SAVE_AWARD_POINTS[event.deviceKind],
        ruleEvents: [
          {
            type: "save-awarded",
            tag: event.tag,
            deviceKind: event.deviceKind,
            points: SAVE_AWARD_POINTS[event.deviceKind],
          },
        ],
      };
  }
}

function handleCaptured(
  state: CaptureAwardsState,
  tag: string,
  deviceKind: CaptureMachineEventKind,
): CaptureAwardResult {
  if (state.armedCaptureTags.includes(tag)) {
    return {
      nextState: state,
      awardedScore: 0,
      ruleEvents: [],
    };
  }

  return {
    nextState: {
      armedCaptureTags: [...state.armedCaptureTags, tag],
    },
    awardedScore: CAPTURE_AWARD_POINTS[deviceKind],
    ruleEvents: [
      {
        type: "capture-awarded",
        tag,
        deviceKind,
        points: CAPTURE_AWARD_POINTS[deviceKind],
      },
    ],
  };
}

function handleEjected(
  state: CaptureAwardsState,
  tag: string,
  deviceKind: CaptureMachineEventKind,
): CaptureAwardResult {
  if (!state.armedCaptureTags.includes(tag)) {
    return {
      nextState: state,
      awardedScore: 0,
      ruleEvents: [],
    };
  }

  return {
    nextState: {
      armedCaptureTags: state.armedCaptureTags.filter((armedTag) => armedTag !== tag),
    },
    awardedScore: EJECT_AWARD_POINTS[deviceKind],
    ruleEvents: [
      {
        type: "eject-awarded",
        tag,
        deviceKind,
        points: EJECT_AWARD_POINTS[deviceKind],
      },
    ],
  };
}
