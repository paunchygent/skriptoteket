/**
 * Guest handoff controller: an outdated-format refusal shows the unreadable
 * notice (U14, repairs F1; split setup shared in U13b).
 *
 * Expected behavior:
 *   A signed-in handoff of a draft the browser itself cannot read leaves the
 *   `unreadable` notice with the same download and remove as the permanent
 *   one; every other refusal on a readable draft keeps its current reason. A
 *   recorded permanent rejection for a draft the browser itself cannot read
 *   shows the unreadable notice on remount without posting again.
 */

import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { unzipSync } from "fflate";

import { useToastStore } from "../../../stores/toast";
import {
  guestHandoffApiError as apiError,
  seedGuestHandoffHarness,
} from "./useExamWorkspaceGuestHandoff.specSupport";
import { EXAM_WORKSPACE_FILE_NOTICE_GUEST_UNREADABLE_COPY } from "./examWorkspaceFileNoticeCopy";
import {
  blobBytes,
  equipStoredPictureBytes,
  seatOlderFormat,
  startController,
} from "./useExamWorkspaceGuestHandoffController.specSupport";

function toastMessages(): string[] {
  return useToastStore().toasts.map((toast) => toast.message);
}

beforeEach(() => {
  setActivePinia(createPinia());
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("useExamWorkspaceGuestHandoffController unreadable drafts", () => {
  it("another permanent refusal on a readable draft keeps the permanent notice", async () => {
    const { lock, rejections, storage, teacher } = await seedGuestHandoffHarness();
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(apiError(422, "VALIDATION_ERROR"));
    const { controller, scope } = startController({ lock, rejections, storage, teacher });
    try {
      await expect(controller.start()).resolves.toBeNull();
      expect(controller.notice.value).toEqual({ reason: "permanent", busy: false });
      expect(rejections.read()).toEqual({
        cursor: (await storage.load())?.draft.cursor,
        reason: "permanent",
      });
    } finally {
      scope.stop();
    }
  });

  it("a remount after an outdated refusal posts nothing and keeps the unreadable notice", async () => {
    const { lock, rejections, storage, teacher } = await seedGuestHandoffHarness();
    await seatOlderFormat(storage);
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(apiError(422, "DOCUMENT_SCHEMA_OUTDATED"));
    const first = startController({ lock, rejections, storage, teacher });
    try {
      await expect(first.controller.start()).resolves.toBeNull();
      expect(first.controller.notice.value).toEqual({ reason: "unreadable", busy: false });
    } finally {
      first.scope.stop();
    }

    const second = startController({ lock, rejections, storage, teacher });
    try {
      await expect(second.controller.start()).resolves.toBeNull();
      expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);
      expect(second.controller.notice.value).toEqual({ reason: "unreadable", busy: false });
    } finally {
      second.scope.stop();
    }
  });

  it("download on the unreadable notice saves one zip with the stored record and its pictures", async () => {
    const { draft, lock, rejections, storage, teacher } = await seedGuestHandoffHarness();
    await seatOlderFormat(storage);
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(apiError(422, "DOCUMENT_SCHEMA_OUTDATED"));
    const download = vi.fn<(blob: Blob, filename: string) => void>();
    const { controller, scope } = startController({ lock, rejections, storage, teacher }, download);
    try {
      await expect(controller.start()).resolves.toBeNull();
      expect(controller.notice.value).toEqual({ reason: "unreadable", busy: false });
      await equipStoredPictureBytes(storage);
      vi.useRealTimers();
      await controller.download();
      expect(download).toHaveBeenCalledTimes(1);
      const [blob, filename] = download.mock.calls[0];
      expect(filename).toBe(`${draft.saved_document.title}.zip`);
      expect(blob.type).toBe("application/zip");
      expect(controller.notice.value).toEqual({ reason: "unreadable", busy: false });
      expect(toastMessages()).toEqual([]);
      const stored = await storage.load();
      if (stored === null) {
        throw new Error("expected the stored draft to survive the download");
      }
      const unzipped = unzipSync(await blobBytes(blob));
      expect(Object.keys(unzipped).sort()).toEqual([
        "assets/asset_a",
        "assets/asset_b",
        "draft.json",
      ]);
      const draftJson = unzipped["draft.json"];
      if (draftJson === undefined) {
        throw new Error("expected draft.json in the zip");
      }
      expect(JSON.parse(new TextDecoder().decode(draftJson))).toEqual(stored.draft);
    } finally {
      scope.stop();
    }
  });

  it("remove on the unreadable notice clears the draft, the record and the notice", async () => {
    const { lock, rejections, storage, teacher } = await seedGuestHandoffHarness();
    await seatOlderFormat(storage);
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(apiError(422, "DOCUMENT_SCHEMA_OUTDATED"));
    const { controller, scope } = startController({ lock, rejections, storage, teacher });
    try {
      await expect(controller.start()).resolves.toBeNull();
      expect(controller.notice.value).toEqual({ reason: "unreadable", busy: false });
      await controller.remove();
      await expect(storage.load()).resolves.toBeNull();
      expect(rejections.read()).toBeNull();
      expect(controller.notice.value).toBeNull();
      expect(toastMessages()).toEqual([]);
    } finally {
      scope.stop();
    }
  });

  it("pins the unreadable sentence", () => {
    expect(EXAM_WORKSPACE_FILE_NOTICE_GUEST_UNREADABLE_COPY).toBe(
      "Provet är sparat i ett äldre format och kan inte öppnas. Ladda ner det som en fil eller ta bort det från webbläsaren.",
    );
  });

});
