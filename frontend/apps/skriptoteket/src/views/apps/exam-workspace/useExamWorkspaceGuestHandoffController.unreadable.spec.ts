/**
 * Guest handoff controller: an outdated-format refusal shows the unreadable
 * notice (U14, repairs F1).
 *
 * Expected behavior:
 *   A signed-in handoff the server refuses with DOCUMENT_SCHEMA_OUTDATED
 *   leaves the `unreadable` notice with the same download and remove as the
 *   permanent one; every other refusal keeps its current reason. A recorded
 *   permanent rejection for a draft the browser itself cannot read shows the
 *   unreadable notice on remount without posting again.
 */

import { createPinia, setActivePinia } from "pinia";
import { effectScope } from "vue";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { unzipSync } from "fflate";

import { useToastStore } from "../../../stores/toast";
import type { StoredGuestDraft } from "./examWorkspaceGuestDraftStorage";
import type { ExamWorkspaceGuestDraft } from "./examWorkspaceGuestDraft";
import {
  guestHandoffApiError as apiError,
  seedGuestHandoffHarness,
} from "./useExamWorkspaceGuestHandoff.specSupport";
import { EXAM_WORKSPACE_FILE_NOTICE_GUEST_UNREADABLE_COPY } from "./examWorkspaceFileNoticeCopy";
import { useExamWorkspaceGuestHandoffController } from "./useExamWorkspaceGuestHandoffController";
import type { GuestHandoffDeps } from "./useExamWorkspaceGuestHandoff";

const OLD_TOKEN = '"native_exam_document_v10"';
const V9_TOKEN = '"native_exam_document_v9"';

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

function toastMessages(): string[] {
  return useToastStore().toasts.map((toast) => toast.message);
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

async function equipStoredPictureBytes(storage: {
  load(): Promise<StoredGuestDraft | null>;
}): Promise<void> {
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

async function seatOlderFormat(storage: {
  load(): Promise<StoredGuestDraft | null>;
  replaceIf(expectedCursor: string | null, next: StoredGuestDraft): Promise<boolean>;
}): Promise<void> {
  const stored = await storage.load();
  if (stored === null) {
    throw new Error("expected a seeded draft to downgrade");
  }
  const draft: ExamWorkspaceGuestDraft = JSON.parse(
    JSON.stringify(stored.draft).replaceAll(OLD_TOKEN, V9_TOKEN),
  );
  // Picture bytes stay by reference: the draft is JSON data, the assets are not.
  const downgraded: StoredGuestDraft = { assets: stored.assets, draft };
  expect(await storage.replaceIf(stored.draft.cursor, downgraded)).toBe(true);
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
  it("an outdated-format refusal shows the unreadable notice, no toast and no retry", async () => {
    const { lock, rejections, storage, teacher } = await seedGuestHandoffHarness();
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(apiError(422, "DOCUMENT_SCHEMA_OUTDATED"));
    const { controller, scope } = startController({ lock, rejections, storage, teacher });
    try {
      await expect(controller.start()).resolves.toBeNull();
      expect(controller.notice.value).toEqual({ reason: "unreadable", busy: false });
      expect(toastMessages()).toEqual([]);

      await vi.advanceTimersByTimeAsync(3_600_000);
      expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);
    } finally {
      scope.stop();
    }
  });

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
