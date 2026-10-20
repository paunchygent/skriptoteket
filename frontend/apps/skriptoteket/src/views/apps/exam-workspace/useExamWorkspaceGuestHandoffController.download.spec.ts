/**
 * Guest handoff controller: the download action on the rejection notice
 * (TASK-SKRIPT-41-02-05, U2b; split by responsibility in U13b).
 *
 * Expected behavior:
 *   Download saves the stored draft record and its stored picture bytes as
 *   one zip. A stored draft with another cursor, nothing stored, or any
 *   failure downloads nothing and shows the download failure toast. The
 *   notice stays busy while the zip is built.
 */

import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { unzipSync } from "fflate";

import {
  createInMemoryExamWorkspaceGuestDraftStorage,
  type StoredGuestDraft,
} from "./examWorkspaceGuestDraftStorage";
import { createInMemoryGuestHandoffRejectionStorage } from "./examWorkspaceGuestHandoffRejection";
import type { ExamWorkspaceGuestDraft } from "./examWorkspaceGuestDraft";
import {
  editedGuestDraft,
  guestHandoffApiError as apiError,
  seedGuestHandoffHarness,
} from "./useExamWorkspaceGuestHandoff.specSupport";
import { EXAM_WORKSPACE_FILE_NOTICE_DOWNLOAD_FAILURE_COPY } from "./examWorkspaceFileNoticeCopy";
import {
  blobBytes,
  equipStoredPictureBytes,
  seatOlderFormat,
  startController,
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

describe("useExamWorkspaceGuestHandoffController download", () => {
  it("7) download saves one zip with the stored record and its picture bytes", async () => {
    const { draft, lock, rejections, storage, teacher } = await seedGuestHandoffHarness();
    await seatOlderFormat(storage);
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(apiError(422, "DOCUMENT_SCHEMA_OUTDATED"));
    const download = vi.fn<(blob: Blob, filename: string) => void>();
    const { controller, scope } = startController({ lock, rejections, storage, teacher }, download);
    const spies = toastSpies();
    try {
      await expect(controller.start()).resolves.toBeNull();
      await equipStoredPictureBytes(storage);
      // FileReader never fires under fake timers; no retry timer is pending here.
      vi.useRealTimers();
      await controller.download();
      expect(download).toHaveBeenCalledTimes(1);
      const [blob, filename] = download.mock.calls[0];
      expect(filename).toBe(`${draft.saved_document.title}.zip`);
      expect(blob.type).toBe("application/zip");
      expect(controller.notice.value).toEqual({ reason: "unreadable", busy: false });
      expect(spies.failure).not.toHaveBeenCalled();
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
      const assetA = unzipped["assets/asset_a"];
      const assetB = unzipped["assets/asset_b"];
      if (draftJson === undefined || assetA === undefined || assetB === undefined) {
        throw new Error("expected draft.json and both picture entries in the zip");
      }
      expect(JSON.parse(new TextDecoder().decode(draftJson))).toEqual(stored.draft);
      expect(new TextDecoder().decode(assetA)).toBe("a");
      expect(new TextDecoder().decode(assetB)).toBe("b");
    } finally {
      scope.stop();
    }
  });

  it("7b) download falls back to Prov.zip when the title is blank", async () => {
    const blankStorage = createInMemoryExamWorkspaceGuestDraftStorage();
    const blankRejections = createInMemoryGuestHandoffRejectionStorage();
    const { draft: base } = editedGuestDraft();
    const blank: ExamWorkspaceGuestDraft = {
      ...base,
      saved_document: { ...base.saved_document, title: "   " },
    };
    expect(await blankStorage.replaceIf(null, { assets: {}, draft: blank })).toBe(true);
    const { lock, teacher } = await seedGuestHandoffHarness();
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(apiError(422, "DOCUMENT_SCHEMA_OUTDATED"));
    const download = vi.fn<(blob: Blob, filename: string) => void>();
    const { controller, scope } = startController(
      { lock, rejections: blankRejections, storage: blankStorage, teacher },
      download,
    );
    try {
      await expect(controller.start()).resolves.toBeNull();
      expect(controller.notice.value).toEqual({ reason: "permanent", busy: false });
      // FileReader never fires under fake timers; no retry timer is pending here.
      vi.useRealTimers();
      await controller.download();
      expect(download).toHaveBeenCalledTimes(1);
      const [blob, filename] = download.mock.calls[0];
      expect(filename).toBe("Prov.zip");
      expect(blob.type).toBe("application/zip");
      const unzipped = unzipSync(await blobBytes(blob));
      const draftJson = unzipped["draft.json"];
      if (draftJson === undefined) {
        throw new Error("expected draft.json in the zip");
      }
      expect(JSON.parse(new TextDecoder().decode(draftJson))).toEqual(blank);
    } finally {
      scope.stop();
    }
  });

  it("7c) download with a newer stored cursor downloads nothing and shows S6", async () => {
    const { draft, lock, rejections, storage, teacher } = await seedGuestHandoffHarness();
    await seatOlderFormat(storage);
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(apiError(422, "DOCUMENT_SCHEMA_OUTDATED"));
    const download = vi.fn<(blob: Blob, filename: string) => void>();
    const { controller, scope } = startController({ lock, rejections, storage, teacher }, download);
    const spies = toastSpies();
    try {
      await expect(controller.start()).resolves.toBeNull();
      const newer = { ...draft, cursor: "cursor-newer" };
      expect(await storage.replaceIf(draft.cursor, { assets: {}, draft: newer })).toBe(true);
      vi.useRealTimers();
      await controller.download();
      expect(download).not.toHaveBeenCalled();
      expect(toastMessages(spies.failure)).toEqual([
        EXAM_WORKSPACE_FILE_NOTICE_DOWNLOAD_FAILURE_COPY,
      ]);
      expect(controller.notice.value).toEqual({ reason: "unreadable", busy: false });
    } finally {
      scope.stop();
    }
  });

  it("7d) download with nothing stored downloads nothing and shows S6", async () => {
    const { draft, lock, rejections, storage, teacher } = await seedGuestHandoffHarness();
    await seatOlderFormat(storage);
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(apiError(422, "DOCUMENT_SCHEMA_OUTDATED"));
    const download = vi.fn<(blob: Blob, filename: string) => void>();
    const { controller, scope } = startController({ lock, rejections, storage, teacher }, download);
    const spies = toastSpies();
    try {
      await expect(controller.start()).resolves.toBeNull();
      expect(await storage.clearIf(draft.cursor)).toBe(true);
      vi.useRealTimers();
      await controller.download();
      expect(download).not.toHaveBeenCalled();
      expect(toastMessages(spies.failure)).toEqual([
        EXAM_WORKSPACE_FILE_NOTICE_DOWNLOAD_FAILURE_COPY,
      ]);
      expect(controller.notice.value).toEqual({ reason: "unreadable", busy: false });
    } finally {
      scope.stop();
    }
  });

  it("7e) download with an unreadable storage downloads nothing and shows S6", async () => {
    const { lock, rejections, storage, teacher } = await seedGuestHandoffHarness();
    await seatOlderFormat(storage);
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(apiError(422, "DOCUMENT_SCHEMA_OUTDATED"));
    const deps = { lock, rejections, storage, teacher };
    const download = vi.fn<(blob: Blob, filename: string) => void>();
    const { controller, scope } = startController(deps, download);
    const spies = toastSpies();
    try {
      await expect(controller.start()).resolves.toBeNull();
      deps.storage = {
        ...storage,
        load: async (): Promise<StoredGuestDraft | null> => {
          throw new Error("lagringen är blockerad");
        },
      };
      vi.useRealTimers();
      await controller.download();
      expect(download).not.toHaveBeenCalled();
      expect(toastMessages(spies.failure)).toEqual([
        EXAM_WORKSPACE_FILE_NOTICE_DOWNLOAD_FAILURE_COPY,
      ]);
      expect(controller.notice.value).toEqual({ reason: "unreadable", busy: false });
    } finally {
      scope.stop();
    }
  });

  it("7f) download marks the notice busy while storage reads", async () => {
    const { lock, rejections, storage, teacher } = await seedGuestHandoffHarness();
    await seatOlderFormat(storage);
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(apiError(422, "DOCUMENT_SCHEMA_OUTDATED"));
    const download = vi.fn<(blob: Blob, filename: string) => void>();
    const deps = { lock, rejections, storage, teacher };
    const { controller, scope } = startController(deps, download);
    try {
      await expect(controller.start()).resolves.toBeNull();
      await equipStoredPictureBytes(storage);
      let release!: (stored: StoredGuestDraft | null) => void;
      deps.storage = {
        ...storage,
        load: () =>
          new Promise<StoredGuestDraft | null>((resolve) => {
            release = resolve;
          }),
      };
      const pending = controller.download();
      expect(controller.notice.value).toEqual({ reason: "unreadable", busy: true });
      expect(download).not.toHaveBeenCalled();
      vi.useRealTimers();
      release(await storage.load());
      await pending;
      expect(download).toHaveBeenCalledTimes(1);
      expect(controller.notice.value).toEqual({ reason: "unreadable", busy: false });
    } finally {
      scope.stop();
    }
  });
});
