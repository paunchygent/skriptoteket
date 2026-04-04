// @vitest-environment node

/**
 * Launcher behavior regressions for Flunk-Out Frenzy physics world.
 *
 * These tests preserve feed, release, seam, and containment behavior while the
 * proof-matrix checks live in a separate imported module.
 */

import { beforeAll, describe, expect, it } from "vitest";

import type { PrototypeAlphaTable } from "../../table/prototypeAlphaTable";
import {
  VPW_SHOOTER_LANE_LEFT_BOUNDARY_SEGMENTS,
  VPW_SHOOTER_DIVIDER_PATH,
  VPW_SHOOTER_OUTER_INNER_EDGE,
} from "../../table/prototypeAlphaVpwDonorMap";
import { VPW_SHOOTER_PLUNGER_TRIGGER_SPEC } from "../../table/prototypeAlphaVpwDonorDevices";
import { isPointInLauncherLaneRegion } from "../plungerLaneState";
import type { PhysicsWorld as PhysicsWorldType } from "../PhysicsWorld";
import {
  collectEventsForSteps,
  collectEventsUntil,
  trackMinimumBallX,
  trackMinimumBallY,
} from "../test-support/physicsTestTelemetry";

let PhysicsWorld: typeof PhysicsWorldType;
let PROTOTYPE_ALPHA_TABLE: PrototypeAlphaTable;

describe("PhysicsWorld Launcher behavior", () => {
  beforeAll(async () => {
    const performanceLike = globalThis.performance ?? { now: () => Date.now() };
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
            shape: expect.objectContaining({ kind: "thick-segment", radius: 2 }),
          }),
        ]),
      );
      expect(feedEvents).toContainEqual({
        type: "launcher-fed",
        tag: PROTOTYPE_ALPHA_TABLE.launcher.tag,
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
              return event.type === "gate-passed" && event.tag === PROTOTYPE_ALPHA_TABLE.gates[0].tag;
            });
          });
      const gatePhaseEvents = [...releaseEvents, ...gateEvents];
      const dividerTopY = Math.min(...VPW_SHOOTER_DIVIDER_PATH.map((point) => point.y));

      expect(releaseEvents).toContainEqual({
        type: "launcher-released",
        tag: PROTOTYPE_ALPHA_TABLE.launcher.tag,
      });
      expect(gatePhaseEvents).toContainEqual({
        type: "gate-passed",
        tag: PROTOTYPE_ALPHA_TABLE.gates[0].tag,
      });
      const minBallYAfterRelease = trackMinimumBallY(world, 180);
      const minBallXAfterRelease = trackMinimumBallX(world, 260);
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
      const chargeEvents = collectEventsUntil(world, 40, (events) => {
        return events.some((event) => event.type === "launcher-charged");
      });
      expect(chargeEvents).toContainEqual({
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
      world.spawnBall();
      collectEventsUntil(world, 40, (events) => {
        return events.some((event) => event.type === "launcher-fed");
      });

      for (let index = 0; index < 200; index += 1) {
        world.step(16);
        const ball = world.currentSnapshot().ball;
        if (!ball) {
          continue;
        }
        expect(isPointInLauncherLaneRegion(ball, PROTOTYPE_ALPHA_TABLE.launcher)).toBe(true);
      }
    } finally {
      world.dispose();
    }
  });

  it("does not synthesize sw16 gate-passed on route start before physical donor-exit", async () => {
    const world = await PhysicsWorld.create();

    try {
      const gateTag = PROTOTYPE_ALPHA_TABLE.gates[0].tag;
      world.spawnBall();
      collectEventsUntil(world, 40, (events) => {
        return events.some((event) => event.type === "launcher-fed");
      });

      world.applyCommand({ type: "launch", pressed: true });
      for (let index = 0; index < 18; index += 1) {
        world.step(16);
      }
      world.applyCommand({ type: "launch", pressed: false });
      const releaseStepEvents = world.step(16);

      expect(releaseStepEvents).toContainEqual({
        type: "launcher-released",
        tag: PROTOTYPE_ALPHA_TABLE.launcher.tag,
      });
      expect(releaseStepEvents).not.toContainEqual({ type: "gate-passed", tag: gateTag });

      const gateEvents = collectEventsUntil(world, 180, (events) => {
        return events.some((event) => event.type === "gate-passed" && event.tag === gateTag);
      });
      expect(gateEvents).toContainEqual({ type: "gate-passed", tag: gateTag });
    } finally {
      world.dispose();
    }
  });

  it("does not allow main-world launch input to bypass the launcher chain release seam", async () => {
    const world = await PhysicsWorld.create();

    try {
      world.spawnBall({
        x: PROTOTYPE_ALPHA_TABLE.flippers.left.pivot.x,
        y: PROTOTYPE_ALPHA_TABLE.flippers.left.pivot.y,
      });

      world.applyCommand({ type: "launch", pressed: true });
      for (let index = 0; index < 12; index += 1) {
        world.step(16);
      }
      world.applyCommand({ type: "launch", pressed: false });

      expect(world.step(16)).not.toContainEqual({
        type: "launcher-released",
        tag: PROTOTYPE_ALPHA_TABLE.launcher.tag,
      });
    } finally {
      world.dispose();
    }
  });

  it("moves the plunger and advances the ball under direct launch commands without UI dependencies", async () => {
    const world = await PhysicsWorld.create();

    try {
      world.spawnBall();
      collectEventsUntil(world, 40, (events) => {
        return events.some((event) => event.type === "launcher-fed");
      });

      const initialPlungerY = world.currentSnapshot().plunger?.y ?? 0;
      const initialBallY = world.currentSnapshot().ball?.y ?? 0;

      world.applyCommand({ type: "launch", pressed: true });
      for (let index = 0; index < 30; index += 1) {
        world.step(16);
      }
      expect(world.currentSnapshot().plunger?.y).toBeGreaterThan(initialPlungerY);

      world.applyCommand({ type: "launch", pressed: false });
      for (let index = 0; index < 60; index += 1) {
        world.step(16);
      }
      expect(world.currentSnapshot().ball?.y).toBeLessThan(initialBallY);
    } finally {
      world.dispose();
    }
  });

  it("passes a 10-cycle launch matrix across short/medium/full holds without wedge lock", async () => {
    const gateTag = PROTOTYPE_ALPHA_TABLE.gates[0].tag;
    const world = await PhysicsWorld.create();

    try {
      for (let cycle = 0; cycle < 10; cycle += 1) {
        world.spawnBall();
        collectEventsUntil(world, 40, (events) => {
          return events.some((event) => event.type === "launcher-fed");
        });

        const holdSteps = cycle % 3 === 0 ? 10 : cycle % 3 === 1 ? 30 : 56;
        world.applyCommand({ type: "launch", pressed: true });
        for (let index = 0; index < holdSteps; index += 1) {
          world.step(16);
        }
        world.applyCommand({ type: "launch", pressed: false });

        let gatePassed = false;
        for (let index = 0; index < 200; index += 1) {
          const events = world.step(16);
          if (events.some((event) => event.type === "gate-passed" && event.tag === gateTag)) {
            gatePassed = true;
            break;
          }
        }
        expect(gatePassed).toBe(true);
      }
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
      expect(isPointInLauncherLaneRegion(corridorProbe!, PROTOTYPE_ALPHA_TABLE.launcher)).toBe(true);

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
});

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
  return { x: (leftX + rightX) / 2, y };
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
