/**
 * Prototype-alpha engine tests for Flunk-Out Frenzy.
 *
 * These tests verify the full local loop at the engine boundary: machine
 * events flow through rules, drained balls respawn until game over, and the
 * published view state stays aligned with the current ball lifecycle.
 */

import { describe, expect, it } from "vitest";

import type { RuntimeCommand } from "../core/runtimeTypes";
import type { MachineEvent, PhysicsSnapshot } from "../physics/physicsTypes";
import { PROTOTYPE_ALPHA_TABLE } from "../table/prototypeAlphaTable";
import {
  PrototypeAlphaGameEngine,
  type PrototypeAlphaPhysicsMachine,
} from "./PrototypeAlphaGameEngine";
import { RuleEngine } from "../rules/RuleEngine";

class FakePhysicsMachine implements PrototypeAlphaPhysicsMachine {
  public spawnCount = 0;
  private pendingEvents: MachineEvent[] = [];
  private ballVisible = false;

  reset(): void {
    this.pendingEvents = [];
    this.ballVisible = false;
    this.spawnCount = 0;
  }

  spawnBall(): void {
    this.spawnCount += 1;
    this.ballVisible = true;
  }

  applyCommand(_command: RuntimeCommand): void {}

  enqueueEvents(events: MachineEvent[]): void {
    this.pendingEvents.push(...events);
  }

  removeBall(): void {
    this.ballVisible = false;
  }

  step(_dtMs: number): MachineEvent[] {
    const events = [...this.pendingEvents];
    this.pendingEvents = [];

    if (events.some((event) => event.type === "drain-enter")) {
      this.ballVisible = false;
    }

    return events;
  }

  currentSnapshot(): PhysicsSnapshot {
    return {
      ball: this.ballVisible
        ? {
            x: PROTOTYPE_ALPHA_TABLE.ball.spawn.x,
            y: PROTOTYPE_ALPHA_TABLE.ball.spawn.y,
            radius: PROTOTYPE_ALPHA_TABLE.ball.radius,
          }
        : null,
      flippers: {
        left: {
          side: "left",
          pivotX: PROTOTYPE_ALPHA_TABLE.flippers.left.pivot.x,
          pivotY: PROTOTYPE_ALPHA_TABLE.flippers.left.pivot.y,
          length: PROTOTYPE_ALPHA_TABLE.flippers.left.length,
          thickness: PROTOTYPE_ALPHA_TABLE.flippers.left.thickness,
          angleDeg: PROTOTYPE_ALPHA_TABLE.flippers.left.restAngleDeg,
        },
        right: {
          side: "right",
          pivotX: PROTOTYPE_ALPHA_TABLE.flippers.right.pivot.x,
          pivotY: PROTOTYPE_ALPHA_TABLE.flippers.right.pivot.y,
          length: PROTOTYPE_ALPHA_TABLE.flippers.right.length,
          thickness: PROTOTYPE_ALPHA_TABLE.flippers.right.thickness,
          angleDeg: PROTOTYPE_ALPHA_TABLE.flippers.right.restAngleDeg,
        },
      },
    };
  }

  dispose(): void {}
}

describe("PrototypeAlphaGameEngine", () => {
  it("starts with a spawned first ball and default HUD state", () => {
    const physics = new FakePhysicsMachine();
    const engine = new PrototypeAlphaGameEngine(physics, new RuleEngine());

    const state = engine.startGame();

    expect(physics.spawnCount).toBe(1);
    expect(state.score).toBe(0);
    expect(state.ballsRemaining).toBe(3);
    expect(state.multiplier).toBe(1);
    expect(state.bonus).toEqual({
      points: 0,
      collectReady: false,
    });
    expect(state.jackpot).toEqual({
      points: 10_000,
      lit: false,
    });
    expect(state.ballLifecycle).toEqual({
      shootAgainLit: false,
    });
    expect(state.roundFinished).toBe(false);
    expect(state.view.ball).not.toBeNull();
    expect(state.effects).toEqual([
      { type: "round-started" },
      { type: "ball-spawned" },
    ]);
  });

  it("applies score and multiplier progression from semantic machine events", () => {
    const physics = new FakePhysicsMachine();
    const engine = new PrototypeAlphaGameEngine(physics, new RuleEngine());
    engine.startGame();

    physics.enqueueEvents([
      { type: "rollover-enter", tag: "lane/top-l" },
      { type: "rollover-enter", tag: "lane/top-a" },
      { type: "rollover-enter", tag: "lane/top-t" },
      { type: "rollover-enter", tag: "lane/top-e" },
    ]);
    const lanesState = engine.step(16);

    expect(lanesState.score).toBe(2200);
    expect(lanesState.multiplier).toBe(2);
    expect(lanesState.bonus).toEqual({
      points: 1000,
      collectReady: true,
    });
    expect(lanesState.effects).toEqual(
      expect.arrayContaining([
        { type: "rollover-lit", tag: "lane/top-l", label: "L" },
        { type: "rollover-lit", tag: "lane/top-a", label: "A" },
        { type: "rollover-lit", tag: "lane/top-t", label: "T" },
        { type: "rollover-lit", tag: "lane/top-e", label: "E" },
        { type: "late-bank-complete", multiplier: 2 },
      ]),
    );

    physics.enqueueEvents([
      { type: "bumper-fired", tag: "bumper/pop-top" },
      { type: "sling-fired", tag: "sling/left", side: "left" },
    ]);
    const scoringState = engine.step(16);

    expect(scoringState.score).toBe(2720);
    expect(scoringState.multiplier).toBe(2);
  });

  it("lights shoot-again from the jocks bank and keeps the current ball on the next drain", () => {
    const physics = new FakePhysicsMachine();
    const engine = new PrototypeAlphaGameEngine(physics, new RuleEngine());
    engine.startGame();

    physics.enqueueEvents([
      { type: "standup-target-hit", tag: "target/jock-left" },
      { type: "standup-target-hit", tag: "target/jock-center" },
      { type: "standup-target-hit", tag: "target/jock-right" },
    ]);
    const litState = engine.step(16);

    expect(litState.ballLifecycle.shootAgainLit).toBe(true);
    expect(litState.effects).toContainEqual({ type: "shoot-again-lit" });

    physics.enqueueEvents([{ type: "drain-enter", tag: "drain/main" }]);
    const drainState = engine.step(16);

    expect(drainState.ballsRemaining).toBe(3);
    expect(drainState.ballLifecycle.shootAgainLit).toBe(false);
    expect(drainState.view.ball).not.toBeNull();
  });

  it("respawns the next ball after the first two drains and ends the run on the third", () => {
    const physics = new FakePhysicsMachine();
    const engine = new PrototypeAlphaGameEngine(physics, new RuleEngine());
    engine.startGame();

    physics.enqueueEvents([{ type: "drain-enter", tag: "drain/main" }]);
    const firstDrain = engine.step(16);
    expect(firstDrain.ballsRemaining).toBe(2);
    expect(firstDrain.roundFinished).toBe(false);
    expect(firstDrain.view.ball).not.toBeNull();

    physics.enqueueEvents([{ type: "drain-enter", tag: "drain/main" }]);
    const secondDrain = engine.step(16);
    expect(secondDrain.ballsRemaining).toBe(1);
    expect(secondDrain.roundFinished).toBe(false);
    expect(secondDrain.view.ball).not.toBeNull();

    physics.enqueueEvents([{ type: "drain-enter", tag: "drain/main" }]);
    const thirdDrain = engine.step(16);
    expect(thirdDrain.ballsRemaining).toBe(0);
    expect(thirdDrain.roundFinished).toBe(true);
    expect(thirdDrain.view.ball).toBeNull();
    expect(thirdDrain.effects).toEqual([
      { type: "ball-drained", ballsRemaining: 0 },
      { type: "game-over", finalScore: 0 },
    ]);

    expect(physics.spawnCount).toBe(3);
  });

  it("lights and awards jackpot via popup-target and tripwire progression", () => {
    const physics = new FakePhysicsMachine();
    const engine = new PrototypeAlphaGameEngine(physics, new RuleEngine());
    engine.startGame();

    physics.enqueueEvents([{ type: "popup-target-hit", tag: "target/pop-study" }]);
    const litState = engine.step(16);

    expect(litState.jackpot).toEqual({
      points: 15000,
      lit: true,
    });
    expect(litState.effects).toContainEqual({ type: "jackpot-lit", points: 15000 });

    physics.enqueueEvents([{ type: "tripwire-crossed", tag: "tripwire/right-orbit-return" }]);
    const awardedState = engine.step(16);

    expect(awardedState.score).toBe(15000);
    expect(awardedState.jackpot).toEqual({
      points: 10000,
      lit: false,
    });
    expect(awardedState.effects).toEqual(
      expect.arrayContaining([
        { type: "tripwire-crossed", tag: "tripwire/right-orbit-return" },
        { type: "jackpot-awarded", points: 15000 },
      ]),
    );
  });

  it("surfaces target, tripwire, and gate machine events as semantic presentation effects", () => {
    const physics = new FakePhysicsMachine();
    const engine = new PrototypeAlphaGameEngine(physics, new RuleEngine());
    engine.startGame();

    physics.enqueueEvents([
      { type: "tripwire-crossed", tag: "tripwire/right-orbit-return" },
      { type: "standup-target-hit", tag: "target/jock-left" },
      { type: "popup-target-hit", tag: "target/pop-study" },
      { type: "gate-passed", tag: "gate/launch-lane-exit" },
    ]);
    const state = engine.step(16);

    expect(state.score).toBe(0);
    expect(state.multiplier).toBe(1);
    expect(state.effects).toEqual([
      { type: "tripwire-crossed", tag: "tripwire/right-orbit-return" },
      { type: "standup-target-hit", tag: "target/jock-left" },
      { type: "popup-target-hit", tag: "target/pop-study" },
      { type: "gate-passed", tag: "gate/launch-lane-exit" },
      { type: "jackpot-lit", points: 17500 },
    ]);
  });
});
