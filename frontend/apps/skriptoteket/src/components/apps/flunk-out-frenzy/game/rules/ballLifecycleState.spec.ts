/**
 * Ball-lifecycle state tests for Flunk-Out Frenzy.
 *
 * These checks isolate drain progression and `shootAgain` consumption so the
 * main rule engine can stay focused on coordinating modules instead of hiding
 * lifecycle edge cases inline.
 */

import { describe, expect, it } from "vitest";

import {
  createInitialBallLifecycleState,
  lightShootAgain,
  resolveDrain,
} from "./ballLifecycleState";

describe("ballLifecycleState", () => {
  it("counts down remaining balls until the round ends", () => {
    const firstDrain = resolveDrain(createInitialBallLifecycleState(3));
    const secondDrain = resolveDrain(firstDrain.nextState);
    const thirdDrain = resolveDrain(secondDrain.nextState);

    expect(firstDrain.nextState.ballsRemaining).toBe(2);
    expect(firstDrain.shouldRespawnBall).toBe(true);
    expect(secondDrain.nextState.ballsRemaining).toBe(1);
    expect(secondDrain.shouldRespawnBall).toBe(true);
    expect(thirdDrain.nextState.ballsRemaining).toBe(0);
    expect(thirdDrain.nextState.roundFinished).toBe(true);
    expect(thirdDrain.shouldRespawnBall).toBe(false);
  });

  it("consumes shoot-again on drain without decrementing the ball count", () => {
    const result = resolveDrain(lightShootAgain(createInitialBallLifecycleState(3)));

    expect(result.nextState.ballsRemaining).toBe(3);
    expect(result.nextState.shootAgainLit).toBe(false);
    expect(result.nextState.roundFinished).toBe(false);
    expect(result.shouldRespawnBall).toBe(true);
  });
});
