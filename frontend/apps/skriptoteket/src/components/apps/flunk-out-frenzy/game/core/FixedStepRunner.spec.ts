/**
 * Fixed-step runner tests for Flunk-Out Frenzy.
 *
 * These tests prove the runtime runner advances work in fixed increments and
 * stops cleanly when paused or disposed by the host layer.
 */

import { describe, expect, it } from "vitest";

import { FixedStepRunner } from "./FixedStepRunner";
import type { AnimationScheduler } from "./runtimeTypes";

interface ManualFrame {
  handle: number;
  callback: FrameRequestCallback;
}

class ManualAnimationScheduler implements AnimationScheduler {
  private frameHandle = 0;
  private nowMs = 0;
  private readonly frames = new Map<number, FrameRequestCallback>();

  now(): number {
    return this.nowMs;
  }

  requestFrame(callback: FrameRequestCallback): number {
    const handle = ++this.frameHandle;
    this.frames.set(handle, callback);
    return handle;
  }

  cancelFrame(handle: number): void {
    this.frames.delete(handle);
  }

  runFrame(deltaMs: number): void {
    const nextFrame = this.nextFrame();
    if (!nextFrame) {
      return;
    }

    this.nowMs += deltaMs;
    nextFrame.callback(this.nowMs);
  }

  hasPendingFrame(): boolean {
    return this.frames.size > 0;
  }

  private nextFrame(): ManualFrame | null {
    const [handle, callback] = this.frames.entries().next().value ?? [];
    if (!handle || !callback) {
      return null;
    }

    this.frames.delete(handle);
    return { handle, callback };
  }
}

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
