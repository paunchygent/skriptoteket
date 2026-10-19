/**
 * Exam workspace guest handoff after sign-in.
 *
 * Expected behavior:
 *   With no stored draft the handoff calls nothing and returns null. With a
 *   draft it posts the newest (position) document keyed by the snapshot
 *   cursor with only the declared picture bytes, then clears only that
 *   snapshot and returns the new lineage id. A failed post keeps the browser
 *   copy, shows one failure toast and returns null. A failed clearIf after a
 *   successful post still returns the lineage id, and the clear never runs
 *   before the post resolves. A newer draft or newer edits stored while the
 *   post is in flight are kept; a second handoff posts the new cursor as its
 *   own key.
 */

import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi, type Mock } from "vitest";

import type {
  ExamWorkspaceDocumentResponse,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import { useToastStore } from "../../../stores/toast";
import {
  createInMemoryExamWorkspaceGuestDraftStorage,
  type StoredGuestDraft,
} from "./examWorkspaceGuestDraftStorage";
import type { ExamWorkspaceGuestDraftStoragePort } from "./examWorkspaceGuestDraftStorage";
import {
  guestDocumentResponse,
  newGuestDraft,
  storeGuestUndoStep,
  type ExamWorkspaceGuestDraft,
  type ExamWorkspaceGuestDraftIdSource,
} from "./examWorkspaceGuestDraft";
import { buildParentDocument } from "./examWorkspaceParentDocument.specSupport";
import {
  GUEST_HANDOFF_FAILURE_COPY,
  runGuestHandoff,
  type GuestHandoffTeacher,
} from "./useExamWorkspaceGuestHandoff";

const NOW = "2026-10-18T10:00:00.000Z";

function createIds(start = 0): ExamWorkspaceGuestDraftIdSource {
  let counter = start;
  return {
    now: () => NOW,
    uuid: () => {
      counter += 1;
      return `10000000-0000-4000-8000-${String(counter).padStart(12, "0")}`;
    },
  };
}

function assetEntry(assetId: string) {
  return {
    asset_id: assetId,
    byte_length: 1,
    height: 1,
    media_type: "image/png" as const,
    sha256: "a".repeat(64),
    width: 1,
  };
}

function pictureDocument(): NativeExamDocument {
  return {
    ...buildParentDocument(),
    assets: [assetEntry("asset_a"), assetEntry("asset_b")],
  };
}

/** The draft stands on a newer edit than the saved baseline. */
function editedDraft(): { draft: ExamWorkspaceGuestDraft; position: NativeExamDocument } {
  const ids = createIds();
  const draft = newGuestDraft(pictureDocument(), ids);
  const outcome = storeGuestUndoStep(
    draft,
    { afterStepId: null, document: { ...pictureDocument(), title: "Redigerad" }, expectedCursor: draft.cursor },
    ids,
  );
  if (outcome.kind !== "ok") {
    throw new Error(`expected a stored step, got ${outcome.kind}`);
  }
  return { draft: outcome.draft, position: guestDocumentResponse(outcome.draft).document };
}

function handoffResponse(lineageId: string): ExamWorkspaceDocumentResponse {
  const { position } = editedDraft();
  return {
    conversion: null,
    document: position,
    export_blockers: [],
    history_cursor: "20000000-0000-4000-8000-000000000001",
    notes: [],
    saved_document: position,
    summary: {
      course_key: null,
      lineage_id: lineageId,
      name: position.title,
      saved_at: NOW,
      title: position.title,
      vault_file_id: "file-1",
      version: position.revision,
    },
  };
}

function teacherMock(): { importExamWorkspaceGuestDraft: Mock<GuestHandoffTeacher["importExamWorkspaceGuestDraft"]> } {
  return {
    importExamWorkspaceGuestDraft: vi.fn<GuestHandoffTeacher["importExamWorkspaceGuestDraft"]>(),
  };
}

function failureToasts(): string[] {
  return useToastStore().toasts.map((toast) => toast.message);
}

async function seed(
  storage: ExamWorkspaceGuestDraftStoragePort,
  stored: StoredGuestDraft,
): Promise<void> {
  expect(await storage.replaceIf(null, stored)).toBe(true);
}

beforeEach(() => {
  setActivePinia(createPinia());
});

describe("runGuestHandoff", () => {
  it("calls nothing and returns null without a stored draft", async () => {
    const storage = createInMemoryExamWorkspaceGuestDraftStorage();
    const teacher = teacherMock();

    await expect(runGuestHandoff({ storage, teacher })).resolves.toBeNull();

    expect(teacher.importExamWorkspaceGuestDraft).not.toHaveBeenCalled();
    await expect(storage.load()).resolves.toBeNull();
    expect(failureToasts()).toEqual([]);
  });

  it("hands the newest document with only the declared blobs, then clears the snapshot and returns the lineage", async () => {
    const storage = createInMemoryExamWorkspaceGuestDraftStorage();
    const { draft, position } = editedDraft();
    const blobA = new Blob(["a"]);
    const blobB = new Blob(["b"]);
    await seed(storage, {
      assets: { asset_a: blobA, asset_b: blobB, asset_extra: new Blob(["extra"]) },
      draft,
    });
    const teacher = teacherMock();
    teacher.importExamWorkspaceGuestDraft.mockResolvedValue(handoffResponse("lineage-new"));

    await expect(runGuestHandoff({ storage, teacher })).resolves.toBe("lineage-new");

    expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);
    expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledWith(draft.cursor, position, {
      asset_a: blobA,
      asset_b: blobB,
    });
    await expect(storage.load()).resolves.toBeNull();
    expect(failureToasts()).toEqual([]);
  });

  it("keeps the browser copy, toasts once and returns null when the post fails", async () => {
    const storage = createInMemoryExamWorkspaceGuestDraftStorage();
    const { draft } = editedDraft();
    const stored = {
      assets: { asset_a: new Blob(["a"]), asset_b: new Blob(["b"]) },
      draft,
    };
    await seed(storage, stored);
    const teacher = teacherMock();
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(new Error("nätverksfel"));

    await expect(runGuestHandoff({ storage, teacher })).resolves.toBeNull();

    await expect(storage.load()).resolves.toEqual(stored);
    expect(failureToasts()).toEqual([GUEST_HANDOFF_FAILURE_COPY]);
  });

  it("still returns the lineage when clearing the snapshot fails after a successful post", async () => {
    const inner = createInMemoryExamWorkspaceGuestDraftStorage();
    const { draft } = editedDraft();
    await seed(inner, { assets: {}, draft });
    const clearIf = vi.fn().mockRejectedValue(new Error("lagringen svarar inte"));
    const storage: ExamWorkspaceGuestDraftStoragePort = {
      clearIf,
      load: () => inner.load(),
      replaceIf: (expected, next) => inner.replaceIf(expected, next),
    };
    const teacher = teacherMock();
    teacher.importExamWorkspaceGuestDraft.mockResolvedValue(handoffResponse("lineage-new"));

    await expect(runGuestHandoff({ storage, teacher })).resolves.toBe("lineage-new");

    expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);
    expect(clearIf).toHaveBeenCalledTimes(1);
    expect(clearIf).toHaveBeenCalledWith(draft.cursor);
    expect(failureToasts()).toEqual([]);
  });

  it("never clears the browser snapshot before the post resolves", async () => {
    const inner = createInMemoryExamWorkspaceGuestDraftStorage();
    const { draft } = editedDraft();
    await seed(inner, { assets: {}, draft });
    const clearIf = vi.fn().mockImplementation((expected: string) => inner.clearIf(expected));
    const storage: ExamWorkspaceGuestDraftStoragePort = {
      clearIf,
      load: () => inner.load(),
      replaceIf: (expected, next) => inner.replaceIf(expected, next),
    };
    let resolvePost!: (response: ExamWorkspaceDocumentResponse) => void;
    const post = new Promise<ExamWorkspaceDocumentResponse>((resolve) => {
      resolvePost = resolve;
    });
    const teacher = teacherMock();
    teacher.importExamWorkspaceGuestDraft.mockReturnValue(post);

    const handoff = runGuestHandoff({ storage, teacher });
    await Promise.resolve();
    expect(clearIf).not.toHaveBeenCalled();

    resolvePost(handoffResponse("lineage-new"));
    await expect(handoff).resolves.toBe("lineage-new");
    expect(clearIf).toHaveBeenCalledTimes(1);
  });

  it("keeps a newer draft stored while the old snapshot posts and clears nothing of it", async () => {
    const storage = createInMemoryExamWorkspaceGuestDraftStorage();
    const old = newGuestDraft(buildParentDocument(), createIds());
    await seed(storage, { assets: {}, draft: old });
    let resolvePost!: (response: ExamWorkspaceDocumentResponse) => void;
    const post = new Promise<ExamWorkspaceDocumentResponse>((resolve) => {
      resolvePost = resolve;
    });
    const teacher = teacherMock();
    teacher.importExamWorkspaceGuestDraft.mockReturnValue(post);

    const handoff = runGuestHandoff({ storage, teacher });
    await vi.waitFor(() => expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledOnce());
    expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledWith(
      old.cursor,
      expect.anything(),
      expect.anything(),
    );

    const newer = newGuestDraft(
      { ...buildParentDocument(), document_id: "11111111-1111-4111-8111-111111111111" },
      createIds(),
    );
    expect(await storage.replaceIf(old.cursor, { assets: {}, draft: newer })).toBe(true);

    resolvePost(handoffResponse("lineage-old"));
    await expect(handoff).resolves.toBe("lineage-old");

    // The posted snapshot is gone but the newer draft owns the slot now.
    const kept = await storage.load();
    expect(kept?.draft.lineage_id).toBe(newer.lineage_id);
    expect(kept?.draft.cursor).toBe(newer.cursor);
  });

  it("keeps edits of the same draft made mid-post and posts the new cursor on the next handoff", async () => {
    const storage = createInMemoryExamWorkspaceGuestDraftStorage();
    // A distinct id source: production cursors come from crypto.randomUUID,
    // so the mid-post edit must not reuse the seeded draft's cursor string.
    const editIds = createIds(100);
    const { draft } = editedDraft();
    await seed(storage, { assets: {}, draft });
    let resolvePost!: (response: ExamWorkspaceDocumentResponse) => void;
    const post = new Promise<ExamWorkspaceDocumentResponse>((resolve) => {
      resolvePost = resolve;
    });
    const teacher = teacherMock();
    teacher.importExamWorkspaceGuestDraft.mockReturnValue(post);

    const first = runGuestHandoff({ storage, teacher });
    await vi.waitFor(() => expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledOnce());

    const edited = storeGuestUndoStep(
      draft,
      {
        afterStepId: null,
        document: { ...pictureDocument(), title: "Redigerad igen" },
        expectedCursor: draft.cursor,
      },
      editIds,
    );
    if (edited.kind !== "ok") {
      throw new Error(`expected a stored step, got ${edited.kind}`);
    }
    expect(await storage.replaceIf(draft.cursor, { assets: {}, draft: edited.draft })).toBe(true);

    resolvePost(handoffResponse("lineage-old"));
    await expect(first).resolves.toBe("lineage-old");

    const kept = await storage.load();
    expect(kept?.draft.cursor).toBe(edited.draft.cursor);

    teacher.importExamWorkspaceGuestDraft.mockResolvedValue(handoffResponse("lineage-new"));
    await expect(runGuestHandoff({ storage, teacher })).resolves.toBe("lineage-new");
    expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(2);
    expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenNthCalledWith(
      2,
      edited.draft.cursor,
      expect.anything(),
      expect.anything(),
    );
    expect(teacher.importExamWorkspaceGuestDraft.mock.calls[1]?.[0]).not.toBe(
      teacher.importExamWorkspaceGuestDraft.mock.calls[0]?.[0],
    );
    await expect(storage.load()).resolves.toBeNull();
  });

  it("returns null without posting, toasting or clearing when the stored draft cannot be read", async () => {
    const clearIf = vi.fn();
    const storage: ExamWorkspaceGuestDraftStoragePort = {
      clearIf,
      load: () => Promise.reject(new Error("lagringen är blockerad")),
      replaceIf: () => Promise.reject(new Error("unreachable")),
    };
    const teacher = teacherMock();

    await expect(runGuestHandoff({ storage, teacher })).resolves.toBeNull();

    expect(teacher.importExamWorkspaceGuestDraft).not.toHaveBeenCalled();
    expect(clearIf).not.toHaveBeenCalled();
    expect(failureToasts()).toEqual([]);
  });
});
