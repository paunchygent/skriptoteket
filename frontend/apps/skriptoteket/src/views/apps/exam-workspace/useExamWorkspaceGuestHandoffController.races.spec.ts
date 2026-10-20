/**
 * Guest handoff controller race repair proof (TASK-SKRIPT-41-02-05, U7b).
 *
 * Expected behavior (review ba74ef97 R1-R3, fixed):
 *   a) Disposing the scope while the first draft load is pending posts
 *      nothing and records nothing.
 *   b) A background retry disposed while its draft load is pending makes no
 *      second POST and records nothing.
 *   c) Removing stale A keeps B's draft and B's record; a new controller's
 *      start makes no POST.
 *   d) Retrying stale vault-full A after B was permanently rejected makes no
 *      POST; the notice becomes permanent.
 *   e) Retrying stale vault-full A after the slot was emptied makes no POST;
 *      the notice closes.
 *   f) Two controllers over one shared lock POST a rejected cursor once;
 *      both end with the permanent notice.
 *   g) remove() with a retired owner clears nothing.
 */

import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { effectScope } from "vue";

import { createLocalStorageGuestHandoffRejectionStorage } from "./examWorkspaceGuestHandoffRejection";
import {
  createInMemoryGuestHandoffLock,
  createWebGuestHandoffLock,
} from "./examWorkspaceGuestHandoffLock";
import type { StoredGuestDraft } from "./examWorkspaceGuestDraftStorage";
import { runGuestHandoff } from "./useExamWorkspaceGuestHandoff";
import { useExamWorkspaceGuestHandoffController } from "./useExamWorkspaceGuestHandoffController";
import {
  guestHandoffApiError,
  guestHandoffOwnerStub,
  liveAttempt,
  seedGuestHandoffHarness,
} from "./useExamWorkspaceGuestHandoff.specSupport";

const B_CURSOR = "20000000-0000-4000-8000-000000000002";

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, reject, resolve };
}

async function replaceSlotWithB(
  storage: Awaited<ReturnType<typeof seedGuestHandoffHarness>>["storage"],
) {
  const current = (await storage.load())!;
  const b = { ...current.draft, cursor: B_CURSOR };
  expect(await storage.replaceIf(current.draft.cursor, { ...current, draft: b })).toBe(true);
  return b;
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

beforeEach(() => {
  setActivePinia(createPinia());
  localStorage.clear();
});

describe("useExamWorkspaceGuestHandoffController races", () => {
  it("a) disposing while the first draft load is pending posts and records nothing", async () => {
    const harness = await seedGuestHandoffHarness();
    const rejections = createLocalStorageGuestHandoffRejectionStorage();
    const stored = await harness.storage.load();
    const load = deferred<StoredGuestDraft | null>();
    const storage = { ...harness.storage, load: () => load.promise };
    harness.teacher.importExamWorkspaceGuestDraft.mockRejectedValue(guestHandoffApiError(422));
    const scope = effectScope();
    const controller = scope.run(() =>
      useExamWorkspaceGuestHandoffController({ ...harness, rejections, storage }),
    )!;
    try {
      const pending = controller.start();
      scope.stop();
      expect(harness.teacher.importExamWorkspaceGuestDraft).not.toHaveBeenCalled();
      load.resolve(stored);
      await expect(pending).resolves.toBeNull();
      expect(harness.teacher.importExamWorkspaceGuestDraft).not.toHaveBeenCalled();
      expect(rejections.read()).toBeNull();
    } finally {
      scope.stop();
    }
  });

  it("b) a background retry disposed while its draft load is pending makes no second POST", async () => {
    vi.useFakeTimers();
    try {
      const harness = await seedGuestHandoffHarness();
      const rejections = createLocalStorageGuestHandoffRejectionStorage();
      harness.teacher.importExamWorkspaceGuestDraft.mockRejectedValue(guestHandoffApiError(503));
      const scope = effectScope();
      const controller = scope.run(() =>
        useExamWorkspaceGuestHandoffController({ ...harness, rejections }),
      )!;
      try {
        await controller.start();
        expect(harness.teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);
        const stored = await harness.storage.load();
        const load = deferred<StoredGuestDraft | null>();
        let loads = 0;
        harness.storage.load = async () => {
          loads += 1;
          return load.promise;
        };
        await vi.advanceTimersByTimeAsync(5_000);
        expect(loads).toBe(1);
        expect(harness.teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);
        scope.stop();
        load.resolve(stored);
        await vi.advanceTimersByTimeAsync(0);
        expect(harness.teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);
        expect(rejections.read()).toBeNull();
      } finally {
        scope.stop();
      }
    } finally {
      vi.useRealTimers();
    }
  });

  it("c) removing stale A keeps B's draft and record; a new start makes no POST", async () => {
    const harness = await seedGuestHandoffHarness();
    const rejections = createLocalStorageGuestHandoffRejectionStorage();
    harness.teacher.importExamWorkspaceGuestDraft.mockRejectedValue(guestHandoffApiError(422));
    const scope = effectScope();
    const controller = scope.run(() =>
      useExamWorkspaceGuestHandoffController({ ...harness, rejections }),
    )!;
    try {
      await controller.start();
      const b = await replaceSlotWithB(harness.storage);
      await runGuestHandoff({
        lock: harness.lock,
        owner: guestHandoffOwnerStub(),
        rejections,
        storage: harness.storage,
        teacher: harness.teacher,
      }, liveAttempt());
      expect(rejections.read()).toEqual({ cursor: b.cursor, reason: "permanent" });
      await controller.remove();
      expect((await harness.storage.load())?.draft.cursor).toBe(b.cursor);
      expect(rejections.read()).toEqual({ cursor: b.cursor, reason: "permanent" });
      const callsBefore = harness.teacher.importExamWorkspaceGuestDraft.mock.calls.length;
      const fresh = effectScope();
      try {
        const next = fresh.run(() =>
          useExamWorkspaceGuestHandoffController({ ...harness, rejections }),
        )!;
        await next.start();
        expect(next.notice.value).toEqual({ reason: "permanent", busy: false });
      } finally {
        fresh.stop();
      }
      expect(harness.teacher.importExamWorkspaceGuestDraft.mock.calls.length).toBe(callsBefore);
      expect(harness.teacher.importExamWorkspaceGuestDraft.mock.calls.map((call) => call[0])).toEqual([
        harness.draft.cursor,
        b.cursor,
      ]);
    } finally {
      scope.stop();
    }
  });

  it("d) retrying stale vault-full A after B was rejected posts nothing and turns permanent", async () => {
    const harness = await seedGuestHandoffHarness();
    const rejections = createLocalStorageGuestHandoffRejectionStorage();
    harness.teacher.importExamWorkspaceGuestDraft
      .mockRejectedValueOnce(guestHandoffApiError(422, "VALIDATION_ERROR", { reason: "vault_full" }))
      .mockRejectedValue(guestHandoffApiError(422));
    const scope = effectScope();
    const controller = scope.run(() =>
      useExamWorkspaceGuestHandoffController({ ...harness, rejections }),
    )!;
    try {
      await controller.start();
      expect(controller.notice.value).toEqual({ reason: "vault_full", busy: false });
      const b = await replaceSlotWithB(harness.storage);
      await runGuestHandoff({
        lock: harness.lock,
        owner: guestHandoffOwnerStub(),
        rejections,
        storage: harness.storage,
        teacher: harness.teacher,
      }, liveAttempt());
      expect(rejections.read()).toEqual({ cursor: b.cursor, reason: "permanent" });
      await controller.retry();
      expect(harness.teacher.importExamWorkspaceGuestDraft.mock.calls.map((call) => call[0])).toEqual([
        harness.draft.cursor,
        b.cursor,
      ]);
      expect(controller.notice.value).toEqual({ reason: "permanent", busy: false });
    } finally {
      scope.stop();
    }
  });

  it("e) retrying stale vault-full A after the slot was emptied closes the notice", async () => {
    const harness = await seedGuestHandoffHarness();
    const rejections = createLocalStorageGuestHandoffRejectionStorage();
    harness.teacher.importExamWorkspaceGuestDraft.mockRejectedValue(
      guestHandoffApiError(422, "VALIDATION_ERROR", { reason: "vault_full" }),
    );
    const scope = effectScope();
    const controller = scope.run(() =>
      useExamWorkspaceGuestHandoffController({ ...harness, rejections }),
    )!;
    try {
      await controller.start();
      expect(controller.notice.value).toEqual({ reason: "vault_full", busy: false });
      expect(await harness.storage.clearIf(harness.draft.cursor)).toBe(true);
      await controller.retry();
      expect(harness.teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);
      expect(controller.notice.value).toBeNull();
    } finally {
      scope.stop();
    }
  });

  it("f) two controllers over one shared lock POST once and both end permanent", async () => {
    const harness = await seedGuestHandoffHarness();
    const lock = createInMemoryGuestHandoffLock();
    const one = createLocalStorageGuestHandoffRejectionStorage();
    const two = createLocalStorageGuestHandoffRejectionStorage();
    const reply = deferred<never>();
    harness.teacher.importExamWorkspaceGuestDraft.mockReturnValue(reply.promise);
    const scopeOne = effectScope();
    const scopeTwo = effectScope();
    try {
      const first = scopeOne.run(() =>
        useExamWorkspaceGuestHandoffController({
          lock,
          rejections: one,
          storage: harness.storage,
          teacher: harness.teacher,
        }),
      )!;
      const second = scopeTwo.run(() =>
        useExamWorkspaceGuestHandoffController({
          lock,
          rejections: two,
          storage: harness.storage,
          teacher: harness.teacher,
        }),
      )!;
      const pendingOne = first.start();
      const pendingTwo = second.start();
      await vi.waitFor(() => expect(harness.teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1));
      reply.reject(guestHandoffApiError(422));
      await expect(pendingOne).resolves.toBeNull();
      await expect(pendingTwo).resolves.toBeNull();
      expect(harness.teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);
      expect(first.notice.value).toEqual({ reason: "permanent", busy: false });
      expect(second.notice.value).toEqual({ reason: "permanent", busy: false });
    } finally {
      scopeOne.stop();
      scopeTwo.stop();
    }
  });

  it("g) remove() with a retired owner clears nothing", async () => {
    const harness = await seedGuestHandoffHarness();
    const rejections = createLocalStorageGuestHandoffRejectionStorage();
    harness.teacher.importExamWorkspaceGuestDraft.mockRejectedValue(guestHandoffApiError(422));
    const scope = effectScope();
    const controller = scope.run(() =>
      useExamWorkspaceGuestHandoffController({ ...harness, rejections }),
    )!;
    try {
      await controller.start();
      expect(controller.notice.value).toEqual({ reason: "permanent", busy: false });
      const gate = deferred<void>();
      const holding = harness.lock.run(() => gate.promise, new AbortController().signal);
      const removing = controller.remove();
      scope.stop();
      gate.resolve(undefined);
      await holding;
      await removing;
      expect((await harness.storage.load())?.draft.cursor).toBe(harness.draft.cursor);
      expect(rejections.read()).toEqual({ cursor: harness.draft.cursor, reason: "permanent" });
    } finally {
      scope.stop();
    }
  });

  it.each([["missing"], ["denied"]])(
    "h) P10 port: %s Web Locks settle start with the permanent notice and remove clears without the lock",
    async (kind) => {
      const harness = await seedGuestHandoffHarness();
      const restore = setNavigatorLocks(
        kind === "missing"
          ? undefined
          : {
              request: async (): Promise<never> => {
                throw new DOMException("Storage access is denied.", "SecurityError");
              },
            },
      );
      const scope = effectScope();
      try {
        const controller = scope.run(() =>
          useExamWorkspaceGuestHandoffController({
            ...harness,
            lock: createWebGuestHandoffLock(),
          }),
        )!;
        await expect(controller.start()).resolves.toBeNull();
        expect(controller.notice.value).toEqual({ reason: "permanent", busy: false });
        expect(harness.teacher.importExamWorkspaceGuestDraft).not.toHaveBeenCalled();
        expect(harness.rejections.read()).toBeNull();
        expect((await harness.storage.load())?.draft.cursor).toBe(harness.draft.cursor);
        await controller.remove();
        await expect(harness.storage.load()).resolves.toBeNull();
        expect(controller.notice.value).toBeNull();
      } finally {
        scope.stop();
        restore();
      }
    },
  );

  it("i) P12 port: a held POST aborted by pagehide settles, and a later start proceeds and POSTs", async () => {
    const harness = await seedGuestHandoffHarness();
    const rejections = createLocalStorageGuestHandoffRejectionStorage();
    harness.teacher.importExamWorkspaceGuestDraft.mockImplementationOnce(
      (_key, _document, _assets, _notes, binding) =>
        new Promise<never>((_resolve, reject) => {
          binding.signal?.addEventListener(
            "abort",
            () => reject(new DOMException("Aborted.", "AbortError")),
            { once: true },
          );
        }),
    );
    harness.teacher.importExamWorkspaceGuestDraft.mockRejectedValue(guestHandoffApiError(422));
    const scope = effectScope();
    const first = scope.run(() =>
      useExamWorkspaceGuestHandoffController({ ...harness, rejections }),
    )!;
    const firstPending = first.start();
    await vi.waitFor(() =>
      expect(harness.teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1),
    );
    window.dispatchEvent(new Event("pagehide"));
    await expect(firstPending).resolves.toBeNull();
    expect(rejections.read()).toBeNull();
    expect((await harness.storage.load())?.draft.cursor).toBe(harness.draft.cursor);
    scope.stop();
    const later = effectScope();
    try {
      const second = later.run(() =>
        useExamWorkspaceGuestHandoffController({ ...harness, rejections }),
      )!;
      await expect(second.start()).resolves.toBeNull();
      expect(second.notice.value).toEqual({ reason: "permanent", busy: false });
    } finally {
      later.stop();
    }
    expect(harness.teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(2);
  });

  it("j) P12 port: a held POST aborted by disposal settles, and a later start proceeds and POSTs", async () => {
    const harness = await seedGuestHandoffHarness();
    const rejections = createLocalStorageGuestHandoffRejectionStorage();
    harness.teacher.importExamWorkspaceGuestDraft.mockImplementationOnce(
      (_key, _document, _assets, _notes, binding) =>
        new Promise<never>((_resolve, reject) => {
          binding.signal?.addEventListener(
            "abort",
            () => reject(new DOMException("Aborted.", "AbortError")),
            { once: true },
          );
        }),
    );
    harness.teacher.importExamWorkspaceGuestDraft.mockRejectedValue(guestHandoffApiError(422));
    const scope = effectScope();
    const first = scope.run(() =>
      useExamWorkspaceGuestHandoffController({ ...harness, rejections }),
    )!;
    const firstPending = first.start();
    await vi.waitFor(() =>
      expect(harness.teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1),
    );
    scope.stop();
    await expect(firstPending).resolves.toBeNull();
    expect(rejections.read()).toBeNull();
    expect((await harness.storage.load())?.draft.cursor).toBe(harness.draft.cursor);
    const later = effectScope();
    try {
      const second = later.run(() =>
        useExamWorkspaceGuestHandoffController({ ...harness, rejections }),
      )!;
      await expect(second.start()).resolves.toBeNull();
      expect(second.notice.value).toEqual({ reason: "permanent", busy: false });
    } finally {
      later.stop();
    }
    expect(harness.teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(2);
  });

  it("k) after pagehide aborts an attempt, a vault-full notice retry still POSTs", async () => {
    const harness = await seedGuestHandoffHarness();
    const rejections = createLocalStorageGuestHandoffRejectionStorage();
    harness.teacher.importExamWorkspaceGuestDraft.mockRejectedValue(
      guestHandoffApiError(422, "VALIDATION_ERROR", { reason: "vault_full" }),
    );
    const scope = effectScope();
    try {
      const controller = scope.run(() =>
        useExamWorkspaceGuestHandoffController({ ...harness, rejections }),
      )!;
      await controller.start();
      expect(controller.notice.value).toEqual({ reason: "vault_full", busy: false });
      window.dispatchEvent(new Event("pagehide"));
      await controller.retry();
      expect(harness.teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(2);
      expect(controller.notice.value).toEqual({ reason: "vault_full", busy: false });
    } finally {
      scope.stop();
    }
  });
});
