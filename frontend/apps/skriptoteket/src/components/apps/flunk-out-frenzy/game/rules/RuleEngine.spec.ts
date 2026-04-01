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
    expect(step.snapshot.bonus).toEqual({
      points: 1000,
      collectReady: true,
    });
    expect(step.shouldRespawnBall).toBe(false);
    expect(step.ruleEvents).toContainEqual({ type: "late-bank-complete", multiplier: 2 });
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

  it("does not award duplicate rollover bonus after a lane is already lit", () => {
    const rules = new RuleEngine();

    rules.startGame();

    const firstStep = rules.handleMachineEvents([
      { type: "rollover-enter", tag: "lane/top-l" },
    ]);

    const secondStep = rules.handleMachineEvents([
      { type: "rollover-enter", tag: "lane/top-l" },
    ]);

    expect(firstStep.snapshot.score).toBe(50);
    expect(firstStep.snapshot.bonus).toEqual({
      points: 250,
      collectReady: true,
    });

    expect(secondStep.snapshot.score).toBe(50);
    expect(secondStep.snapshot.multiplier).toBe(1);
    expect(secondStep.snapshot.litLaneTags).toEqual(["lane/top-l"]);
    expect(secondStep.snapshot.bonus).toEqual({
      points: 250,
      collectReady: true,
    });
    expect(secondStep.ruleEvents).toEqual([]);
  });

  it("lights shoot-again from the jocks bank and consumes it on drain", () => {
    const rules = new RuleEngine();

    rules.startGame();

    const bankStep = rules.handleMachineEvents([
      { type: "standup-target-hit", tag: "target/jock-left" },
      { type: "standup-target-hit", tag: "target/jock-center" },
      { type: "standup-target-hit", tag: "target/jock-right" },
    ]);

    expect(bankStep.snapshot.ballLifecycle.shootAgainLit).toBe(true);
    expect(bankStep.ruleEvents).toContainEqual({ type: "shoot-again-lit" });

    const drainStep = rules.handleMachineEvents([{ type: "drain-enter", tag: "drain/main" }]);

    expect(drainStep.snapshot.ballLifecycle.ballsRemaining).toBe(3);
    expect(drainStep.snapshot.ballLifecycle.shootAgainLit).toBe(false);
    expect(drainStep.shouldRespawnBall).toBe(true);
  });

  it("awards jackpot on tripwire after the popup target lights it", () => {
    const rules = new RuleEngine();

    rules.startGame();

    const popupStep = rules.handleMachineEvents([
      { type: "popup-target-hit", tag: "target/pop-study" },
    ]);

    expect(popupStep.snapshot.jackpot).toEqual({
      points: 15000,
      lit: true,
    });
    expect(popupStep.ruleEvents).toContainEqual({ type: "jackpot-lit", points: 15000 });

    const jackpotStep = rules.handleMachineEvents([
      { type: "tripwire-crossed", tag: "tripwire/right-orbit-return" },
    ]);

    expect(jackpotStep.snapshot.score).toBe(15000);
    expect(jackpotStep.snapshot.jackpot).toEqual({
      points: 10000,
      lit: false,
    });
    expect(jackpotStep.ruleEvents).toContainEqual({ type: "jackpot-awarded", points: 15000 });
  });

  it("respawns drained balls until the third drain ends the run", () => {
    const rules = new RuleEngine();

    rules.startGame();

    const firstDrain = rules.handleMachineEvents([{ type: "drain-enter", tag: "drain/main" }]);
    const secondDrain = rules.handleMachineEvents([{ type: "drain-enter", tag: "drain/main" }]);
    const thirdDrain = rules.handleMachineEvents([{ type: "drain-enter", tag: "drain/main" }]);

    expect(firstDrain.snapshot.ballLifecycle.ballsRemaining).toBe(2);
    expect(firstDrain.shouldRespawnBall).toBe(true);

    expect(secondDrain.snapshot.ballLifecycle.ballsRemaining).toBe(1);
    expect(secondDrain.shouldRespawnBall).toBe(true);

    expect(thirdDrain.snapshot.ballLifecycle.ballsRemaining).toBe(0);
    expect(thirdDrain.snapshot.ballLifecycle.roundFinished).toBe(true);
    expect(thirdDrain.shouldRespawnBall).toBe(false);
  });
});
