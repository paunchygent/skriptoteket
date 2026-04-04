// @vitest-environment node

import { beforeAll, describe, expect, it } from "vitest";

import type { PhysicsWorld as PhysicsWorldType } from "../PhysicsWorld";

let PhysicsWorld: typeof PhysicsWorldType;

describe("PhysicsWorld Flippers", () => {
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

    ({ PhysicsWorld } = await import("../PhysicsWorld"));
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
});
