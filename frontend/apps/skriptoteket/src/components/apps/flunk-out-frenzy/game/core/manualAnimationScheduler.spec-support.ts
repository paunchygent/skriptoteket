/**
 * Manual animation scheduler test helper for Flunk-Out Frenzy runtime specs.
 *
 * This helper provides deterministic frame scheduling for core runtime tests so
 * `GameRuntime` and `FixedStepRunner` can be exercised without browser timers
 * or real animation frames.
 */

import type { AnimationScheduler } from "./runtimeTypes";

interface ManualFrame {
  handle: number;
  callback: FrameRequestCallback;
}

export class ManualAnimationScheduler implements AnimationScheduler {
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
