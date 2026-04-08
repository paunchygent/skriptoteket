/**
 * Planner toolbar overflow threshold tests.
 *
 * These tests freeze the exact just-above / just-below breakpoint ladder so
 * retained review can reason about deterministic toolbar collapse instead of
 * broad viewport matrices.
 */

import { describe, expect, it } from "vitest";

import {
  derivePlannerToolbarOverflowThresholds,
  resolveOverflowHiddenContributionIds,
} from "./usePlannerToolbarOverflow";

describe("usePlannerToolbarOverflow", () => {
  const contributionOrder = ["undo-redo", "reset", "new-draft"];
  const contributionWidthsPx = {
    "undo-redo": 70,
    reset: 88,
    "new-draft": 94,
  };

  it("keeps all actions inline until the fully visible width budget is crossed", () => {
    const thresholds = derivePlannerToolbarOverflowThresholds({
      fullyVisibleRequiredWidthPx: 842,
      contributionOrder,
      contributionWidthsPx,
    });

    expect(thresholds).toEqual({
      "undo-redo": 842,
      reset: 772,
      "new-draft": 684,
    });
    expect(
      resolveOverflowHiddenContributionIds({
        availableWidthPx: 842,
        contributionOrder,
        thresholds,
      }),
    ).toEqual([]);
    expect(
      resolveOverflowHiddenContributionIds({
        availableWidthPx: 841,
        contributionOrder,
        thresholds,
      }),
    ).toEqual(["undo-redo"]);
  });

  it("reuses the same thresholds when the fully visible requirement stays stable", () => {
    const thresholds = derivePlannerToolbarOverflowThresholds({
      fullyVisibleRequiredWidthPx: 842,
      contributionOrder,
      contributionWidthsPx,
    });

    expect(thresholds).toEqual({
      "undo-redo": 842,
      reset: 772,
      "new-draft": 684,
    });
    expect(
      resolveOverflowHiddenContributionIds({
        availableWidthPx: 772,
        contributionOrder,
        thresholds,
      }),
    ).toEqual(["undo-redo"]);
    expect(
      resolveOverflowHiddenContributionIds({
        availableWidthPx: 771,
        contributionOrder,
        thresholds,
      }),
    ).toEqual(["undo-redo", "reset"]);
  });

  it("keeps the collapse ladder monotonic for deeper overflow states", () => {
    const thresholds = derivePlannerToolbarOverflowThresholds({
      fullyVisibleRequiredWidthPx: 842,
      contributionOrder,
      contributionWidthsPx,
    });

    expect(thresholds).toEqual({
      "undo-redo": 842,
      reset: 772,
      "new-draft": 684,
    });
    expect(
      resolveOverflowHiddenContributionIds({
        availableWidthPx: 900,
        contributionOrder,
        thresholds,
      }),
    ).toEqual([]);
    expect(
      resolveOverflowHiddenContributionIds({
        availableWidthPx: 800,
        contributionOrder,
        thresholds,
      }),
    ).toEqual(["undo-redo"]);
    expect(
      resolveOverflowHiddenContributionIds({
        availableWidthPx: 700,
        contributionOrder,
        thresholds,
      }),
    ).toEqual(["undo-redo", "reset"]);
    expect(
      resolveOverflowHiddenContributionIds({
        availableWidthPx: 683,
        contributionOrder,
        thresholds,
      }),
    ).toEqual(["undo-redo", "reset", "new-draft"]);
  });
});
