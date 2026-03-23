/**
 * Fixed-step runner tests for Flunk-Out Frenzy.
 *
 * These tests prove the runtime runner advances work in fixed increments and
 * stops cleanly when paused or disposed by the host layer.
 */

import { describe, expect, it } from "vitest";

import { FixedStepRunner } from "./FixedStepRunner";
import { ManualAnimationScheduler } from "./manualAnimationScheduler.spec-support";

describe("FixedStepRunner", () => {
  it("advances work in fixed increments after animation frames arrive", () => {
    const scheduler = new ManualAnimationScheduler();
    const steps: number[] = [];
    const runner = new FixedStepRunner(10, (dtMs) => steps.push(dtMs), scheduler);

    runner.start();
    scheduler.runFrame(0);
    scheduler.runFrame(35);

    expect(steps).toEqual([10, 10, 10]);
    expect(scheduler.hasPendingFrame()).toBe(true);
  });

  it("stops scheduling work after stop is called", () => {
    const scheduler = new ManualAnimationScheduler();
    const steps: number[] = [];
    const runner = new FixedStepRunner(10, (dtMs) => steps.push(dtMs), scheduler);

    runner.start();
    scheduler.runFrame(0);
    runner.stop();
    scheduler.runFrame(25);

    expect(steps).toEqual([]);
    expect(runner.isRunning()).toBe(false);
    expect(scheduler.hasPendingFrame()).toBe(false);
  });
});
