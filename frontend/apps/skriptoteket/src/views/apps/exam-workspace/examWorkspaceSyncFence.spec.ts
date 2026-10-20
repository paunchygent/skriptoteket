/**
 * Exam workspace sync fence (TASK-SKRIPT-40-04-14, F1).
 *
 * The generation rule: every async result carries the generation it started
 * in, and anything older is dropped before it can touch state. A bump
 * resolves every outstanding settle as `stale` at once, even while the
 * transport promise never settles; a later settlement of a stale token still
 * yields `stale`, and a stale rejection stays silent.
 */

import { describe, expect, it } from "vitest";

import { createSyncFence } from "./examWorkspaceSyncFence";

function deferred<T>(): {
  promise: Promise<T>;
  resolve: (value: T) => void;
  reject: (reason: unknown) => void;
} {
  let resolveFn: ((value: T) => void) | null = null;
  let rejectFn: ((reason: unknown) => void) | null = null;
  const promise = new Promise<T>((resolve, reject) => {
    resolveFn = resolve;
    rejectFn = reject;
  });
  return {
    promise,
    reject: (reason: unknown) => {
      if (rejectFn !== null) {
        rejectFn(reason);
      }
    },
    resolve: (value: T) => {
      if (resolveFn !== null) {
        resolveFn(value);
      }
    },
  };
}

describe("the sync fence", () => {
  it("hands out a token that is current until a bump retires it", () => {
    const fence = createSyncFence();
    const token = fence.begin();
    expect(fence.isCurrent(token)).toBe(true);
    fence.retire();
    expect(fence.isCurrent(token)).toBe(false);
    expect(fence.isCurrent(fence.begin())).toBe(true);
  });

  it("settles a same-generation resolution as current with its value", async () => {
    const fence = createSyncFence();
    const token = fence.begin();
    const pending = deferred<string>();
    const settled = fence.settle(token, pending.promise);
    pending.resolve("fresh copy");
    await expect(settled).resolves.toEqual({ kind: "current", value: "fresh copy" });
  });

  it("settles a same-generation rejection as failed with its error", async () => {
    const fence = createSyncFence();
    const token = fence.begin();
    const pending = deferred<string>();
    const settled = fence.settle(token, pending.promise);
    const failure = new Error("network down");
    pending.reject(failure);
    const outcome = await settled;
    expect(outcome.kind).toBe("failed");
    if (outcome.kind === "failed") {
      expect(outcome.error).toBe(failure);
    }
  });

  it("resolves every outstanding settle as stale at once on retire, while the promises never settle", async () => {
    const fence = createSyncFence();
    const token = fence.begin();
    const first = deferred<string>();
    const second = deferred<number>();
    const settledFirst = fence.settle(token, first.promise);
    const settledSecond = fence.settle(token, second.promise);
    fence.retire();
    await expect(settledFirst).resolves.toEqual({ kind: "stale" });
    await expect(settledSecond).resolves.toEqual({ kind: "stale" });
    // Neither transport promise settled: the bump alone resolved both waits.
  });

  it("yields stale when the promise resolves after its token went stale", async () => {
    const fence = createSyncFence();
    const token = fence.begin();
    const pending = deferred<string>();
    const settled = fence.settle(token, pending.promise);
    fence.retire();
    pending.resolve("late copy");
    await expect(settled).resolves.toEqual({ kind: "stale" });
  });

  it("yields stale and stays silent when the promise rejects after its token went stale", async () => {
    const fence = createSyncFence();
    const token = fence.begin();
    const pending = deferred<string>();
    const settled = fence.settle(token, pending.promise);
    fence.retire();
    pending.reject(new Error("late failure"));
    await expect(settled).resolves.toEqual({ kind: "stale" });
  });

  it("settles stale at once for an already stale token and swallows its later rejection", async () => {
    const fence = createSyncFence();
    const token = fence.begin();
    fence.retire();
    const pending = deferred<string>();
    await expect(fence.settle(token, pending.promise)).resolves.toEqual({ kind: "stale" });
    pending.reject(new Error("abandoned failure"));
  });

  it("keeps only the newest generation current across retires", () => {
    const fence = createSyncFence();
    const first = fence.begin();
    fence.retire();
    const second = fence.begin();
    fence.retire();
    const third = fence.begin();
    expect(fence.isCurrent(first)).toBe(false);
    expect(fence.isCurrent(second)).toBe(false);
    expect(fence.isCurrent(third)).toBe(true);
  });

  it("exposes the current generation, kept in step by retire", () => {
    const fence = createSyncFence();
    expect(fence.generation.value).toBe(0);
    fence.begin();
    expect(fence.generation.value).toBe(0);
    fence.retire();
    expect(fence.generation.value).toBe(1);
    expect(fence.isCurrent(fence.begin())).toBe(true);
    fence.retire();
    expect(fence.generation.value).toBe(2);
  });
});
