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

type LaunchProofHoldProfile = "rest" | "short" | "medium" | "full" | "relaunch";
type LaunchProofStrikeClassification =
  | "no_effective_strike"
  | "post_strike_route_rejection"
  | "strike_and_route_accepted";
type LaunchProofRouteCaptureDecision = "none" | "accepted" | "rejected";
type LaunchProofRouteRejectReason =
  | "distance_xy"
  | "distance_z"
  | "vy_gate"
  | "window_expired"
  | "no_route";

type LaunchProofCaseContract = Readonly<{
  caseId: string;
  holdProfile: LaunchProofHoldProfile;
  holdSteps: number;
  thresholdPx: number;
  thresholdVy: number;
  relaunchSecondHoldSteps?: number;
}>;

type LaunchProofCaseRecord = Readonly<{
  case_id: string;
  hold_profile: LaunchProofHoldProfile;
  dt_ms: number;
  hold_steps: number;
  relaunch_gap_steps: number;
  observation_steps: number;
  threshold_px: number;
  threshold_vy: number;
  plunger_delta: number;
  ball_displacement_magnitude: number;
  max_vy: number;
  min_vy: number;
  feed_inside_at_rest: boolean;
  separation_px_at_rest: number;
  route_capture_decision: LaunchProofRouteCaptureDecision;
  route_capture_reason: LaunchProofRouteRejectReason | null;
  sw16_exit_observed: boolean;
  contact_diagnostics: {
    maxOverlapPx: number;
    minRelativeVyAtContact: number | null;
    impulseTransferMarker: number;
    lastContactAtStep: number | null;
  };
  strike_classification: LaunchProofStrikeClassification;
}>;

const PR0206_DT_MS = 16;
const PR0206_PRE_RELEASE_STABILITY_STEPS = 10;
const PR0206_OBSERVATION_STEPS = 60;
const PR0206_RELAUNCH_GAP_STEPS = 16;
const PR0206_PROOF_MATRIX_CASES: readonly LaunchProofCaseContract[] = [
  {
    caseId: "K-REST-STEADY",
    holdProfile: "rest",
    holdSteps: 0,
    thresholdPx: 0,
    thresholdVy: 0,
  },
  {
    caseId: "K-SHORT-STEADY",
    holdProfile: "short",
    holdSteps: 8,
    thresholdPx: 2,
    thresholdVy: -8,
  },
  {
    caseId: "K-MEDIUM-STEADY",
    holdProfile: "medium",
    holdSteps: 26,
    thresholdPx: 4,
    thresholdVy: -20,
  },
  {
    caseId: "K-FULL-STEADY",
    holdProfile: "full",
    holdSteps: 56,
    thresholdPx: 8,
    thresholdVy: -40,
  },
  {
    caseId: "K-RELAUNCH-MEDIUM",
    holdProfile: "relaunch",
    holdSteps: 26,
    relaunchSecondHoldSteps: 26,
    thresholdPx: 4,
    thresholdVy: -20,
  },
];
const ALLOWED_ROUTE_REJECT_REASONS: readonly LaunchProofRouteRejectReason[] = [
  "distance_xy",
  "distance_z",
  "vy_gate",
  "window_expired",
  "no_route",
];

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

  it("proof baseline: full-charge release should produce deterministic launch effect signature", async () => {
    const world = await PhysicsWorld.create();

    try {
      const dtMs = 16;
      const holdSteps = 56;
      const observationSteps = 60;
      world.spawnBall();
      collectEventsUntil(world, 40, (events) => {
        return events.some((event) => event.type === "launcher-fed");
      });

      const startBall = world.currentSnapshot().ball;
      expect(startBall).not.toBeNull();
      if (!startBall) {
        throw new Error("Expected launcher ball at proof baseline start.");
      }

      world.applyCommand({ type: "launch", pressed: true });
      for (let index = 0; index < holdSteps; index += 1) {
        world.step(dtMs);
      }
      world.applyCommand({ type: "launch", pressed: false });

      let maxDisplacementPx = 0;
      let minVy = Number.POSITIVE_INFINITY;
      let lastRouteDecision: string | null = null;
      let lastRouteReason: string | null = null;

      for (let index = 0; index < observationSteps; index += 1) {
        world.step(dtMs);
        const snapshot = world.currentSnapshot();
        const ball = snapshot.ball;
        if (!ball) {
          continue;
        }
        maxDisplacementPx = Math.max(
          maxDisplacementPx,
          Math.hypot(ball.x - startBall.x, ball.y - startBall.y),
        );
        const telemetry = snapshot.launcherTelemetry;
        const vy = telemetry?.ball.velocity?.y ?? 0;
        minVy = Math.min(minVy, vy);
        lastRouteDecision = telemetry?.routeCapture.lastDecision ?? lastRouteDecision;
        lastRouteReason = telemetry?.routeCapture.lastRejectReason ?? lastRouteReason;
      }

      expect({
        maxDisplacementPx,
        minVy,
        lastRouteDecision,
        lastRouteReason,
      }).toMatchObject({
        maxDisplacementPx: expect.any(Number),
        minVy: expect.any(Number),
      });
      expect(maxDisplacementPx).toBeGreaterThanOrEqual(8);
      expect(minVy).toBeLessThanOrEqual(-40);
    } finally {
      world.dispose();
    }
  });

  it("runs the unchanged PR-0206 matrix and records proof-only root-cause telemetry contracts", async () => {
    const gateTag = PROTOTYPE_ALPHA_TABLE.gates[0].tag;
    const records: LaunchProofCaseRecord[] = [];

    for (const proofCase of PR0206_PROOF_MATRIX_CASES) {
      records.push(await runLaunchProofCase(proofCase, gateTag));
    }

    expect(records.map((record) => record.hold_profile)).toEqual([
      "rest",
      "short",
      "medium",
      "full",
      "relaunch",
    ]);
    expect(records.map((record) => record.hold_steps)).toEqual([0, 8, 26, 56, 26]);
    expect(records.map((record) => record.relaunch_gap_steps)).toEqual(
      Array.from({ length: records.length }, () => PR0206_RELAUNCH_GAP_STEPS),
    );
    expect(records.map((record) => record.observation_steps)).toEqual(
      Array.from({ length: records.length }, () => PR0206_OBSERVATION_STEPS),
    );
    expect(records.map((record) => record.dt_ms)).toEqual(
      Array.from({ length: records.length }, () => PR0206_DT_MS),
    );
    expect(records.map((record) => record.threshold_px)).toEqual([0, 2, 4, 8, 4]);
    expect(records.map((record) => record.threshold_vy)).toEqual([0, -8, -20, -40, -20]);

    const restRecord = records.find((record) => record.hold_profile === "rest");
    expect(restRecord).toBeDefined();
    if (!restRecord) {
      throw new Error("Expected rest profile proof record.");
    }
    expect(restRecord.feed_inside_at_rest).toBe(true);
    expect(restRecord.separation_px_at_rest).toBeGreaterThanOrEqual(0);
    expect(restRecord.separation_px_at_rest).toBeLessThanOrEqual(2);

    for (const record of records) {
      expect(["none", "accepted", "rejected"]).toContain(record.route_capture_decision);
      if (record.route_capture_reason !== null) {
        expect(ALLOWED_ROUTE_REJECT_REASONS).toContain(record.route_capture_reason);
      }
      expect([
        "no_effective_strike",
        "post_strike_route_rejection",
        "strike_and_route_accepted",
      ]).toContain(record.strike_classification);
      expect("gate-passed" in record).toBe(false);
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
      expect(releaseStepEvents).not.toContainEqual({
        type: "gate-passed",
        tag: gateTag,
      });

      const gateEvents = collectEventsUntil(world, 180, (events) => {
        return events.some((event) => event.type === "gate-passed" && event.tag === gateTag);
      });
      expect(gateEvents).toContainEqual({
        type: "gate-passed",
        tag: gateTag,
      });
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
      const releaseStepEvents = world.step(16);

      expect(releaseStepEvents).not.toContainEqual({
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

      const initialSnapshot = world.currentSnapshot();
      const initialPlungerY = initialSnapshot.plunger?.y ?? 0;
      const initialBallY = initialSnapshot.ball?.y ?? 0;

      world.applyCommand({ type: "launch", pressed: true });
      for (let index = 0; index < 20; index += 1) {
        world.step(16);
      }
      const chargedPlungerY = world.currentSnapshot().plunger?.y ?? initialPlungerY;

      world.applyCommand({ type: "launch", pressed: false });
      const releaseEvents = world.step(16);
      const minBallYAfterRelease = trackMinimumBallY(world, 120);

      expect(chargedPlungerY).toBeGreaterThan(initialPlungerY);
      expect(releaseEvents).toContainEqual({
        type: "launcher-released",
        tag: PROTOTYPE_ALPHA_TABLE.launcher.tag,
      });
      expect(minBallYAfterRelease).toBeLessThan(initialBallY);
    } finally {
      world.dispose();
    }
  });

  it("passes a 10-cycle launch matrix across short/medium/full holds without wedge lock", async () => {
    const world = await PhysicsWorld.create();

    try {
      const gateTag = PROTOTYPE_ALPHA_TABLE.gates[0].tag;
      const dividerTopY = Math.min(...VPW_SHOOTER_DIVIDER_PATH.map((point) => point.y));
      const leftFieldThreshold = PROTOTYPE_ALPHA_TABLE.flippers.left.pivot.x + 20;

      world.spawnBall();
      const idleEvents = collectEventsForSteps(world, 24);
      expect(idleEvents).not.toContainEqual({
        type: "gate-passed",
        tag: gateTag,
      });
      world.removeBall();

      const holdStepsMatrix = [2, 4, 6, 8, 10, 12, 14, 16, 18, 22];
      for (const holdSteps of holdStepsMatrix) {
        const cycle = runLaunchCycle(world, holdSteps, gateTag);
        const expectsRouteTraversal = holdSteps >= 12;

        expect(cycle.events).toContainEqual({
          type: "launcher-fed",
          tag: PROTOTYPE_ALPHA_TABLE.launcher.tag,
        });
        expect(cycle.events).toContainEqual({
          type: "launcher-released",
          tag: PROTOTYPE_ALPHA_TABLE.launcher.tag,
        });
        expect(cycle.gatePassCount).toBeLessThanOrEqual(1);
        if (expectsRouteTraversal) {
          expect(cycle.gatePassCount).toBe(1);
          expect(cycle.minY).toBeLessThan(dividerTopY);
          expect(cycle.minX).toBeLessThan(leftFieldThreshold);
        }
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

function classifyStrikeFromContact(args: {
  maxOverlapPx: number;
  minRelativeVyAtContact: number | null;
  impulseTransferMarker: number;
  routeCaptureDecision: LaunchProofRouteCaptureDecision;
}): LaunchProofStrikeClassification {
  const strikeEvidencePresent = args.maxOverlapPx >= 0.5
    || (args.minRelativeVyAtContact ?? Number.POSITIVE_INFINITY) <= -5
    || args.impulseTransferMarker >= 0.1;
  if (!strikeEvidencePresent) {
    return "no_effective_strike";
  }
  if (args.routeCaptureDecision === "accepted") {
    return "strike_and_route_accepted";
  }
  return "post_strike_route_rejection";
}

function normalizeRouteCaptureDecision(
  value: string | null | undefined,
): LaunchProofRouteCaptureDecision {
  if (value === "accepted" || value === "rejected" || value === "none") {
    return value;
  }
  return "none";
}

function normalizeRouteCaptureReason(
  value: string | null | undefined,
): LaunchProofRouteRejectReason | null {
  if (value === null || value === undefined) {
    return null;
  }
  if (
    value === "distance_xy"
    || value === "distance_z"
    || value === "vy_gate"
    || value === "window_expired"
    || value === "no_route"
  ) {
    return value;
  }
  return null;
}

function executeRelease(
  world: PhysicsWorldType,
  holdSteps: number,
  events: MachineEvent[],
): void {
  world.applyCommand({ type: "launch", pressed: true });
  for (let index = 0; index < holdSteps; index += 1) {
    events.push(...world.step(PR0206_DT_MS));
  }
  world.applyCommand({ type: "launch", pressed: false });
  events.push(...world.step(PR0206_DT_MS));
}

async function runLaunchProofCase(
  proofCase: LaunchProofCaseContract,
  gateTag: string,
): Promise<LaunchProofCaseRecord> {
  const world = await PhysicsWorld.create();

  try {
    world.spawnBall();
    const feedEvents = collectEventsUntil(world, 40, (events) => {
      return events.some((event) => event.type === "launcher-fed");
    });
    const allEvents: MachineEvent[] = [...feedEvents];
    const restSnapshot = world.currentSnapshot();
    const restBall = restSnapshot.ball;
    const restTelemetry = restSnapshot.launcherTelemetry;

    if (!restBall || !restTelemetry) {
      throw new Error(`Missing rest telemetry for launch proof case "${proofCase.caseId}".`);
    }
    const restSeparation = restTelemetry.contact.separationPx;
    if (restSeparation === null) {
      throw new Error(`Missing rest-separation telemetry for launch proof case "${proofCase.caseId}".`);
    }

    const restPlungerY = restSnapshot.plunger?.y ?? 0;
    let maxPlungerY = restPlungerY;
    let maxDisplacement = 0;
    let maxVy = Number.NEGATIVE_INFINITY;
    let minVy = Number.POSITIVE_INFINITY;
    let routeCaptureDecision: LaunchProofRouteCaptureDecision = "none";
    let routeCaptureReason: LaunchProofRouteRejectReason | null = null;
    let sw16ExitObserved = allEvents.some((event) => {
      return event.type === "gate-passed" && event.tag === gateTag;
    });
    let maxOverlapPx = 0;
    let minRelativeVyAtContact = Number.POSITIVE_INFINITY;
    let impulseTransferMarker = 0;
    let lastContactAtStep: number | null = null;

    if (proofCase.holdProfile === "rest") {
      for (let index = 0; index < PR0206_PRE_RELEASE_STABILITY_STEPS; index += 1) {
        allEvents.push(...world.step(PR0206_DT_MS));
      }
    } else {
      executeRelease(world, proofCase.holdSteps, allEvents);
      if (proofCase.holdProfile === "relaunch") {
        for (let index = 0; index < PR0206_RELAUNCH_GAP_STEPS; index += 1) {
          allEvents.push(...world.step(PR0206_DT_MS));
        }
        executeRelease(
          world,
          proofCase.relaunchSecondHoldSteps ?? proofCase.holdSteps,
          allEvents,
        );
      }
    }

    for (let index = 0; index < PR0206_OBSERVATION_STEPS; index += 1) {
      const stepEvents = world.step(PR0206_DT_MS);
      allEvents.push(...stepEvents);
      sw16ExitObserved = sw16ExitObserved || stepEvents.some((event) => {
        return event.type === "gate-passed" && event.tag === gateTag;
      });

      const snapshot = world.currentSnapshot();
      const ball = snapshot.ball;
      if (ball) {
        maxDisplacement = Math.max(
          maxDisplacement,
          Math.hypot(ball.x - restBall.x, ball.y - restBall.y),
        );
      }
      maxPlungerY = Math.max(maxPlungerY, snapshot.plunger?.y ?? maxPlungerY);

      const telemetry = snapshot.launcherTelemetry;
      if (!telemetry) {
        continue;
      }
      const vy = telemetry.ball.velocity?.y;
      if (Number.isFinite(vy)) {
        maxVy = Math.max(maxVy, vy ?? maxVy);
        minVy = Math.min(minVy, vy ?? minVy);
      }
      routeCaptureDecision = normalizeRouteCaptureDecision(
        telemetry.routeCapture.lastDecision ?? routeCaptureDecision,
      );
      routeCaptureReason = normalizeRouteCaptureReason(
        telemetry.routeCapture.lastRejectReason ?? routeCaptureReason,
      );
      maxOverlapPx = Math.max(maxOverlapPx, telemetry.contact.overlapPx);
      const relativeVyAtContact = telemetry.contact.relativeVyAtContact;
      if (Number.isFinite(relativeVyAtContact)) {
        minRelativeVyAtContact = Math.min(
          minRelativeVyAtContact,
          relativeVyAtContact ?? minRelativeVyAtContact,
        );
      }
      impulseTransferMarker = Math.max(
        impulseTransferMarker,
        telemetry.contact.impulseTransferMarker,
      );
      lastContactAtStep = telemetry.contact.lastContactAtStep ?? lastContactAtStep;
    }

    const normalizedMaxVy = Number.isFinite(maxVy) ? maxVy : 0;
    const normalizedMinVy = Number.isFinite(minVy) ? minVy : 0;
    const normalizedMinRelativeVyAtContact = Number.isFinite(minRelativeVyAtContact)
      ? minRelativeVyAtContact
      : null;
    const strikeClassification = classifyStrikeFromContact({
      maxOverlapPx,
      minRelativeVyAtContact: normalizedMinRelativeVyAtContact,
      impulseTransferMarker,
      routeCaptureDecision,
    });

    return {
      case_id: proofCase.caseId,
      hold_profile: proofCase.holdProfile,
      dt_ms: PR0206_DT_MS,
      hold_steps: proofCase.holdSteps,
      relaunch_gap_steps: PR0206_RELAUNCH_GAP_STEPS,
      observation_steps: PR0206_OBSERVATION_STEPS,
      threshold_px: proofCase.thresholdPx,
      threshold_vy: proofCase.thresholdVy,
      plunger_delta: Math.max(0, maxPlungerY - restPlungerY),
      ball_displacement_magnitude: maxDisplacement,
      max_vy: normalizedMaxVy,
      min_vy: normalizedMinVy,
      feed_inside_at_rest: restTelemetry.sensors.feedInside,
      separation_px_at_rest: restSeparation,
      route_capture_decision: routeCaptureDecision,
      route_capture_reason: routeCaptureReason,
      sw16_exit_observed: sw16ExitObserved,
      contact_diagnostics: {
        maxOverlapPx,
        minRelativeVyAtContact: normalizedMinRelativeVyAtContact,
        impulseTransferMarker,
        lastContactAtStep,
      },
      strike_classification: strikeClassification,
    };
  } finally {
    world.dispose();
  }
}

function collectEventsForSteps(world: PhysicsWorldType, steps: number): MachineEvent[] {
  const events: MachineEvent[] = [];

  for (let index = 0; index < steps; index += 1) {
    events.push(...world.step(16));
  }

  return events;
}

function runLaunchCycle(
  world: PhysicsWorldType,
  holdSteps: number,
  gateTag: string,
): Readonly<{
  events: MachineEvent[];
  gatePassCount: number;
  minX: number;
  minY: number;
}> {
  world.spawnBall();
  const feedEvents = collectEventsUntil(world, 40, (events) => {
    return events.some((event) => event.type === "launcher-fed");
  });

  const cycleEvents: MachineEvent[] = [...feedEvents];
  world.applyCommand({ type: "launch", pressed: true });
  for (let index = 0; index < holdSteps; index += 1) {
    cycleEvents.push(...world.step(16));
  }
  world.applyCommand({ type: "launch", pressed: false });
  cycleEvents.push(...world.step(16));

  let gatePassCount = cycleEvents.filter((event) => {
    return event.type === "gate-passed" && event.tag === gateTag;
  }).length;
  let minX = world.currentSnapshot().ball?.x ?? Number.POSITIVE_INFINITY;
  let minY = world.currentSnapshot().ball?.y ?? Number.POSITIVE_INFINITY;

  for (let index = 0; index < 300; index += 1) {
    const events = world.step(16);
    cycleEvents.push(...events);
    gatePassCount += events.filter((event) => {
      return event.type === "gate-passed" && event.tag === gateTag;
    }).length;
    const ball = world.currentSnapshot().ball;
    if (!ball) {
      break;
    }
    minX = Math.min(minX, ball.x);
    minY = Math.min(minY, ball.y);
  }

  return {
    events: cycleEvents,
    gatePassCount,
    minX,
    minY,
  };
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
