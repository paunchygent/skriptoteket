/**
 * Capture lifecycle tests for Flunk-Out Frenzy physics.
 *
 * These tests keep capture/save lifecycle transitions deterministic and bounded
 * before `PhysicsWorld` applies the resulting ball actions.
 */

import { describe, expect, it } from "vitest";

import {
  applyCaptureLifecycleStep,
  createCaptureDeviceTagIndex,
  createInitialCaptureLifecycleState,
  createSaveDeviceTagIndex,
} from "./captureDeviceLifecycle";

const CAPTURE_DEVICE = {
  tag: "capture/scoop-study",
  kind: "hole",
  x: 300,
  y: 480,
  width: 56,
  height: 56,
  holdMs: 64,
  cooldownMs: 300,
  ejectImpulse: { x: -120, y: -1120 },
} as const;

const SAVE_DEVICE = {
  tag: "save/right-kickback",
  kind: "kickback",
  x: 462,
  y: 1018,
  width: 62,
  height: 38,
  cooldownMs: 650,
  saveImpulse: { x: -420, y: -560 },
} as const;

describe("captureDeviceLifecycle", () => {
  it("converts capture->hold->eject into deterministic semantic events", () => {
    const state = createInitialCaptureLifecycleState();
    const captureDevicesByTag = createCaptureDeviceTagIndex([CAPTURE_DEVICE]);
    const saveDevicesByTag = createSaveDeviceTagIndex([SAVE_DEVICE]);

    const capturedStep = applyCaptureLifecycleStep({
      state,
      events: [{ type: "ball-captured", tag: CAPTURE_DEVICE.tag, deviceKind: CAPTURE_DEVICE.kind }],
      dtMs: 16,
      hasBall: true,
      captureDevicesByTag,
      saveDevicesByTag,
    });
    expect(capturedStep.forwardedEvents).toEqual([
      { type: "ball-captured", tag: CAPTURE_DEVICE.tag, deviceKind: CAPTURE_DEVICE.kind },
    ]);
    expect(capturedStep.holdPosition).toEqual({
      x: CAPTURE_DEVICE.x,
      y: CAPTURE_DEVICE.y,
    });
    expect(capturedStep.postStepEvents).toEqual([]);

    const ejectStep = applyCaptureLifecycleStep({
      state,
      events: [],
      dtMs: 64,
      hasBall: true,
      captureDevicesByTag,
      saveDevicesByTag,
    });
    expect(ejectStep.postStepEvents).toEqual([
      { type: "ball-ejected", tag: CAPTURE_DEVICE.tag, deviceKind: CAPTURE_DEVICE.kind },
    ]);
    expect(ejectStep.holdPosition).toBeNull();
    expect(ejectStep.impulses).toContainEqual(CAPTURE_DEVICE.ejectImpulse);
  });

  it("suppresses repeated save events while a save-device cooldown is active", () => {
    const state = createInitialCaptureLifecycleState();
    const captureDevicesByTag = createCaptureDeviceTagIndex([CAPTURE_DEVICE]);
    const saveDevicesByTag = createSaveDeviceTagIndex([SAVE_DEVICE]);

    const firstSaveStep = applyCaptureLifecycleStep({
      state,
      events: [{ type: "ball-saved", tag: SAVE_DEVICE.tag, deviceKind: SAVE_DEVICE.kind }],
      dtMs: 16,
      hasBall: true,
      captureDevicesByTag,
      saveDevicesByTag,
    });
    expect(firstSaveStep.forwardedEvents).toEqual([
      { type: "ball-saved", tag: SAVE_DEVICE.tag, deviceKind: SAVE_DEVICE.kind },
    ]);
    expect(firstSaveStep.impulses).toContainEqual(SAVE_DEVICE.saveImpulse);

    const suppressedStep = applyCaptureLifecycleStep({
      state,
      events: [{ type: "ball-saved", tag: SAVE_DEVICE.tag, deviceKind: SAVE_DEVICE.kind }],
      dtMs: 16,
      hasBall: true,
      captureDevicesByTag,
      saveDevicesByTag,
    });
    expect(suppressedStep.forwardedEvents).toEqual([]);
    expect(suppressedStep.impulses).toEqual([]);

    const cooldownExpiredStep = applyCaptureLifecycleStep({
      state,
      events: [{ type: "ball-saved", tag: SAVE_DEVICE.tag, deviceKind: SAVE_DEVICE.kind }],
      dtMs: SAVE_DEVICE.cooldownMs,
      hasBall: true,
      captureDevicesByTag,
      saveDevicesByTag,
    });
    expect(cooldownExpiredStep.forwardedEvents).toEqual([
      { type: "ball-saved", tag: SAVE_DEVICE.tag, deviceKind: SAVE_DEVICE.kind },
    ]);
  });
});
