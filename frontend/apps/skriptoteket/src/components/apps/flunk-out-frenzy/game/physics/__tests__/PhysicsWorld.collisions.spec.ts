// @vitest-environment node

import { beforeAll, describe, expect, it } from "vitest";

import type { PrototypeAlphaTable } from "../../table/prototypeAlphaTable";
import { VPW_GATE_SPECS } from "../../table/prototypeAlphaVpwDonorMap";
import { VPW_RIGHT_RETURN_TRIGGER_SPEC } from "../../table/prototypeAlphaVpwDonorDevices";
import type { PhysicsWorld as PhysicsWorldType } from "../PhysicsWorld";
import type { MachineEvent } from "../physicsTypes";

let PhysicsWorld: typeof PhysicsWorldType;
let PROTOTYPE_ALPHA_TABLE: PrototypeAlphaTable;

describe("PhysicsWorld Collisions", () => {
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

      const leftSling = PROTOTYPE_ALPHA_TABLE.slings[0];
      const leftSlingCentroid = {
        x: (leftSling.vertices[0].x + leftSling.vertices[1].x + leftSling.vertices[2].x) / 3,
        y: (leftSling.vertices[0].y + leftSling.vertices[1].y + leftSling.vertices[2].y) / 3,
      };
      world.spawnBall(leftSlingCentroid);
      const slingEvents = world.step(16);
      expect(slingEvents).toContainEqual({
        type: "sling-fired",
        tag: leftSling.tag,
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

  it("emits tripwire and target events from authored device zones", async () => {
    const world = await PhysicsWorld.create();
    const rightReturnShape = expectCapsuleTriggerShape(VPW_RIGHT_RETURN_TRIGGER_SPEC.shape);

    try {
      world.spawnBall({
        x: rightReturnShape.center.x,
        y: rightReturnShape.center.y,
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
    } finally {
      world.dispose();
    }
  });

  it("does not fire the right-return tripwire for an aabb-only false positive outside the rotated donor gate", async () => {
    const world = await PhysicsWorld.create();

    try {
      world.spawnBall(
        falsePositiveProbeForRotatedRect(
          VPW_GATE_SPECS.rightReturn,
          PROTOTYPE_ALPHA_TABLE.ball.radius,
        ),
      );

      expect(world.step(16)).not.toContainEqual({
        type: "tripwire-crossed",
        tag: "tripwire/right-orbit-return",
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
      { type: "ball-captured", tag: "capture/scoop-study", deviceKind: "hole" },
      { type: "ball-ejected", tag: "capture/scoop-study", deviceKind: "hole" },
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

function falsePositiveProbeForRotatedRect(
  rect: {
    center: { x: number; y: number };
    width: number;
    height: number;
  },
  ballRadius: number,
): { x: number; y: number } {
  return {
    x: rect.center.x + rect.width / 2 + ballRadius * 0.25,
    y: rect.center.y - rect.height / 2 - ballRadius * 0.9,
  };
}

function expectCapsuleTriggerShape(
  shape: (typeof VPW_RIGHT_RETURN_TRIGGER_SPEC)["shape"],
): Extract<(typeof VPW_RIGHT_RETURN_TRIGGER_SPEC)["shape"], { kind: "capsule" }> {
  if (shape.kind !== "capsule") {
    throw new Error(`Expected capsule trigger shape, got ${shape.kind}.`);
  }

  return shape;
}
