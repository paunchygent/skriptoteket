// @vitest-environment node

/**
 * Physics-world tests for Flunk-Out Frenzy prototype alpha.
 *
 * These tests exercise the Rapier-backed machine layer directly so the rules
 * engine can trust stable semantic events instead of raw physics handles.
 */

import { beforeAll, describe, expect, it } from "vitest";

import type { PrototypeAlphaTable } from "../table/prototypeAlphaTable";
import {
  VPW_LAUNCH_LANE_EXIT_TRIGGER_SPEC,
  VPW_RIGHT_RETURN_TRIGGER_SPEC,
  VPW_SHOOTER_PLUNGER_TRIGGER_SPEC,
} from "../table/prototypeAlphaVpwDonorDevices";
import {
  VPW_GATE_SPECS,
  VPW_SHOOTER_DIVIDER_PATH,
  VPW_SHOOTER_LANE_LEFT_BOUNDARY_SEGMENTS,
  VPW_SHOOTER_OUTER_INNER_EDGE,
} from "../table/prototypeAlphaVpwDonorMap";
import { isPointInLauncherLaneRegion } from "./plungerLaneState";
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
      const shooterCorridorSegments = PROTOTYPE_ALPHA_TABLE.physics.colliders.filter((collider) => {
        return collider.id.startsWith("outer-boundary-shooter-corridor:segment:");
      });
      world.spawnBall();
      const feedEvents = collectEventsUntil(world, 40, (events) => {
        return events.some((event) => event.type === "launcher-fed");
      });

      const initialY = world.currentSnapshot().ball?.y ?? 0;
      const initialPlungerY = world.currentSnapshot().plunger?.y ?? 0;
      expect(PROTOTYPE_ALPHA_TABLE.launcher.launchAssistX).toBe(0);
      expect(shooterCorridorSegments).toEqual(
        expect.arrayContaining([
          expect.objectContaining({
            shape: expect.objectContaining({
              kind: "thick-segment",
              radius: 2,
            }),
          }),
        ]),
      );
      expect(feedEvents).toContainEqual({
        type: "launcher-fed",
        tag: PROTOTYPE_ALPHA_TABLE.launcher.tag,
      });
      expect(feedEvents).not.toContainEqual({
        type: "gate-passed",
        tag: PROTOTYPE_ALPHA_TABLE.gates[0].tag,
      });

      world.applyCommand({ type: "launch", pressed: true });
      collectEventsUntil(world, 40, (events) => {
        return events.some((event) => event.type === "launcher-charged");
      });
      for (let index = 0; index < 18; index += 1) {
        world.step(16);
      }
      const chargedPlungerY = world.currentSnapshot().plunger?.y ?? initialPlungerY;

      world.applyCommand({ type: "launch", pressed: false });
      const releaseEvents = world.step(16);
      const gateEvents = releaseEvents.some((event) => {
        return event.type === "gate-passed" && event.tag === PROTOTYPE_ALPHA_TABLE.gates[0].tag;
      })
        ? []
        : collectEventsUntil(world, 120, (events) => {
            return events.some((event) => {
              return event.type === "gate-passed"
                && event.tag === PROTOTYPE_ALPHA_TABLE.gates[0].tag;
            });
          });
      const gatePhaseEvents = [...releaseEvents, ...gateEvents];
      const dividerTopY = Math.min(...VPW_SHOOTER_DIVIDER_PATH.map((point) => point.y));
      const minBallYAfterRelease = trackMinimumBallY(world, 180);
      const minBallXAfterRelease = trackMinimumBallX(world, 260);

      expect(releaseEvents).toContainEqual({
        type: "launcher-released",
        tag: PROTOTYPE_ALPHA_TABLE.launcher.tag,
      });
      expect(gatePhaseEvents).toContainEqual({
        type: "gate-passed",
        tag: PROTOTYPE_ALPHA_TABLE.gates[0].tag,
      });
      expect(chargedPlungerY).toBeGreaterThan(initialPlungerY);
      expect(world.currentSnapshot().plunger?.y ?? chargedPlungerY).toBeLessThan(chargedPlungerY);
      expect(minBallYAfterRelease).toBeLessThan(dividerTopY);
      expect(minBallYAfterRelease).toBeLessThan(initialY);
      expect(minBallXAfterRelease).toBeLessThan(PROTOTYPE_ALPHA_TABLE.flippers.left.pivot.x + 20);
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

  it("keeps a served ball contained in the shooter lane until it reaches the donor sw16 gate", async () => {
    const world = await PhysicsWorld.create();

    try {
      const launchGate = PROTOTYPE_ALPHA_TABLE.gates[0];
      expect(launchGate).toMatchObject({
        shape: VPW_LAUNCH_LANE_EXIT_TRIGGER_SPEC.shape,
        triggerPhase: "exit",
      });
      expect(VPW_SHOOTER_PLUNGER_TRIGGER_SPEC.shape.kind).toBe("rect");

      world.spawnBall(PROTOTYPE_ALPHA_TABLE.ball.spawn);
      const idleEvents = collectEventsForSteps(world, 12);
      const ball = world.currentSnapshot().ball;

      expect(idleEvents).toContainEqual({
        type: "launcher-fed",
        tag: PROTOTYPE_ALPHA_TABLE.launcher.tag,
      });
      expect(idleEvents).not.toContainEqual({
        type: "gate-passed",
        tag: launchGate.tag,
      });
      expect(idleEvents).not.toContainEqual({
        type: "launcher-released",
        tag: PROTOTYPE_ALPHA_TABLE.launcher.tag,
      });
      expect(ball).not.toBeNull();
      expect(isPointInLauncherLaneRegion(ball!, PROTOTYPE_ALPHA_TABLE.launcher)).toBe(true);
    } finally {
      world.dispose();
    }
  });

  it("does not treat the old full-height shooter aabb as launcher containment anymore", async () => {
    const world = await PhysicsWorld.create();
    const plungerShape = expectRectTriggerShape(VPW_SHOOTER_PLUNGER_TRIGGER_SPEC.shape);

    try {
      const corridorProbe = midpointBetweenBoundariesAtY(
        VPW_SHOOTER_LANE_LEFT_BOUNDARY_SEGMENTS.wall010,
        VPW_SHOOTER_OUTER_INNER_EDGE,
        640,
      );
      expect(corridorProbe).not.toBeNull();
      expect(
        isPointInLauncherLaneRegion(corridorProbe!, PROTOTYPE_ALPHA_TABLE.launcher),
      ).toBe(true);

      const laneTopY = topYForLauncherRegions(PROTOTYPE_ALPHA_TABLE.launcher.laneRegions);
      const probe = {
        x: plungerShape.center.x,
        y: laneTopY - PROTOTYPE_ALPHA_TABLE.ball.radius * 2,
      };

      expect(isPointInLauncherLaneRegion(probe, PROTOTYPE_ALPHA_TABLE.launcher)).toBe(false);
      world.spawnBall(probe);

      const events = collectEventsForSteps(world, 6);
      expect(events).not.toContainEqual({
        type: "launcher-fed",
        tag: PROTOTYPE_ALPHA_TABLE.launcher.tag,
      });
    } finally {
      world.dispose();
    }
  });

  it("does not fire the right-return tripwire for an aabb-only false positive outside the rotated donor gate", async () => {
    const world = await PhysicsWorld.create();

    try {
      const probe = falsePositiveProbeForRotatedRect(
        VPW_GATE_SPECS.rightReturn,
        PROTOTYPE_ALPHA_TABLE.ball.radius,
      );
      world.spawnBall(probe);

      expect(world.step(16)).not.toContainEqual({
        type: "tripwire-crossed",
        tag: "tripwire/right-orbit-return",
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

      const leftSlingCentroid = centroidForTriangle(PROTOTYPE_ALPHA_TABLE.slings[0].vertices);
      world.spawnBall(leftSlingCentroid);
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

  it("holds a captured ball and emits an eject event when the hold window expires", async () => {
    const world = await PhysicsWorld.create();

    try {
      const captureDevice = PROTOTYPE_ALPHA_TABLE.captureDevices[0];
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

      const ejectEvents = collectEventsUntil(world, 120, (events) => {
        return events.some((event) => {
          return event.type === "ball-ejected" && event.tag === captureDevice.tag;
        });
      });
      expect(ejectEvents).toContainEqual({
        type: "ball-ejected",
        tag: captureDevice.tag,
        deviceKind: captureDevice.kind,
      });
      expect(world.currentSnapshot().ball).not.toBeNull();
    } finally {
      world.dispose();
    }
  });

  it("emits save events and applies the authored kickback impulse", async () => {
    const world = await PhysicsWorld.create();

    try {
      const saveDevice = PROTOTYPE_ALPHA_TABLE.saveDevices[0];
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

function collectEventsForSteps(world: PhysicsWorldType, steps: number): MachineEvent[] {
  const events: MachineEvent[] = [];

  for (let index = 0; index < steps; index += 1) {
    events.push(...world.step(16));
  }

  return events;
}

function centroidForTriangle(
  vertices: readonly [
    { x: number; y: number },
    { x: number; y: number },
    { x: number; y: number },
  ],
): { x: number; y: number } {
  return {
    x: (vertices[0].x + vertices[1].x + vertices[2].x) / 3,
    y: (vertices[0].y + vertices[1].y + vertices[2].y) / 3,
  };
}

function trackMinimumBallY(world: PhysicsWorldType, steps: number): number {
  let minY = world.currentSnapshot().ball?.y ?? Number.POSITIVE_INFINITY;

  for (let index = 0; index < steps; index += 1) {
    world.step(16);
    minY = Math.min(minY, world.currentSnapshot().ball?.y ?? minY);
  }

  return minY;
}

function trackMinimumBallX(world: PhysicsWorldType, steps: number): number {
  let minX = world.currentSnapshot().ball?.x ?? Number.POSITIVE_INFINITY;

  for (let index = 0; index < steps; index += 1) {
    world.step(16);
    minX = Math.min(minX, world.currentSnapshot().ball?.x ?? minX);
  }

  return minX;
}

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

function topYForLauncherRegions(
  regions: PrototypeAlphaTable["launcher"]["laneRegions"],
): number {
  return Math.min(
    ...regions.flatMap((region) => {
      switch (region.kind) {
        case "rect":
          return [region.center.y - region.height / 2];
        case "circle":
          return [region.center.y - region.radius];
        case "capsule":
          return [region.center.y - region.length / 2 - region.radius];
        case "donor-corridor":
          return region.leftBoundary.map((point) => point.y);
        case "polygon":
          return region.points.map((point) => point.y);
      }
    }),
  );
}

function expectRectTriggerShape(
  shape: (typeof VPW_SHOOTER_PLUNGER_TRIGGER_SPEC)["shape"],
): Extract<(typeof VPW_SHOOTER_PLUNGER_TRIGGER_SPEC)["shape"], { kind: "rect" }> {
  if (shape.kind !== "rect") {
    throw new Error(`Expected rect trigger shape, got ${shape.kind}.`);
  }

  return shape;
}

function expectCapsuleTriggerShape(
  shape: (typeof VPW_RIGHT_RETURN_TRIGGER_SPEC)["shape"],
): Extract<(typeof VPW_RIGHT_RETURN_TRIGGER_SPEC)["shape"], { kind: "capsule" }> {
  if (shape.kind !== "capsule") {
    throw new Error(`Expected capsule trigger shape, got ${shape.kind}.`);
  }

  return shape;
}

function midpointBetweenBoundariesAtY(
  leftBoundary: readonly { x: number; y: number }[],
  rightBoundary: readonly { x: number; y: number }[],
  y: number,
): { x: number; y: number } | null {
  const leftX = xOnBoundaryAtY(leftBoundary, y);
  const rightX = xOnBoundaryAtY(rightBoundary, y);
  if (leftX === null || rightX === null) {
    return null;
  }

  return {
    x: (leftX + rightX) / 2,
    y,
  };
}

function xOnBoundaryAtY(
  path: readonly { x: number; y: number }[],
  y: number,
): number | null {
  for (let index = 0; index < path.length - 1; index += 1) {
    const start = path[index];
    const end = path[index + 1];
    const minY = Math.min(start.y, end.y);
    const maxY = Math.max(start.y, end.y);
    if (y < minY || y > maxY) {
      continue;
    }
    if (Math.abs(end.y - start.y) < 1e-6) {
      return Math.max(start.x, end.x);
    }
    const ratio = (y - start.y) / (end.y - start.y);
    return start.x + (end.x - start.x) * ratio;
  }

  return null;
}
