/**
 * Guest handoff controller: the remove action on the rejection notice
 * (TASK-SKRIPT-41-02-05, U2b; split by responsibility in U13b).
 *
 * Expected behavior:
 *   Remove clears the held draft from storage and clears its rejection
 *   record, leaving no notice. A failing clear keeps the notice and the
 *   record while the stored draft survives.
 */

import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  guestHandoffApiError as apiError,
  seedGuestHandoffHarness,
} from "./useExamWorkspaceGuestHandoff.specSupport";
import {
  seatOlderFormat,
  startController,
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

describe("useExamWorkspaceGuestHandoffController removal", () => {
  it("8a) remove clears the draft, the record and the notice", async () => {
    const { lock, rejections, storage, teacher } = await seedGuestHandoffHarness();
    await seatOlderFormat(storage);
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(apiError(422, "DOCUMENT_SCHEMA_OUTDATED"));
    const { controller, scope } = startController({ lock, rejections, storage, teacher });
    const spies = toastSpies();
    try {
      await expect(controller.start()).resolves.toBeNull();
      await controller.remove();
      await expect(storage.load()).resolves.toBeNull();
      expect(rejections.read()).toBeNull();
      expect(controller.notice.value).toBeNull();
      expect(spies.warning).not.toHaveBeenCalled();
      expect(spies.success).not.toHaveBeenCalled();
      expect(spies.failure).not.toHaveBeenCalled();
    } finally {
      scope.stop();
    }
  });

  it("8b) remove keeps the notice and the record when clearIf throws", async () => {
    const { draft, lock, rejections, storage, teacher } = await seedGuestHandoffHarness();
    await seatOlderFormat(storage);
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(apiError(422, "DOCUMENT_SCHEMA_OUTDATED"));
    const failingStorage = {
      ...storage,
      clearIf: vi.fn<() => Promise<boolean>>().mockRejectedValue(new Error("locked")),
    };
    const { controller, scope } = startController({
      lock,
      rejections,
      storage: failingStorage,
      teacher,
    });
    try {
      await expect(controller.start()).resolves.toBeNull();
      await controller.remove();
      expect(controller.notice.value).toEqual({ reason: "unreadable", busy: false });
      expect(rejections.read()).toEqual({ cursor: draft.cursor, reason: "permanent" });
      await expect(storage.load()).resolves.not.toBeNull();
    } finally {
      scope.stop();
    }
  });
});
