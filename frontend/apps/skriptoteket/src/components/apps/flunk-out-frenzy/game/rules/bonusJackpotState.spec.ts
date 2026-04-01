/**
 * Bonus and jackpot rule-state tests for Flunk-Out Frenzy.
 *
 * These checks keep the prototype's first bonus, jackpot, and award-arm rules
 * explicit before they are threaded through the engine and HUD layers.
 */

import { describe, expect, it } from "vitest";

import {
  createInitialBonusJackpotState,
  currentBonusSnapshot,
  currentJackpotSnapshot,
  handleBonusJackpotMachineEvent,
  settleBonusJackpotOnDrain,
} from "./bonusJackpotState";

describe("bonusJackpotState", () => {
  it("lights jackpot from the popup target and increases its value", () => {
    const result = handleBonusJackpotMachineEvent(
      createInitialBonusJackpotState(),
      { type: "popup-target-hit", tag: "target/pop-study" },
    );

    expect(currentJackpotSnapshot(result.nextState)).toEqual({
      points: 15_000,
      lit: true,
    });
    expect(result.ruleEvents).toEqual([{ type: "jackpot-lit", points: 15_000 }]);
  });

  it("awards a lit jackpot on tripwire crossing and resets it afterward", () => {
    const litJackpot = handleBonusJackpotMachineEvent(
      createInitialBonusJackpotState(),
      { type: "popup-target-hit", tag: "target/pop-study" },
    ).nextState;

    const result = handleBonusJackpotMachineEvent(
      litJackpot,
      { type: "tripwire-crossed", tag: "tripwire/right-orbit-return" },
    );

    expect(result.awardedScore).toBe(15_000);
    expect(currentJackpotSnapshot(result.nextState)).toEqual({
      points: 10_000,
      lit: false,
    });
    expect(result.ruleEvents).toEqual([{ type: "jackpot-awarded", points: 15_000 }]);
  });

  it("marks the jocks standup-target bank as a shoot-again completion trigger", () => {
    let state = createInitialBonusJackpotState();

    for (const tag of ["target/jock-left", "target/jock-center", "target/jock-right"]) {
      state = handleBonusJackpotMachineEvent(
        state,
        { type: "standup-target-hit", tag },
      ).nextState;
    }

    const result = handleBonusJackpotMachineEvent(
      {
        ...state,
        completedStandupTargetTags: ["target/jock-left", "target/jock-center"],
      },
      { type: "standup-target-hit", tag: "target/jock-right" },
    );

    expect(result.completedShootAgainBank).toBe(true);
    expect(result.nextState.completedStandupTargetTags).toEqual([]);
  });

  it("settles earned bonus on drain and resets ball-scoped state", () => {
    const progressedState = handleBonusJackpotMachineEvent(
      handleBonusJackpotMachineEvent(
        createInitialBonusJackpotState(),
        { type: "rollover-enter", tag: "lane/top-l" },
      ).nextState,
      { type: "gate-passed", tag: "gate/launch-lane-exit" },
    ).nextState;

    const result = settleBonusJackpotOnDrain(progressedState);

    expect(result.awardedScore).toBe(750);
    expect(currentBonusSnapshot(result.nextState)).toEqual({
      points: 0,
      collectReady: false,
    });
    expect(currentJackpotSnapshot(result.nextState)).toEqual({
      points: 10_000,
      lit: false,
    });
    expect(result.ruleEvents).toEqual([{ type: "bonus-awarded", points: 750 }]);
  });
});
