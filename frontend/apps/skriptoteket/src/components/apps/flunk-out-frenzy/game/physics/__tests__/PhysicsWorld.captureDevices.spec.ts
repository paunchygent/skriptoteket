// @vitest-environment node

import { beforeAll, describe, expect, it } from "vitest";

import type { PrototypeAlphaTable } from "../../table/prototypeAlphaTable";
import type { PhysicsWorld as PhysicsWorldType } from "../PhysicsWorld";
import { collectEventsForSteps } from "../test-support/physicsTestTelemetry";

let PhysicsWorld: typeof PhysicsWorldType;
let PROTOTYPE_ALPHA_TABLE: PrototypeAlphaTable;

describe("PhysicsWorld Capture Devices", () => {
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
    ({ PROTOTYPE_ALPHA_TABLE } = await import("../../table/prototypeAlphaTable"));
  });

  it("holds a captured ball and emits an eject event when the hold window expires", async () => {
    const world = await PhysicsWorld.create();
    const captureDevice = PROTOTYPE_ALPHA_TABLE.captureDevices[0];

    try {
      world.spawnBall({
        x: captureDevice.x,
        y: captureDevice.y,
      });

      const captureEvents = world.step(16);
      expect(captureEvents).toContainEqual({
        type: "ball-captured",
        tag: captureDevice.tag,
        deviceKind: captureDevice.kind,
      });

      const ejectEvents = collectEventsForSteps(world, 120);
      expect(ejectEvents).toContainEqual(
        expect.objectContaining({
          type: "ball-ejected",
          tag: captureDevice.tag,
          deviceKind: captureDevice.kind,
        }),
      );
      expect(world.currentSnapshot().ball).not.toBeNull();
    } finally {
      world.dispose();
    }
  });

  it("emits save events and applies the authored kickback impulse", async () => {
    const world = await PhysicsWorld.create();
    const saveDevice = PROTOTYPE_ALPHA_TABLE.saveDevices[0];

    try {
      world.spawnBall({
        x: saveDevice.x,
        y: saveDevice.y,
      });
      const beforeSaveX = world.currentSnapshot().ball?.x ?? saveDevice.x;
      const beforeSaveY = world.currentSnapshot().ball?.y ?? saveDevice.y;

      const saveEvents = world.step(16);
      expect(saveEvents).toContainEqual({
        type: "ball-saved",
        tag: saveDevice.tag,
        deviceKind: saveDevice.kind,
      });

      for (let index = 0; index < 10; index += 1) {
        world.step(16);
      }

      const afterSave = world.currentSnapshot().ball;
      const afterSaveX = afterSave?.x ?? beforeSaveX;
      const afterSaveY = afterSave?.y ?? beforeSaveY;
      const traveledDistance = Math.hypot(afterSaveX - beforeSaveX, afterSaveY - beforeSaveY);

      expect(afterSave).not.toBeNull();
      expect(traveledDistance).toBeGreaterThan(8);
    } finally {
      world.dispose();
    }
  });
});
