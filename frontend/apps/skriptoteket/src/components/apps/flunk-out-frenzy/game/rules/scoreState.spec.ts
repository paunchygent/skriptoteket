/**
 * Score-state tests for Flunk-Out Frenzy.
 *
 * These checks keep multiplier and lane-bank arithmetic isolated from the
 * broader rule orchestrator so future mechanics can reuse the same pure score
 * helpers without bloating `RuleEngine.ts`.
 */

import { describe, expect, it } from "vitest";

import {
  awardScaledPoints,
  createInitialScoreState,
  handleLaneRollover,
} from "./scoreState";

describe("scoreState", () => {
  it("awards scaled points using the active multiplier", () => {
    const state = {
      ...createInitialScoreState(),
      multiplier: 3,
    };

    expect(awardScaledPoints(state, 250).score).toBe(750);
  });

  it("completes the L-A-T-E bank once and increases the multiplier", () => {
    let state = createInitialScoreState();

    for (const tag of ["lane/top-l", "lane/top-a", "lane/top-t", "lane/top-e"]) {
      state = handleLaneRollover(
        state,
        tag,
        ["lane/top-l", "lane/top-a", "lane/top-t", "lane/top-e"],
        50,
      ).nextState;
    }

    expect(state.score).toBe(2_200);
    expect(state.multiplier).toBe(2);
    expect(state.litLaneTags).toEqual([]);
  });
});
