/**
 * Guest handoff controller: first attempt, backoff, toasts and retry lifetime
 * (TASK-SKRIPT-41-02-05, U2b; split by responsibility in U13b).
 *
 * Expected behavior:
 *   The first attempt gates the view. Transient failures show one toast and
 *   retry in the background with doubling delay, at most three times; the last
 *   failure shows one more toast. Rejections leave a notice with download,
 *   remove and (vault-full) manual retry actions. Disposing the scope stops
 *   timers and silences late completions.
 */

import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  guestHandoffApiError as apiError,
  seedGuestHandoffHarness,
} from "./useExamWorkspaceGuestHandoff.specSupport";
import {
  GUEST_HANDOFF_LATE_SUCCESS_COPY,
  GUEST_HANDOFF_MANUAL_RETRY_FAILED_COPY,
  GUEST_HANDOFF_RETRIES_EXHAUSTED_COPY,
  GUEST_HANDOFF_TRANSIENT_COPY,
} from "./useExamWorkspaceGuestHandoffController";
import type { ImportResult } from "./useExamWorkspaceGuestHandoffController.specSupport";
import {
  seatOlderFormat,
  startController,
  successResult,
  toastMessages,
  toastSpies,
} from "./useExamWorkspaceGuestHandoffController.specSupport";

beforeEach(() => {
  setActivePinia(createPinia());
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("useExamWorkspaceGuestHandoffController handoff and retry lifetime", () => {
  it("1) transient at start retries three times with doubling delay, then stops", async () => {
    const { lock, rejections, storage, teacher } = await seedGuestHandoffHarness();
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(apiError(503, "SERVICE_UNAVAILABLE"));
    const { controller, scope } = startController({ lock, rejections, storage, teacher });
    const spies = toastSpies();
    try {
      await expect(controller.start()).resolves.toBeNull();
      expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);
      expect(toastMessages(spies.warning)).toEqual([
        GUEST_HANDOFF_TRANSIENT_COPY,
      ]);

      await vi.advanceTimersByTimeAsync(4_999);
      expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);
      await vi.advanceTimersByTimeAsync(1);
      expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(2);
      expect(toastMessages(spies.warning)).toEqual([GUEST_HANDOFF_TRANSIENT_COPY]);

      await vi.advanceTimersByTimeAsync(10_000);
      expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(3);
      expect(toastMessages(spies.warning)).toEqual([GUEST_HANDOFF_TRANSIENT_COPY]);

      await vi.advanceTimersByTimeAsync(20_000);
      expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(4);
      expect(toastMessages(spies.warning)).toEqual([
        GUEST_HANDOFF_TRANSIENT_COPY,
        GUEST_HANDOFF_RETRIES_EXHAUSTED_COPY,
      ]);

      await vi.advanceTimersByTimeAsync(3_600_000);
      expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(4);
    } finally {
      scope.stop();
    }
  });

  it("2) a late success on retry #2 toasts, clears the draft and stops", async () => {
    const { draft, lock, rejections, storage, teacher } = await seedGuestHandoffHarness();
    teacher.importExamWorkspaceGuestDraft
      .mockRejectedValueOnce(apiError(503, "SERVICE_UNAVAILABLE"))
      .mockRejectedValueOnce(apiError(503, "SERVICE_UNAVAILABLE"))
      .mockResolvedValue(successResult(draft));
    const { controller, scope } = startController({ lock, rejections, storage, teacher });
    const spies = toastSpies();
    try {
      await expect(controller.start()).resolves.toBeNull();
      await vi.advanceTimersByTimeAsync(5_000);
      expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(2);
      expect(toastMessages(spies.success)).toEqual([]);

      await vi.advanceTimersByTimeAsync(10_000);
      expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(3);
      expect(toastMessages(spies.success)).toEqual([GUEST_HANDOFF_LATE_SUCCESS_COPY]);
      await expect(storage.load()).resolves.toBeNull();

      await vi.advanceTimersByTimeAsync(3_600_000);
      expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(3);
    } finally {
      scope.stop();
    }
  });

  it.each([
    ["429", apiError(429, "RATE_LIMITED")],
    ["fetch TypeError", new TypeError("Failed to fetch")],
  ])("4) %s follows the transient path with a retry at 5s", async (_label, error) => {
    const { lock, rejections, storage, teacher } = await seedGuestHandoffHarness();
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(error);
    const { controller, scope } = startController({ lock, rejections, storage, teacher });
    const spies = toastSpies();
    try {
      await expect(controller.start()).resolves.toBeNull();
      expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);
      expect(toastMessages(spies.warning)).toEqual([GUEST_HANDOFF_TRANSIENT_COPY]);
      expect(controller.notice.value).toBeNull();

      await vi.advanceTimersByTimeAsync(5_000);
      expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(2);
    } finally {
      scope.stop();
    }
  });

  it("5) 401 shows nothing and never retries", async () => {
    const { lock, rejections, storage, teacher } = await seedGuestHandoffHarness();
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(apiError(401, "UNAUTHORIZED"));
    const { controller, scope } = startController({ lock, rejections, storage, teacher });
    const spies = toastSpies();
    try {
      await expect(controller.start()).resolves.toBeNull();
      expect(controller.notice.value).toBeNull();
      expect(spies.warning).not.toHaveBeenCalled();
      expect(spies.success).not.toHaveBeenCalled();
      expect(spies.failure).not.toHaveBeenCalled();

      await vi.advanceTimersByTimeAsync(3_600_000);
      expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);
    } finally {
      scope.stop();
    }
  });

  it("6a) vault_full retry posts again ignoring the record; success closes the notice", async () => {
    const { draft, lock, rejections, storage, teacher } = await seedGuestHandoffHarness();
    teacher.importExamWorkspaceGuestDraft
      .mockRejectedValueOnce(apiError(422, "VALIDATION_ERROR", { reason: "vault_full" }))
      .mockResolvedValue(successResult(draft));
    const { controller, scope } = startController({ lock, rejections, storage, teacher });
    const spies = toastSpies();
    try {
      await expect(controller.start()).resolves.toBeNull();
      expect(controller.notice.value).toEqual({ reason: "vault_full", busy: false });
      expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);

      await controller.retry();
      expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(2);
      expect(controller.notice.value).toBeNull();
      expect(toastMessages(spies.success)).toEqual([GUEST_HANDOFF_LATE_SUCCESS_COPY]);
      await expect(storage.load()).resolves.toBeNull();
    } finally {
      scope.stop();
    }
  });

  it("6b) vault_full retry can turn unreadable with a new draft", async () => {
    const { lock, rejections, storage, teacher } = await seedGuestHandoffHarness();
    teacher.importExamWorkspaceGuestDraft
      .mockRejectedValueOnce(apiError(422, "VALIDATION_ERROR", { reason: "vault_full" }))
      .mockRejectedValueOnce(apiError(422, "DOCUMENT_SCHEMA_OUTDATED"));
    const { controller, scope } = startController({ lock, rejections, storage, teacher });
    const spies = toastSpies();
    try {
      await expect(controller.start()).resolves.toBeNull();
      // The retry meets a draft the browser itself cannot read: the server
      // only refuses an outdated format for such a draft.
      await seatOlderFormat(storage);
      await controller.retry();
      expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(2);
      expect(controller.notice.value).toEqual({ reason: "unreadable", busy: false });
      expect(spies.warning).not.toHaveBeenCalled();
      expect(spies.success).not.toHaveBeenCalled();
      expect(spies.failure).not.toHaveBeenCalled();
    } finally {
      scope.stop();
    }
  });

  it("6c) vault_full retry failing transiently keeps the notice, toasts failure, no schedule", async () => {
    const { lock, rejections, storage, teacher } = await seedGuestHandoffHarness();
    teacher.importExamWorkspaceGuestDraft
      .mockRejectedValueOnce(apiError(422, "VALIDATION_ERROR", { reason: "vault_full" }))
      .mockRejectedValue(apiError(503, "SERVICE_UNAVAILABLE"));
    const { controller, scope } = startController({ lock, rejections, storage, teacher });
    const spies = toastSpies();
    try {
      await expect(controller.start()).resolves.toBeNull();
      await controller.retry();
      expect(controller.notice.value).toEqual({ reason: "vault_full", busy: false });
      expect(toastMessages(spies.failure)).toEqual([GUEST_HANDOFF_MANUAL_RETRY_FAILED_COPY]);

      await vi.advanceTimersByTimeAsync(3_600_000);
      expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(2);
    } finally {
      scope.stop();
    }
  });

  it("9a) stopping the scope while a retry is pending makes no second POST", async () => {
    const { lock, rejections, storage, teacher } = await seedGuestHandoffHarness();
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(apiError(503, "SERVICE_UNAVAILABLE"));
    const { controller, scope } = startController({ lock, rejections, storage, teacher });
    const spies = toastSpies();
    await expect(controller.start()).resolves.toBeNull();
    scope.stop();

    await vi.advanceTimersByTimeAsync(3_600_000);
    expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);
    expect(toastMessages(spies.warning)).toEqual([GUEST_HANDOFF_TRANSIENT_COPY]);
  });

  it("9b) an attempt resolving after dispose shows no toast", async () => {
    const { draft, lock, rejections, storage, teacher } = await seedGuestHandoffHarness();
    const pendingPost: { resolve: ((value: ImportResult) => void) | null } = { resolve: null };
    teacher.importExamWorkspaceGuestDraft.mockImplementationOnce(
      () =>
        new Promise<ImportResult>((resolve) => {
          pendingPost.resolve = resolve;
        }),
    );
    const { controller, scope } = startController({ lock, rejections, storage, teacher });
    const spies = toastSpies();
    const pending = controller.start();
    // Let the first attempt reach the teacher POST so it is in flight.
    await vi.advanceTimersByTimeAsync(0);
    expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);
    scope.stop();
    pendingPost.resolve?.(successResult(draft));
    await expect(pending).resolves.toBeNull();
    expect(spies.warning).not.toHaveBeenCalled();
    expect(spies.success).not.toHaveBeenCalled();
    expect(spies.failure).not.toHaveBeenCalled();
    expect(controller.notice.value).toBeNull();
  });

  it("10) retry while busy is ignored to one POST", async () => {
    const { draft, lock, rejections, storage, teacher } = await seedGuestHandoffHarness();
    teacher.importExamWorkspaceGuestDraft
      .mockRejectedValueOnce(apiError(422, "VALIDATION_ERROR", { reason: "vault_full" }))
      .mockResolvedValue(successResult(draft));
    const { controller, scope } = startController({ lock, rejections, storage, teacher });
    try {
      await expect(controller.start()).resolves.toBeNull();
      const first = controller.retry();
      const second = controller.retry();
      await Promise.all([first, second]);
      expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(2);
      expect(controller.notice.value).toBeNull();
    } finally {
      scope.stop();
    }
  });
});
