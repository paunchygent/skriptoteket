/**
 * Plunger-lane state tests for Flunk-Out Frenzy.
 *
 * These tests keep launcher feed, charge, release, and relaunch transitions
 * explicit and pure before `PhysicsWorld` applies any Rapier impulses.
 */

import { describe, expect, it } from "vitest";

import { PROTOTYPE_ALPHA_TABLE } from "../table/prototypeAlphaTable";
import {
  createInitialPlungerLaneState,
  stepPlungerLaneState,
} from "./plungerLaneState";

const SETTLED_LAUNCH_BALL = {
  position: {
    x: PROTOTYPE_ALPHA_TABLE.ball.spawn.x,
    y: PROTOTYPE_ALPHA_TABLE.ball.spawn.y,
  },
  velocity: {
    x: 0,
    y: 0,
  },
} as const;

describe("stepPlungerLaneState", () => {
  it("emits feed, charged, and released launcher events in sequence", () => {
    const launcher = PROTOTYPE_ALPHA_TABLE.launcher;

    const fed = stepPlungerLaneState({
      state: createInitialPlungerLaneState(),
      ball: SETTLED_LAUNCH_BALL,
      launchPressed: false,
      launcher,
      dtMs: 16,
    });
    expect(fed.machineEvents).toEqual([{ type: "launcher-fed", tag: launcher.tag }]);
    expect(fed.nextState.phase).toBe("fed");

    const charged = stepPlungerLaneState({
      state: fed.nextState,
      ball: SETTLED_LAUNCH_BALL,
      launchPressed: true,
      launcher,
      dtMs: launcher.chargeMsMin,
    });
    expect(charged.machineEvents).toEqual([{ type: "launcher-charged", tag: launcher.tag }]);
    expect(charged.nextState.phase).toBe("charging");

    const released = stepPlungerLaneState({
      state: charged.nextState,
      ball: SETTLED_LAUNCH_BALL,
      launchPressed: false,
      launcher,
      dtMs: 16,
    });
    expect(released.machineEvents).toEqual([{ type: "launcher-released", tag: launcher.tag }]);
    expect(released.releaseImpulse).toEqual({
      x: launcher.launchAssistX,
      y: expect.any(Number),
    });
    expect(released.releaseImpulse?.y ?? 0).toBeLessThan(0);
    expect(released.nextState.phase).toBe("released");
  });

  it("re-enters the fed state after the relaunch cooldown when the ball remains in lane", () => {
    const launcher = PROTOTYPE_ALPHA_TABLE.launcher;
    const releasedState = {
      phase: "released" as const,
      chargeMs: 0,
      relaunchCooldownMs: launcher.relaunchCooldownMs,
      chargedEventEmitted: false,
    };

    const relit = stepPlungerLaneState({
      state: releasedState,
      ball: SETTLED_LAUNCH_BALL,
      launchPressed: false,
      launcher,
      dtMs: launcher.relaunchCooldownMs,
    });

    expect(relit.machineEvents).toEqual([{ type: "launcher-fed", tag: launcher.tag }]);
    expect(relit.nextState.phase).toBe("fed");
    expect(relit.releaseImpulse).toBeNull();
  });
});
