/**
 * Capture-award state tests for Flunk-Out Frenzy.
 *
 * These checks keep capture/eject/save score semantics in a focused helper so
 * `RuleEngine.ts` remains a thin coordinator over pure rule modules.
 */

import { describe, expect, it } from "vitest";

import {
  createInitialCaptureAwardsState,
  handleCaptureAwardsMachineEvent,
  resetCaptureAwardsForNextBall,
} from "./captureAwardsState";

describe("captureAwardsState", () => {
  it("awards capture once while a device stays armed, then awards ejection when released", () => {
    const initial = createInitialCaptureAwardsState();

    const firstCapture = handleCaptureAwardsMachineEvent(initial, {
      type: "ball-captured",
      tag: "capture/scoop-study",
      deviceKind: "hole",
    });
    const duplicateCapture = handleCaptureAwardsMachineEvent(firstCapture.nextState, {
      type: "ball-captured",
      tag: "capture/scoop-study",
      deviceKind: "hole",
    });
    const eject = handleCaptureAwardsMachineEvent(firstCapture.nextState, {
      type: "ball-ejected",
      tag: "capture/scoop-study",
      deviceKind: "hole",
    });

    expect(firstCapture.awardedScore).toBe(1_000);
    expect(firstCapture.ruleEvents).toEqual([
      {
        type: "capture-awarded",
        tag: "capture/scoop-study",
        deviceKind: "hole",
        points: 1_000,
      },
    ]);
    expect(duplicateCapture.awardedScore).toBe(0);
    expect(duplicateCapture.ruleEvents).toEqual([]);
    expect(eject.awardedScore).toBe(750);
    expect(eject.ruleEvents).toEqual([
      {
        type: "eject-awarded",
        tag: "capture/scoop-study",
        deviceKind: "hole",
        points: 750,
      },
    ]);
    expect(eject.nextState.armedCaptureTags).toEqual([]);
  });

  it("awards save points immediately and ignores ejection for non-armed captures", () => {
    const initial = createInitialCaptureAwardsState();

    const save = handleCaptureAwardsMachineEvent(initial, {
      type: "ball-saved",
      tag: "save/right-kickback",
      deviceKind: "kickback",
    });
    const strayEject = handleCaptureAwardsMachineEvent(initial, {
      type: "ball-ejected",
      tag: "capture/scoop-study",
      deviceKind: "hole",
    });

    expect(save.awardedScore).toBe(1_250);
    expect(save.ruleEvents).toEqual([
      {
        type: "save-awarded",
        tag: "save/right-kickback",
        deviceKind: "kickback",
        points: 1_250,
      },
    ]);
    expect(save.nextState.armedCaptureTags).toEqual([]);
    expect(strayEject.awardedScore).toBe(0);
    expect(strayEject.ruleEvents).toEqual([]);
  });

  it("clears armed captures on next-ball reset", () => {
    const armedState = handleCaptureAwardsMachineEvent(createInitialCaptureAwardsState(), {
      type: "ball-captured",
      tag: "capture/scoop-study",
      deviceKind: "hole",
    }).nextState;

    expect(resetCaptureAwardsForNextBall(armedState)).toEqual({
      armedCaptureTags: [],
    });
  });
});
