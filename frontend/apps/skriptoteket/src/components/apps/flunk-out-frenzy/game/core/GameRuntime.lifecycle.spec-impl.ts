/**
 * Runtime lifecycle and adapter regressions for Flunk-Out Frenzy.
 *
 * These tests keep the game loop, host element markers, and adapter effects
 * aligned after the monolithic runtime suite was decomposed.
 */

import { describe, expect, it } from "vitest";

import { GameRuntime } from "./GameRuntime";
import { ManualAnimationScheduler } from "./manualAnimationScheduler.spec-support";
import type { GameHudSnapshot, GameViewSnapshot } from "./runtimeTypes";
import type { GameEffectEvent } from "../presentation/gameEffectTypes";
import {
  DisabledAudioDirector,
  FakeAudioDirector,
  FakeRenderer,
  FakeRuntimeEngine,
  lastHud,
} from "./GameRuntime.spec-support";

describe("GameRuntime lifecycle", () => {
  it("publishes ready, running, paused, resumed, and game-over HUD snapshots", () => {
    const scheduler = new ManualAnimationScheduler();
    const engine = new FakeRuntimeEngine();
    const runtime = new GameRuntime({
      scheduler,
      engine,
      renderer: new FakeRenderer(),
      audio: new FakeAudioDirector(),
    });
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
    const runtime = new GameRuntime({
      scheduler,
      engine,
      renderer: new FakeRenderer(),
      audio: new FakeAudioDirector(),
    });
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
    expect(hostElement.dataset.runtimeBonusPoints).toBe("500");
    expect(hostElement.dataset.runtimeJackpotPoints).toBe("12500");
    expect(hostElement.dataset.runtimeJackpotLit).toBe("true");
    expect(hostElement.dataset.runtimeShootAgainLit).toBe("false");
    expect(hostElement.dataset.lastCommand).toBe("Launch laddas");
    expect(engine.appliedCommands).toEqual([
      { type: "left-flip", pressed: true },
      { type: "launch", pressed: true },
    ]);
  });

  it("publishes view snapshots from the simulation engine", () => {
    const scheduler = new ManualAnimationScheduler();
    const engine = new FakeRuntimeEngine();
    const runtime = new GameRuntime({
      scheduler,
      engine,
      renderer: new FakeRenderer(),
      audio: new FakeAudioDirector(),
    });
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
    const runtime = new GameRuntime({
      scheduler,
      engine,
      renderer: new FakeRenderer(),
      audio: new FakeAudioDirector(),
    });
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
      bonus: { points: 0, collectReady: false },
      jackpot: { points: 10_000, lit: false },
      ballLifecycle: { shootAgainLit: false },
      status: "running",
    });
  });

  it("disposes the engine and clears host runtime markers", () => {
    const scheduler = new ManualAnimationScheduler();
    const engine = new FakeRuntimeEngine();
    const runtime = new GameRuntime({
      scheduler,
      engine,
      renderer: new FakeRenderer(),
      audio: new FakeAudioDirector(),
    });
    const hostElement = document.createElement("div");

    runtime.mount(hostElement);
    runtime.start();
    runtime.dispose();

    expect(engine.dispose).toHaveBeenCalledTimes(1);
    expect(hostElement.dataset.runtimeMounted).toBeUndefined();
    expect(hostElement.dataset.ballPresent).toBeUndefined();
  });

  it("keeps HUD mute state false when the runtime audio adapter is disabled", () => {
    const scheduler = new ManualAnimationScheduler();
    const engine = new FakeRuntimeEngine();
    const renderer = new FakeRenderer();
    const audio = new DisabledAudioDirector();
    const runtime = new GameRuntime({ scheduler, engine, renderer, audio });
    const hudEvents: GameHudSnapshot[] = [];

    runtime.subscribeHud((hud) => {
      hudEvents.push(hud);
    });

    runtime.setMuted(true);
    runtime.start();

    expect(lastHud(hudEvents)).toMatchObject({ muted: false, status: "running" });
    expect(audio.setMuted).not.toHaveBeenCalled();
  });

  it("can inject semantic machine events through the debug seam", () => {
    const scheduler = new ManualAnimationScheduler();
    const engine = new FakeRuntimeEngine();
    const renderer = new FakeRenderer();
    const audio = new FakeAudioDirector();
    const runtime = new GameRuntime({ scheduler, engine, renderer, audio });
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

  it("feeds semantic effects into the renderer and audio adapters", () => {
    const scheduler = new ManualAnimationScheduler();
    const engine = new FakeRuntimeEngine();
    const renderer = new FakeRenderer();
    const audio = new FakeAudioDirector();
    const runtime = new GameRuntime({ scheduler, engine, renderer, audio });
    const hostElement = document.createElement("div");

    runtime.mount(hostElement);
    runtime.start();
    runtime.enqueueCommand({ type: "left-flip", pressed: true });

    scheduler.runFrame(0);
    scheduler.runFrame(16);

    expect(renderer.attach).toHaveBeenCalledWith(hostElement);
    expect(audio.consumeEffects).toHaveBeenCalled();

    const consumedEffects = audio.consumeEffects.mock.calls.flatMap(
      ([effects]) => effects as GameEffectEvent[],
    );

    expect(consumedEffects).toEqual(
      expect.arrayContaining([
        { type: "round-started" },
        { type: "ball-spawned" },
        { type: "flipper-fired", side: "left" },
      ]),
    );
  });
});
