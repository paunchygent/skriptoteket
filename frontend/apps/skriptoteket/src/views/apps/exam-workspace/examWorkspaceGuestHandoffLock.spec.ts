/**
 * Exam workspace guest handoff cross-tab lock (TASK-SKRIPT-41-02-05, U7a).
 *
 * Expected behavior:
 *   Overlapping work runs one at a time in call order; a rejecting work item
 *   does not block the next item. The production lock name is the documented
 *   shared name.
 */

import { beforeEach, describe, expect, it } from "vitest";

import {
  createInMemoryGuestHandoffLock,
  createWebGuestHandoffLock,
  EXAM_WORKSPACE_GUEST_HANDOFF_LOCK_NAME,
  GuestHandoffLockUnavailableError,
} from "./examWorkspaceGuestHandoffLock";

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, reject, resolve };
}

/** Point the Web adapter at a throwaway lock manager, restoring afterwards. */
function setNavigatorLocks(value: unknown): () => void {
  const descriptor = Object.getOwnPropertyDescriptor(navigator, "locks");
  const originalValue: unknown = navigator.locks;
  Object.defineProperty(navigator, "locks", { configurable: true, value, writable: true });
  return () => {
    if (descriptor === undefined) {
      Object.defineProperty(navigator, "locks", {
        configurable: true,
        value: originalValue,
        writable: true,
      });
    } else {
      Object.defineProperty(navigator, "locks", descriptor);
    }
  };
}

async function rejectionName(promise: Promise<unknown>): Promise<string> {
  try {
    await promise;
  } catch (error: unknown) {
    return error instanceof DOMException ? error.name : "not-a-dom-exception";
  }
  return "resolved";
}

beforeEach(() => {
  localStorage.clear();
});

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

    const first = lock.run(
      async () => {
        order.push("first-start");
        await gate;
        order.push("first-end");
        return "first";
      },
      new AbortController().signal,
    );
    const second = lock.run(
      async () => {
        order.push("second");
        return "second";
      },
      new AbortController().signal,
    );

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
      lock.run(
        async () => {
          throw new Error("the post failed");
        },
        new AbortController().signal,
      ),
    ).rejects.toThrow("the post failed");

    await expect(lock.run(async () => "next", new AbortController().signal)).resolves.toBe("next");
  });
});

describe("guest handoff lock unavailability and abort (R6/R7)", () => {
  it("a missing navigator.locks is a typed refusal and runs no work", async () => {
    const restore = setNavigatorLocks(undefined);
    try {
      let ran = false;
      const outcome = await createWebGuestHandoffLock()
        .run(
          async () => {
            ran = true;
            return "work";
          },
          new AbortController().signal,
        )
        .then(
          (): unknown => "resolved",
          (error: unknown): unknown => error,
        );
      expect(ran).toBe(false);
      expect(outcome).toBeInstanceOf(GuestHandoffLockUnavailableError);
    } finally {
      restore();
    }
  });

  it("a denied lock request is a typed refusal keeping the original cause", async () => {
    const denial = new DOMException("Storage access is denied.", "SecurityError");
    const restore = setNavigatorLocks({
      request: async (): Promise<never> => {
        throw denial;
      },
    });
    try {
      let ran = false;
      const outcome = await createWebGuestHandoffLock()
        .run(
          async () => {
            ran = true;
            return "work";
          },
          new AbortController().signal,
        )
        .then(
          (): unknown => "resolved",
          (error: unknown): unknown => error,
        );
      expect(ran).toBe(false);
      expect(outcome).toBeInstanceOf(GuestHandoffLockUnavailableError);
      if (outcome instanceof GuestHandoffLockUnavailableError) {
        expect(outcome.cause).toBe(denial);
      } else {
        throw new Error("expected a GuestHandoffLockUnavailableError");
      }
    } finally {
      restore();
    }
  });

  it("a queued web request aborted through its signal rejects with AbortError and never runs work", async () => {
    const release = deferred<void>();
    let first = true;
    const request = (
      name: string,
      options: { signal?: AbortSignal },
      callback: () => Promise<string>,
    ): Promise<string> => {
      void name;
      if (options.signal?.aborted === true) {
        return Promise.reject(new DOMException("Aborted.", "AbortError"));
      }
      if (first) {
        first = false;
        return (async () => {
          await release.promise;
          return await callback();
        })();
      }
      return new Promise<string>((_resolve, reject) => {
        options.signal?.addEventListener(
          "abort",
          () => reject(new DOMException("Aborted.", "AbortError")),
          { once: true },
        );
      });
    };
    const restore = setNavigatorLocks({ request });
    try {
      const webLock = createWebGuestHandoffLock();
      const held = webLock.run(async () => "first", new AbortController().signal);
      const queued = new AbortController();
      let ranQueued = false;
      const waiting = webLock.run(
        async () => {
          ranQueued = true;
          return "second";
        },
        queued.signal,
      );
      queued.abort();
      expect(await rejectionName(waiting)).toBe("AbortError");
      expect(ranQueued).toBe(false);
      release.resolve();
      await expect(held).resolves.toBe("first");
    } finally {
      restore();
    }
  });

  it("a work error after the lock started rethrows the work error unchanged", async () => {
    const failure = new Error("the post failed");
    const restore = setNavigatorLocks({
      request: async (
        _name: string,
        _options: { signal?: AbortSignal },
        callback: () => Promise<string>,
      ): Promise<string> => await callback(),
    });
    try {
      const outcome = await createWebGuestHandoffLock()
        .run(
          async (): Promise<string> => {
            throw failure;
          },
          new AbortController().signal,
        )
        .then(
          (): unknown => "resolved",
          (error: unknown): unknown => error,
        );
      expect(outcome).toBe(failure);
      expect(outcome).not.toBeInstanceOf(GuestHandoffLockUnavailableError);
    } finally {
      restore();
    }
  });

  it("an aborted queued item rejects with AbortError without running, and the next item runs", async () => {
    const lock = createInMemoryGuestHandoffLock();
    const release = deferred<void>();
    const held = lock.run(() => release.promise, new AbortController().signal);
    const queued = new AbortController();
    let ranQueued = false;
    const waiting = lock.run(
      async () => {
        ranQueued = true;
        return "second";
      },
      queued.signal,
    );
    queued.abort();
    release.resolve();
    await held;
    expect(await rejectionName(waiting)).toBe("AbortError");
    expect(ranQueued).toBe(false);
    await expect(lock.run(async () => "third", new AbortController().signal)).resolves.toBe(
      "third",
    );
  });

  it("an already-aborted signal never runs the work", async () => {
    const lock = createInMemoryGuestHandoffLock();
    let ran = false;
    const pending = lock.run(
      async () => {
        ran = true;
        return "work";
      },
      AbortSignal.abort(),
    );
    expect(await rejectionName(pending)).toBe("AbortError");
    expect(ran).toBe(false);
  });
});
