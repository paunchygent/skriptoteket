/**
 * Rule-engine tests for Flunk-Out Frenzy prototype alpha.
 *
 * These tests keep scoring, multiplier progression, and ball lifecycle logic
 * in the pure rules layer so future renderer or audio work does not become the
 * source of game truth.
 */

import { describe, expect, it } from "vitest";

import { RuleEngine } from "./RuleEngine";

describe("RuleEngine", () => {
  it("awards score and increases the multiplier when the full L-A-T-E bank is completed", () => {
    const rules = new RuleEngine();

    rules.startGame();

    const step = rules.handleMachineEvents([
      { type: "rollover-enter", tag: "lane/top-l" },
      { type: "rollover-enter", tag: "lane/top-a" },
      { type: "rollover-enter", tag: "lane/top-t" },
      { type: "rollover-enter", tag: "lane/top-e" },
    ]);

    expect(step.snapshot.score).toBe(2200);
    expect(step.snapshot.multiplier).toBe(2);
    expect(step.snapshot.litLaneTags).toEqual([]);
    expect(step.shouldRespawnBall).toBe(false);
  });

  it("applies the active multiplier to bumper and sling scoring", () => {
    const rules = new RuleEngine();

    rules.startGame();
    rules.handleMachineEvents([
      { type: "rollover-enter", tag: "lane/top-l" },
      { type: "rollover-enter", tag: "lane/top-a" },
      { type: "rollover-enter", tag: "lane/top-t" },
      { type: "rollover-enter", tag: "lane/top-e" },
    ]);

    const step = rules.handleMachineEvents([
      { type: "bumper-fired", tag: "bumper/pop-top" },
      { type: "sling-fired", tag: "sling/left", side: "left" },
    ]);

    expect(step.snapshot.score).toBe(2720);
    expect(step.snapshot.multiplier).toBe(2);
  });

  it("respawns drained balls until the third drain ends the run", () => {
    const rules = new RuleEngine();

    rules.startGame();

    const firstDrain = rules.handleMachineEvents([{ type: "drain-enter", tag: "drain/main" }]);
    const secondDrain = rules.handleMachineEvents([{ type: "drain-enter", tag: "drain/main" }]);
    const thirdDrain = rules.handleMachineEvents([{ type: "drain-enter", tag: "drain/main" }]);

    expect(firstDrain.snapshot.ballsRemaining).toBe(2);
    expect(firstDrain.shouldRespawnBall).toBe(true);

    expect(secondDrain.snapshot.ballsRemaining).toBe(1);
    expect(secondDrain.shouldRespawnBall).toBe(true);

    expect(thirdDrain.snapshot.ballsRemaining).toBe(0);
    expect(thirdDrain.snapshot.roundFinished).toBe(true);
    expect(thirdDrain.shouldRespawnBall).toBe(false);
  });
});
