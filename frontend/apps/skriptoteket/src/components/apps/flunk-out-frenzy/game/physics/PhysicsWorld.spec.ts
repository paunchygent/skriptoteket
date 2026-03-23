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

      const initialY = world.currentSnapshot().ball?.y ?? 0;

      world.applyCommand({ type: "launch", pressed: true });
      for (let index = 0; index < 12; index += 1) {
        world.step(16);
      }

      world.applyCommand({ type: "launch", pressed: false });
      for (let index = 0; index < 12; index += 1) {
        world.step(16);
      }

      expect(world.currentSnapshot().ball?.y ?? 10_000).toBeLessThan(initialY);
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
});
