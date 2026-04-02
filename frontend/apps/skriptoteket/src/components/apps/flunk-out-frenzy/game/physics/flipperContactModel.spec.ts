/**
 * Flipper-contact model tests for Flunk-Out Frenzy.
 *
 * These tests keep the flipper strike heuristics pure and bounded so
 * `PhysicsWorld` can reuse them without burying contact math inline.
 */

import { describe, expect, it } from "vitest";

import { PROTOTYPE_ALPHA_TABLE } from "../table/prototypeAlphaTable";
import { resolveFlipperContactImpulse } from "./flipperContactModel";

describe("resolveFlipperContactImpulse", () => {
  it("returns a stronger strike for contact near the flipper tip than near the base", () => {
    const flipper = PROTOTYPE_ALPHA_TABLE.flippers.left;
    const angleRad = (flipper.activeAngleDeg * Math.PI) / 180;

    const nearBase = resolveFlipperContactImpulse({
      ball: {
        x: 246,
        y: 1022,
        radius: PROTOTYPE_ALPHA_TABLE.ball.radius,
      },
      flipper,
      angleRad,
    });
    const nearTip = resolveFlipperContactImpulse({
      ball: {
        x: 281,
        y: 975,
        radius: PROTOTYPE_ALPHA_TABLE.ball.radius,
      },
      flipper,
      angleRad,
    });

    expect(nearBase).not.toBeNull();
    expect(nearTip).not.toBeNull();
    expect(Math.hypot(nearTip!.impulse.x, nearTip!.impulse.y)).toBeGreaterThan(
      Math.hypot(nearBase!.impulse.x, nearBase!.impulse.y),
    );
    expect(nearTip!.impulse.y).toBeLessThan(0);
    expect(nearTip!.point.x).toBeGreaterThan(nearBase!.point.x);
  });

  it("ignores balls that approach the flipper from underneath", () => {
    const flipper = PROTOTYPE_ALPHA_TABLE.flippers.right;
    const angleRad = (flipper.restAngleDeg * Math.PI) / 180;

    const contact = resolveFlipperContactImpulse({
      ball: {
        x: 438,
        y: 1052,
        radius: PROTOTYPE_ALPHA_TABLE.ball.radius,
      },
      flipper,
      angleRad,
    });

    expect(contact).toBeNull();
  });
});
