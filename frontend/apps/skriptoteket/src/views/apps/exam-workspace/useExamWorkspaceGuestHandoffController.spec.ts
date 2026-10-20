/**
 * Guest handoff controller: first attempt, backoff, toasts and notice actions
 * (TASK-SKRIPT-41-02-05, U2b).
 *
 * Expected behavior:
 *   The first attempt gates the view. Transient failures show one toast and
 *   retry in the background with doubling delay, at most three times; the last
 *   failure shows one more toast. Rejections leave a notice with download,
 *   remove and (vault-full) manual retry actions. Disposing the scope stops
 *   timers and silences late completions.
 */

import { createPinia, setActivePinia } from "pinia";
import { effectScope } from "vue";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { unzipSync } from "fflate";

import { useToastStore } from "../../../stores/toast";
import {
  createInMemoryExamWorkspaceGuestDraftStorage,
  type ExamWorkspaceGuestDraftStoragePort,
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
  GUEST_HANDOFF_LATE_SUCCESS_COPY,
  GUEST_HANDOFF_MANUAL_RETRY_FAILED_COPY,
  GUEST_HANDOFF_RETRIES_EXHAUSTED_COPY,
  GUEST_HANDOFF_TRANSIENT_COPY,
  useExamWorkspaceGuestHandoffController,
} from "./useExamWorkspaceGuestHandoffController";
import {
  type GuestHandoffDeps,
  type GuestHandoffTeacher,
} from "./useExamWorkspaceGuestHandoff";

type ImportResult = Awaited<ReturnType<GuestHandoffTeacher["importExamWorkspaceGuestDraft"]>>;

function successResult(draft: ExamWorkspaceGuestDraft, lineageId = "lineage-new"): ImportResult {
  return {
    conversion: null,
    document: draft.saved_document,
    export_blockers: [],
    history_cursor: draft.cursor,
    notes: [],
    saved_document: draft.saved_document,
    summary: {
      course_key: null,
      lineage_id: lineageId,
      name: draft.saved_document.title,
      saved_at: draft.saved_at,
      title: draft.saved_document.title,
      vault_file_id: "file-1",
      version: draft.saved_document.revision,
    },
  };
}

function toastSpies() {
  const store = useToastStore();
  return {
    failure: vi.spyOn(store, "failure"),
    success: vi.spyOn(store, "success"),
    warning: vi.spyOn(store, "warning"),
  };
}

function toastMessages(spy: { mock: { calls: Array<[string, ...unknown[]]> } }): string[] {
  return spy.mock.calls.map((call) => call[0]);
}

/**
 * jsdom's Blob has no `arrayBuffer`; equip the stored picture blobs with the
 * production Web API through FileReader, following the per-blob
 * `Object.defineProperty(file, "arrayBuffer", ...)` pattern in
 * `client.csrfRecovery.spec.ts`. The in-memory storage keeps picture bytes
 * by reference, so patching the loaded blobs patches the stored ones.
 */
async function equipStoredPictureBytes(
  storage: ExamWorkspaceGuestDraftStoragePort,
): Promise<void> {
  const stored = await storage.load();
  if (stored === null) {
    throw new Error("expected a stored draft to equip");
  }
  for (const blob of Object.values(stored.assets)) {
    Object.defineProperty(blob, "arrayBuffer", {
      configurable: true,
      value: async (): Promise<ArrayBuffer> => {
        const bytes = await blobBytes(blob);
        const copy = new Uint8Array(bytes.length);
        copy.set(bytes);
        return copy.buffer;
      },
    });
  }
}

/**
 * Read a download Blob as raw bytes through FileReader: jsdom's Blob has no
 * `arrayBuffer` the specs can rely on.
 */
async function blobBytes(blob: Blob): Promise<Uint8Array> {
  return await new Promise<Uint8Array>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      if (reader.result instanceof ArrayBuffer) {
        resolve(new Uint8Array(reader.result));
        return;
      }
      reject(new Error("The FileReader did not return bytes."));
    };
    reader.onerror = () => reject(reader.error ?? new Error("Could not read the blob bytes."));
    reader.readAsArrayBuffer(blob);
  });
}

function startController(deps: Omit<GuestHandoffDeps, "owner">, download?: (blob: Blob, filename: string) => void) {
  const scope = effectScope();
  const controller = scope.run(() =>
    useExamWorkspaceGuestHandoffController(deps, download === undefined ? undefined : { download }),
  );
  if (controller === undefined) {
    throw new Error("expected the scope to produce a controller");
  }
  return { controller, scope };
}

beforeEach(() => {
  setActivePinia(createPinia());
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("useExamWorkspaceGuestHandoffController", () => {
  it("1) transient at start retries three times with doubling delay, then stops", async () => {
    const { lock, rejections, storage, teacher } = await seedGuestHandoffHarness();
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(apiError(503, "SERVICE_UNAVAILABLE"));
    const { controller, scope } = startController({ lock, rejections, storage, teacher });
    const spies = toastSpies();
    try {
      await expect(controller.start()).resolves.toBeNull();
      expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);
      expect(useToastStore().toasts.map((toast) => toast.message)).toEqual([
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

  it("3) permanent at start leaves a notice, no toast and no retry", async () => {
    const { lock, rejections, storage, teacher } = await seedGuestHandoffHarness();
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(apiError(422, "DOCUMENT_SCHEMA_OUTDATED"));
    const { controller, scope } = startController({ lock, rejections, storage, teacher });
    const spies = toastSpies();
    try {
      await expect(controller.start()).resolves.toBeNull();
      expect(controller.notice.value).toEqual({ reason: "permanent", busy: false });
      expect(spies.warning).not.toHaveBeenCalled();
      expect(spies.success).not.toHaveBeenCalled();
      expect(spies.failure).not.toHaveBeenCalled();

      await vi.advanceTimersByTimeAsync(3_600_000);
      expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);
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

  it("6b) vault_full retry can turn permanent with a new draft", async () => {
    const { lock, rejections, storage, teacher } = await seedGuestHandoffHarness();
    teacher.importExamWorkspaceGuestDraft
      .mockRejectedValueOnce(apiError(422, "VALIDATION_ERROR", { reason: "vault_full" }))
      .mockRejectedValueOnce(apiError(422, "DOCUMENT_SCHEMA_OUTDATED"));
    const { controller, scope } = startController({ lock, rejections, storage, teacher });
    const spies = toastSpies();
    try {
      await expect(controller.start()).resolves.toBeNull();
      await controller.retry();
      expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(2);
      expect(controller.notice.value).toEqual({ reason: "permanent", busy: false });
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

  it("7) download saves one zip with the stored record and its picture bytes", async () => {
    const { draft, lock, rejections, storage, teacher } = await seedGuestHandoffHarness();
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
      expect(controller.notice.value).toEqual({ reason: "permanent", busy: false });
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
      expect(controller.notice.value).toEqual({ reason: "permanent", busy: false });
    } finally {
      scope.stop();
    }
  });

  it("7d) download with nothing stored downloads nothing and shows S6", async () => {
    const { draft, lock, rejections, storage, teacher } = await seedGuestHandoffHarness();
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
      expect(controller.notice.value).toEqual({ reason: "permanent", busy: false });
    } finally {
      scope.stop();
    }
  });

  it("7e) download with an unreadable storage downloads nothing and shows S6", async () => {
    const { lock, rejections, storage, teacher } = await seedGuestHandoffHarness();
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
      expect(controller.notice.value).toEqual({ reason: "permanent", busy: false });
    } finally {
      scope.stop();
    }
  });

  it("7f) download marks the notice busy while storage reads", async () => {
    const { lock, rejections, storage, teacher } = await seedGuestHandoffHarness();
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
      expect(controller.notice.value).toEqual({ reason: "permanent", busy: true });
      expect(download).not.toHaveBeenCalled();
      vi.useRealTimers();
      release(await storage.load());
      await pending;
      expect(download).toHaveBeenCalledTimes(1);
      expect(controller.notice.value).toEqual({ reason: "permanent", busy: false });
    } finally {
      scope.stop();
    }
  });

  it("8a) remove clears the draft, the record and the notice", async () => {
    const { lock, rejections, storage, teacher } = await seedGuestHandoffHarness();
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
      expect(controller.notice.value).toEqual({ reason: "permanent", busy: false });
      expect(rejections.read()).toEqual({ cursor: draft.cursor, reason: "permanent" });
      await expect(storage.load()).resolves.not.toBeNull();
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
