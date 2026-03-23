/**
 * Runtime core tests for Flunk-Out Frenzy.
 *
 * These tests keep the runtime authoritative over lifecycle, HUD publishing,
 * input forwarding, and game-over transitions while the simulation itself can
 * stay behind a narrower engine interface.
 */

import { describe, expect, it, vi } from "vitest";

import type { RuntimeEngine, RuntimeEngineState } from "./runtimeEngineTypes";
import { GameRuntime } from "./GameRuntime";
import type {
  AnimationScheduler,
  GameHudSnapshot,
  GameViewSnapshot,
  RuntimeCommand,
} from "./runtimeTypes";
import type { MachineEvent } from "../physics/physicsTypes";

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

  private nextFrame(): ManualFrame | null {
    const [handle, callback] = this.frames.entries().next().value ?? [];
    if (!handle || !callback) {
      return null;
    }

    this.frames.delete(handle);
    return { handle, callback };
  }
}

class FakeRuntimeEngine implements RuntimeEngine {
  public readonly appliedCommands: RuntimeCommand[] = [];
  public readonly dispose = vi.fn();
  private score = 0;
  private ballsRemaining = 3;
  private multiplier = 1;
  private roundFinished = false;
  private leftAngle = 18;
  private rightAngle = 162;
  private ballVisible = false;

  startGame(): RuntimeEngineState {
    this.score = 0;
    this.ballsRemaining = 3;
    this.multiplier = 1;
    this.roundFinished = false;
    this.ballVisible = true;
    return this.currentState();
  }

  restartGame(): RuntimeEngineState {
    return this.startGame();
  }

  applyCommand(command: RuntimeCommand): void {
    this.appliedCommands.push(command);

    if (command.type === "left-flip") {
      this.leftAngle = command.pressed ? -24 : 18;
    } else if (command.type === "right-flip") {
      this.rightAngle = command.pressed ? 204 : 162;
    }
  }

  step(_dtMs: number): RuntimeEngineState {
    this.score += 250;
    this.multiplier = 2;

    if (this.score >= 500) {
      this.roundFinished = true;
      this.ballsRemaining = 0;
      this.ballVisible = false;
    }

    return this.currentState();
  }

  currentState(): RuntimeEngineState {
    return {
      score: this.score,
      ballsRemaining: this.ballsRemaining,
      multiplier: this.multiplier,
      roundFinished: this.roundFinished,
      view: createViewSnapshot(this.leftAngle, this.rightAngle, this.ballVisible),
    };
  }

  injectMachineEventsForDebug(events: MachineEvent[]): RuntimeEngineState {
    for (const event of events) {
      if (event.type === "rollover-enter") {
        this.score += 50;
      }

      if (event.type === "drain-enter") {
        this.ballsRemaining = Math.max(this.ballsRemaining - 1, 0);
        this.ballVisible = this.ballsRemaining > 0;
        this.roundFinished = this.ballsRemaining === 0;
      }
    }

    return this.currentState();
  }
}

function createViewSnapshot(
  leftAngle = 18,
  rightAngle = 162,
  ballVisible = false,
): GameViewSnapshot {
  return {
    board: {
      width: 600,
      height: 1200,
    },
    ball: ballVisible
      ? {
          x: 528,
          y: 1044,
          radius: 12,
        }
      : null,
    flippers: {
      left: {
        side: "left",
        pivotX: 220,
        pivotY: 1045,
        length: 96,
        thickness: 20,
        angleDeg: leftAngle,
      },
      right: {
        side: "right",
        pivotX: 380,
        pivotY: 1045,
        length: 96,
        thickness: 20,
        angleDeg: rightAngle,
      },
    },
    rollovers: [
      { tag: "lane/top-l", label: "L", x: 180, y: 150, lit: false },
      { tag: "lane/top-a", label: "A", x: 260, y: 130, lit: false },
      { tag: "lane/top-t", label: "T", x: 340, y: 130, lit: false },
      { tag: "lane/top-e", label: "E", x: 420, y: 150, lit: false },
    ],
  };
}

function lastHud(hudEvents: GameHudSnapshot[]): GameHudSnapshot {
  const hud = hudEvents.at(-1);
  if (!hud) {
    throw new Error("Expected at least one HUD event.");
  }
  return hud;
}

describe("GameRuntime", () => {
  it("publishes ready, running, paused, resumed, and game-over HUD snapshots", () => {
    const scheduler = new ManualAnimationScheduler();
    const engine = new FakeRuntimeEngine();
    const runtime = new GameRuntime({ scheduler, engine });
    const hudEvents: GameHudSnapshot[] = [];

    runtime.subscribeHud((hud) => {
      hudEvents.push(hud);
    });

    runtime.start();
    runtime.pause();
    runtime.resume();
    scheduler.runFrame(0);
    scheduler.runFrame(16);
    scheduler.runFrame(16);

    expect(hudEvents.map((hud) => hud.status)).toEqual([
      "ready",
      "running",
      "paused",
      "running",
      "running",
      "game-over",
    ]);
  });

  it("mirrors runtime state, ball presence, and processed input onto the mounted host element", () => {
    const scheduler = new ManualAnimationScheduler();
    const engine = new FakeRuntimeEngine();
    const runtime = new GameRuntime({ scheduler, engine });
    const hostElement = document.createElement("div");

    runtime.mount(hostElement);
    runtime.start();
    runtime.enqueueCommand({ type: "left-flip", pressed: true });
    runtime.enqueueCommand({ type: "launch", pressed: true });

    scheduler.runFrame(0);
    scheduler.runFrame(16);

    expect(hostElement.dataset.runtimeMounted).toBe("true");
    expect(hostElement.dataset.runtimeStatus).toBe("running");
    expect(hostElement.dataset.leftFlipActive).toBe("true");
    expect(hostElement.dataset.launchActive).toBe("true");
    expect(hostElement.dataset.ballPresent).toBe("true");
    expect(hostElement.dataset.runtimeScore).toBe("250");
    expect(hostElement.dataset.runtimeBallsRemaining).toBe("3");
    expect(hostElement.dataset.runtimeMultiplier).toBe("2");
    expect(hostElement.dataset.lastCommand).toBe("Launch laddas");
    expect(engine.appliedCommands).toEqual([
      { type: "left-flip", pressed: true },
      { type: "launch", pressed: true },
    ]);
  });

  it("publishes view snapshots from the simulation engine", () => {
    const scheduler = new ManualAnimationScheduler();
    const engine = new FakeRuntimeEngine();
    const runtime = new GameRuntime({ scheduler, engine });
    const viewEvents: GameViewSnapshot[] = [];

    runtime.subscribeView((view) => {
      viewEvents.push(view);
    });

    runtime.start();
    runtime.enqueueCommand({ type: "left-flip", pressed: true });
    scheduler.runFrame(0);
    scheduler.runFrame(16);

    expect(viewEvents.at(-1)?.ball).not.toBeNull();
    expect(viewEvents.at(-1)?.flippers.left.angleDeg).toBe(-24);
  });

  it("preserves mute state across restart and resets the game state", () => {
    const scheduler = new ManualAnimationScheduler();
    const engine = new FakeRuntimeEngine();
    const runtime = new GameRuntime({ scheduler, engine });
    const hudEvents: GameHudSnapshot[] = [];

    runtime.subscribeHud((hud) => {
      hudEvents.push(hud);
    });

    runtime.setMuted(true);
    runtime.restart();

    expect(lastHud(hudEvents)).toMatchObject({
      muted: true,
      score: 0,
      ballsRemaining: 3,
      multiplier: 1,
      status: "running",
    });
  });

  it("disposes the engine and clears host runtime markers", () => {
    const scheduler = new ManualAnimationScheduler();
    const engine = new FakeRuntimeEngine();
    const runtime = new GameRuntime({ scheduler, engine });
    const hostElement = document.createElement("div");

    runtime.mount(hostElement);
    runtime.start();
    runtime.dispose();

    expect(engine.dispose).toHaveBeenCalledTimes(1);
    expect(hostElement.dataset.runtimeMounted).toBeUndefined();
    expect(hostElement.dataset.ballPresent).toBeUndefined();
  });

  it("can inject semantic machine events through the debug seam", () => {
    const scheduler = new ManualAnimationScheduler();
    const engine = new FakeRuntimeEngine();
    const runtime = new GameRuntime({ scheduler, engine });
    const hostElement = document.createElement("div");

    runtime.mount(hostElement);
    runtime.start();
    runtime.injectMachineEventsForDebug([
      { type: "rollover-enter", tag: "lane/top-l" },
      { type: "drain-enter", tag: "drain/main" },
    ]);

    expect(hostElement.dataset.runtimeScore).toBe("50");
    expect(hostElement.dataset.runtimeBallsRemaining).toBe("2");
    expect(hostElement.dataset.ballPresent).toBe("true");
    expect(hostElement.dataset.runtimeStatus).toBe("running");
  });
});
