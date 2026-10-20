/**
 * Exam workspace guest handoff cross-tab lock (TASK-SKRIPT-41-02-05, U7a).
 *
 * Expected behavior:
 *   Overlapping work runs one at a time in call order; a rejecting work item
 *   does not block the next item. The production lock name is the documented
 *   shared name.
 */

import { describe, expect, it } from "vitest";

import {
  createInMemoryGuestHandoffLock,
  EXAM_WORKSPACE_GUEST_HANDOFF_LOCK_NAME,
} from "./examWorkspaceGuestHandoffLock";

describe("guest handoff lock", () => {
  it("uses the documented shared name", () => {
    expect(EXAM_WORKSPACE_GUEST_HANDOFF_LOCK_NAME).toBe(
      "skriptoteket.exam-workspace.guest-handoff",
    );
  });

  it("serializes overlapping work in call order", async () => {
    const lock = createInMemoryGuestHandoffLock();
    const order: string[] = [];
    let releaseFirst!: () => void;
    const gate = new Promise<void>((resolve) => {
      releaseFirst = resolve;
    });

    const first = lock.run(async () => {
      order.push("first-start");
      await gate;
      order.push("first-end");
      return "first";
    });
    const second = lock.run(async () => {
      order.push("second");
      return "second";
    });

    await Promise.resolve();
    await Promise.resolve();
    expect(order).toEqual(["first-start"]);

    releaseFirst();
    await expect(first).resolves.toBe("first");
    await expect(second).resolves.toBe("second");
    expect(order).toEqual(["first-start", "first-end", "second"]);
  });

  it("a rejecting work item does not block the next item", async () => {
    const lock = createInMemoryGuestHandoffLock();

    await expect(
      lock.run(async () => {
        throw new Error("the post failed");
      }),
    ).rejects.toThrow("the post failed");

    await expect(
      lock.run(async () => "next"),
    ).resolves.toBe("next");
  });
});
