// @vitest-environment node

/**
 * Physics-world tests for Flunk-Out Frenzy prototype alpha.
 *
 * These tests exercise the Rapier-backed machine layer directly so the rules
 * engine can trust stable semantic events instead of raw physics handles.
 */

import { beforeAll, describe, expect, it } from "vitest";

import type { PrototypeAlphaTable } from "../table/prototypeAlphaTable";
import type { PhysicsWorld as PhysicsWorldType } from "./PhysicsWorld";
import type { MachineEvent } from "./physicsTypes";

let PhysicsWorld: typeof PhysicsWorldType;
let PROTOTYPE_ALPHA_TABLE: PrototypeAlphaTable;

describe("PhysicsWorld", () => {
  beforeAll(async () => {
    const performanceLike = globalThis.performance ?? {
      now: () => Date.now(),
    };

    Object.defineProperty(globalThis, "performance", {
      value: performanceLike,
      configurable: true,
      enumerable: true,
      writable: true,
    });
    Object.defineProperty(globalThis, "self", {
      value: globalThis,
      configurable: true,
      enumerable: true,
      writable: true,
    });

    ({ PhysicsWorld } = await import("./PhysicsWorld"));
    ({ PROTOTYPE_ALPHA_TABLE } = await import("../table/prototypeAlphaTable"));
  });

  it("rotates the flippers when input commands are applied", async () => {
    const world = await PhysicsWorld.create();

    try {
      const beforeLeft = world.currentSnapshot().flippers.left.angleDeg;
      const beforeRight = world.currentSnapshot().flippers.right.angleDeg;
      world.applyCommand({ type: "left-flip", pressed: true });
      world.applyCommand({ type: "right-flip", pressed: true });
      world.step(16);

      expect(world.currentSnapshot().flippers.left.angleDeg).toBeLessThan(beforeLeft);
      expect(world.currentSnapshot().flippers.right.angleDeg).toBeGreaterThan(beforeRight);
    } finally {
      world.dispose();
    }
  });

  it("launches the ball out of the launch lane after a charged release", async () => {
    const world = await PhysicsWorld.create();

    try {
      world.spawnBall();
      collectEventsUntil(world, 40, (events) => {
        return events.some((event) => event.type === "launcher-fed");
      });

      const initialY = world.currentSnapshot().ball?.y ?? 0;

      world.applyCommand({ type: "launch", pressed: true });
      collectEventsUntil(world, 40, (events) => {
        return events.some((event) => event.type === "launcher-charged");
      });
      for (let index = 0; index < 18; index += 1) {
        world.step(16);
      }

      world.applyCommand({ type: "launch", pressed: false });
      const releaseEvents = world.step(16);
      const gateEvents = collectEventsUntil(world, 120, (events) => {
        return events.some((event) => {
          return event.type === "gate-passed"
            && event.tag === PROTOTYPE_ALPHA_TABLE.gates[0].tag;
        });
      });

      expect(releaseEvents).toContainEqual({
        type: "launcher-released",
        tag: PROTOTYPE_ALPHA_TABLE.launcher.tag,
      });
      expect(gateEvents).toContainEqual({
        type: "gate-passed",
        tag: PROTOTYPE_ALPHA_TABLE.gates[0].tag,
      });
      expect(world.currentSnapshot().ball?.y ?? 10_000).toBeLessThan(initialY);
    } finally {
      world.dispose();
    }
  });

  it("emits explicit launcher feed and charged events from the launcher state machine", async () => {
    const world = await PhysicsWorld.create();

    try {
      world.spawnBall();

      const feedEvents = collectEventsUntil(world, 40, (events) => {
        return events.some((event) => event.type === "launcher-fed");
      });
      expect(feedEvents).toContainEqual({
        type: "launcher-fed",
        tag: PROTOTYPE_ALPHA_TABLE.launcher.tag,
      });

      world.applyCommand({ type: "launch", pressed: true });
      const chargedEvents = collectEventsUntil(world, 40, (events) => {
        return events.some((event) => event.type === "launcher-charged");
      });

      expect(chargedEvents).toContainEqual({
        type: "launcher-charged",
        tag: PROTOTYPE_ALPHA_TABLE.launcher.tag,
      });
    } finally {
      world.dispose();
    }
  });

  it("emits bumper, sling, rollover, and drain machine events from authored zones", async () => {
    const world = await PhysicsWorld.create();

    try {
      world.spawnBall({
        x: PROTOTYPE_ALPHA_TABLE.bumpers[0].x,
        y: PROTOTYPE_ALPHA_TABLE.bumpers[0].y,
      });
      const bumperEvents = world.step(16);
      expect(bumperEvents).toContainEqual({
        type: "bumper-fired",
        tag: PROTOTYPE_ALPHA_TABLE.bumpers[0].tag,
      });

      world.spawnBall({ x: 185, y: 930 });
      const slingEvents = world.step(16);
      expect(slingEvents).toContainEqual({
        type: "sling-fired",
        tag: PROTOTYPE_ALPHA_TABLE.slings[0].tag,
        side: "left",
      });

      world.spawnBall({
        x: PROTOTYPE_ALPHA_TABLE.rollovers[0].x,
        y: PROTOTYPE_ALPHA_TABLE.rollovers[0].y,
      });
      const rolloverEvents = world.step(16);
      expect(rolloverEvents).toContainEqual({
        type: "rollover-enter",
        tag: PROTOTYPE_ALPHA_TABLE.rollovers[0].tag,
      });

      world.spawnBall({
        x: PROTOTYPE_ALPHA_TABLE.drain.x,
        y: PROTOTYPE_ALPHA_TABLE.drain.y,
      });
      const drainEvents = world.step(16);
      expect(drainEvents).toContainEqual({
        type: "drain-enter",
        tag: PROTOTYPE_ALPHA_TABLE.drain.tag,
      });
      expect(world.currentSnapshot().ball).toBeNull();
    } finally {
      world.dispose();
    }
  });

  it("emits tripwire, target, and gate events from the authored device zones", async () => {
    const world = await PhysicsWorld.create();

    try {
      world.spawnBall({
        x: PROTOTYPE_ALPHA_TABLE.tripwires[0].x,
        y: PROTOTYPE_ALPHA_TABLE.tripwires[0].y,
      });
      expect(world.step(16)).toContainEqual({
        type: "tripwire-crossed",
        tag: PROTOTYPE_ALPHA_TABLE.tripwires[0].tag,
      });

      world.spawnBall({
        x: PROTOTYPE_ALPHA_TABLE.standupTargets[0].x,
        y: PROTOTYPE_ALPHA_TABLE.standupTargets[0].y,
      });
      expect(world.step(16)).toContainEqual({
        type: "standup-target-hit",
        tag: PROTOTYPE_ALPHA_TABLE.standupTargets[0].tag,
      });

      world.spawnBall({
        x: PROTOTYPE_ALPHA_TABLE.popupTargets[0].x,
        y: PROTOTYPE_ALPHA_TABLE.popupTargets[0].y,
      });
      expect(world.step(16)).toContainEqual({
        type: "popup-target-hit",
        tag: PROTOTYPE_ALPHA_TABLE.popupTargets[0].tag,
      });

      world.spawnBall({
        x: PROTOTYPE_ALPHA_TABLE.gates[0].x,
        y: PROTOTYPE_ALPHA_TABLE.gates[0].y,
      });
      expect(world.step(16)).toContainEqual({
        type: "gate-passed",
        tag: PROTOTYPE_ALPHA_TABLE.gates[0].tag,
      });
    } finally {
      world.dispose();
    }
  });

  it("supports the expanded future-facing machine event surface", () => {
    const futureEvents: MachineEvent[] = [
      { type: "tripwire-crossed", tag: "tripwire/main-return" },
      { type: "standup-target-hit", tag: "target/jock-left" },
      { type: "popup-target-hit", tag: "target/pop-center" },
      { type: "gate-passed", tag: "gate/orbit-return" },
      { type: "launch-lane-enter", tag: "lane/launch" },
      { type: "launcher-fed", tag: "launcher/main" },
      { type: "launcher-charged", tag: "launcher/main" },
      { type: "launcher-released", tag: "launcher/main" },
      { type: "ball-captured", tag: "capture/hole-left", deviceKind: "hole" },
      { type: "ball-ejected", tag: "capture/kickout-left", deviceKind: "kickout" },
      { type: "ball-saved", tag: "save/right-kickback", deviceKind: "kickback" },
    ];

    expect(futureEvents.map((event) => event.type)).toEqual([
      "tripwire-crossed",
      "standup-target-hit",
      "popup-target-hit",
      "gate-passed",
      "launch-lane-enter",
      "launcher-fed",
      "launcher-charged",
      "launcher-released",
      "ball-captured",
      "ball-ejected",
      "ball-saved",
    ]);
  });
});

function collectEventsUntil(
  world: PhysicsWorldType,
  maxSteps: number,
  predicate: (events: MachineEvent[]) => boolean,
): MachineEvent[] {
  for (let index = 0; index < maxSteps; index += 1) {
    const events = world.step(16);
    if (predicate(events)) {
      return events;
    }
  }

  throw new Error("Expected machine events were not emitted in time.");
}
