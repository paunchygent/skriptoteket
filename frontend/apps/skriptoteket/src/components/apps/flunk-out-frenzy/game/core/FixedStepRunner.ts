/**
 * Fixed-step animation runner for Flunk-Out Frenzy.
 *
 * This runner keeps the browser-owned runtime advancing in deterministic fixed
 * increments while still using `requestAnimationFrame` for scheduling. Later
 * physics slices will hang real simulation work off this seam.
 */

import type { AnimationScheduler } from "./runtimeTypes";

export class FixedStepRunner {
  private accumulatorMs = 0;
  private frameHandle: number | null = null;
  private lastFrameTimeMs: number | null = null;
  private running = false;

  constructor(
    private readonly stepMs: number,
    private readonly onStep: (dtMs: number) => void,
    private readonly scheduler: AnimationScheduler,
  ) {}

  start(): void {
    if (this.running) {
      return;
    }

    this.running = true;
    this.lastFrameTimeMs = null;
    this.accumulatorMs = 0;
    this.scheduleNextFrame();
  }

  stop(): void {
    if (!this.running) {
      return;
    }

    this.running = false;
    this.lastFrameTimeMs = null;
    this.accumulatorMs = 0;

    if (this.frameHandle !== null) {
      this.scheduler.cancelFrame(this.frameHandle);
      this.frameHandle = null;
    }
  }

  isRunning(): boolean {
    return this.running;
  }

  private readonly onFrame = (timestampMs: number): void => {
    if (!this.running) {
      return;
    }

    this.frameHandle = null;

    if (this.lastFrameTimeMs === null) {
      this.lastFrameTimeMs = timestampMs;
      this.scheduleNextFrame();
      return;
    }

    const clampedDeltaMs = Math.min(timestampMs - this.lastFrameTimeMs, this.stepMs * 5);
    this.lastFrameTimeMs = timestampMs;
    this.accumulatorMs += clampedDeltaMs;

    while (this.accumulatorMs >= this.stepMs) {
      this.onStep(this.stepMs);
      this.accumulatorMs -= this.stepMs;

      if (!this.running) {
        return;
      }
    }

    this.scheduleNextFrame();
  };

  private scheduleNextFrame(): void {
    if (!this.running || this.frameHandle !== null) {
      return;
    }

    this.frameHandle = this.scheduler.requestFrame(this.onFrame);
  }
}
