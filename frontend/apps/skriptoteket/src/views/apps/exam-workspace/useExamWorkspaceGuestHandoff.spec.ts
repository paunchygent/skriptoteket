/**
 * Exam workspace guest handoff after sign-in.
 *
 * Expected behavior:
 *   With no stored draft the handoff calls nothing and returns null. With a
 *   draft it posts the newest (position) document with the draft id and only
 *   the declared picture bytes, clears the browser copy only after the post
 *   succeeds, and returns the new lineage id. A failed post keeps the browser
 *   copy, shows one failure toast and returns null. A failed clear after a
 *   successful post still returns the lineage id, and the clear never runs
 *   before the post resolves.
 */

import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi, type Mock } from "vitest";

import type {
  ExamWorkspaceDocumentResponse,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import { useToastStore } from "../../../stores/toast";
import { createInMemoryExamWorkspaceGuestDraftStorage } from "./examWorkspaceGuestDraftStorage";
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

function createIds(): ExamWorkspaceGuestDraftIdSource {
  let counter = 0;
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

  it("hands the newest document with only the declared blobs, then clears and returns the lineage", async () => {
    const storage = createInMemoryExamWorkspaceGuestDraftStorage();
    const { draft, position } = editedDraft();
    const blobA = new Blob(["a"]);
    const blobB = new Blob(["b"]);
    await storage.save({
      assets: { asset_a: blobA, asset_b: blobB, asset_extra: new Blob(["extra"]) },
      draft,
    });
    const teacher = teacherMock();
    teacher.importExamWorkspaceGuestDraft.mockResolvedValue(handoffResponse("lineage-new"));

    await expect(runGuestHandoff({ storage, teacher })).resolves.toBe("lineage-new");

    expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);
    expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledWith(draft.draft_id, position, {
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
    await storage.save(stored);
    const teacher = teacherMock();
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(new Error("nätverksfel"));

    await expect(runGuestHandoff({ storage, teacher })).resolves.toBeNull();

    await expect(storage.load()).resolves.toEqual(stored);
    expect(failureToasts()).toEqual([GUEST_HANDOFF_FAILURE_COPY]);
  });

  it("still returns the lineage when clearing the browser copy fails after a successful post", async () => {
    const inner = createInMemoryExamWorkspaceGuestDraftStorage();
    const { draft } = editedDraft();
    await inner.save({ assets: {}, draft });
    const clear = vi.fn().mockRejectedValue(new Error("lagringen svarar inte"));
    const storage: ExamWorkspaceGuestDraftStoragePort = {
      clear,
      load: () => inner.load(),
      save: (next) => inner.save(next),
    };
    const teacher = teacherMock();
    teacher.importExamWorkspaceGuestDraft.mockResolvedValue(handoffResponse("lineage-new"));

    await expect(runGuestHandoff({ storage, teacher })).resolves.toBe("lineage-new");

    expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);
    expect(clear).toHaveBeenCalledTimes(1);
    expect(failureToasts()).toEqual([]);
  });

  it("never clears the browser copy before the post resolves", async () => {
    const inner = createInMemoryExamWorkspaceGuestDraftStorage();
    const { draft } = editedDraft();
    await inner.save({ assets: {}, draft });
    const clear = vi.fn().mockImplementation(() => inner.clear());
    const storage: ExamWorkspaceGuestDraftStoragePort = {
      clear,
      load: () => inner.load(),
      save: (next) => inner.save(next),
    };
    let resolvePost!: (response: ExamWorkspaceDocumentResponse) => void;
    const post = new Promise<ExamWorkspaceDocumentResponse>((resolve) => {
      resolvePost = resolve;
    });
    const teacher = teacherMock();
    teacher.importExamWorkspaceGuestDraft.mockReturnValue(post);

    const handoff = runGuestHandoff({ storage, teacher });
    await Promise.resolve();
    expect(clear).not.toHaveBeenCalled();

    resolvePost(handoffResponse("lineage-new"));
    await expect(handoff).resolves.toBe("lineage-new");
    expect(clear).toHaveBeenCalledTimes(1);
  });

  it("returns null without posting, toasting or clearing when the stored draft cannot be read", async () => {
    const clear = vi.fn();
    const storage: ExamWorkspaceGuestDraftStoragePort = {
      clear,
      load: () => Promise.reject(new Error("lagringen är blockerad")),
      save: () => Promise.reject(new Error("unreachable")),
    };
    const teacher = teacherMock();

    await expect(runGuestHandoff({ storage, teacher })).resolves.toBeNull();

    expect(teacher.importExamWorkspaceGuestDraft).not.toHaveBeenCalled();
    expect(clear).not.toHaveBeenCalled();
    expect(failureToasts()).toEqual([]);
  });
});
