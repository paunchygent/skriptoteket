/**
 * Guest handoff typed outcomes and recorded rejections (TASK-SKRIPT-41-02-05, U2a).
 *
 * Expected behavior:
 *   One handoff attempt returns a typed outcome. Permanent and vault_full
 *   rejections are recorded per draft cursor; while the record matches the
 *   stored draft's cursor, later calls return the rejection without posting.
 *   No toast is shown in any case.
 */

import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi, type Mock } from "vitest";

import { ApiError } from "../../../api/client";
import { useToastStore } from "../../../stores/toast";
import {
  createInMemoryExamWorkspaceGuestDraftStorage,
  type ExamWorkspaceGuestDraftStoragePort,
  type StoredGuestDraft,
} from "./examWorkspaceGuestDraftStorage";
import {
  createInMemoryGuestHandoffRejectionStorage,
  type GuestHandoffRejectionStoragePort,
} from "./examWorkspaceGuestHandoffRejection";
import {
  newGuestDraft,
  storeGuestUndoStep,
  type ExamWorkspaceGuestDraft,
  type ExamWorkspaceGuestDraftIdSource,
} from "./examWorkspaceGuestDraft";
import { buildParentDocument } from "./examWorkspaceParentDocument.specSupport";
import {
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

function pictureDocument() {
  return {
    ...buildParentDocument(),
    assets: [assetEntry("asset_a"), assetEntry("asset_b")],
  };
}

function editedDraft(): { draft: ExamWorkspaceGuestDraft } {
  const ids = createIds();
  const draft = newGuestDraft(pictureDocument(), ids, []);
  const outcome = storeGuestUndoStep(
    draft,
    { afterStepId: null, document: { ...pictureDocument(), title: "Redigerad" }, expectedCursor: draft.cursor },
    ids,
  );
  if (outcome.kind !== "ok") {
    throw new Error(`expected a stored step, got ${outcome.kind}`);
  }
  return { draft: outcome.draft };
}

function apiError(status: number, code = "ERROR", details: unknown = null): ApiError {
  return new ApiError({ code, details, message: code, status });
}

function teacherMock(): { importExamWorkspaceGuestDraft: Mock<GuestHandoffTeacher["importExamWorkspaceGuestDraft"]> } {
  return {
    importExamWorkspaceGuestDraft: vi.fn<GuestHandoffTeacher["importExamWorkspaceGuestDraft"]>(),
  };
}

type Harness = {
  storage: ExamWorkspaceGuestDraftStoragePort;
  rejections: GuestHandoffRejectionStoragePort;
  teacher: { importExamWorkspaceGuestDraft: Mock<GuestHandoffTeacher["importExamWorkspaceGuestDraft"]> };
  draft: ExamWorkspaceGuestDraft;
};

async function seedHarness(): Promise<Harness> {
  const storage = createInMemoryExamWorkspaceGuestDraftStorage();
  const rejections = createInMemoryGuestHandoffRejectionStorage();
  const { draft } = editedDraft();
  expect(await storage.replaceIf(null, {
    assets: { asset_a: new Blob(["a"]), asset_b: new Blob(["b"]) },
    draft,
  })).toBe(true);
  return { draft, rejections, storage, teacher: teacherMock() };
}

function failureToasts(): string[] {
  return useToastStore().toasts.map((toast) => toast.message);
}

beforeEach(() => {
  setActivePinia(createPinia());
});

describe("runGuestHandoff rejections", () => {
  it("a) 422 DOCUMENT_SCHEMA_OUTDATED rejects permanent, keeps the draft, records, and never posts again", async () => {
    const { draft, rejections, storage, teacher } = await seedHarness();
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(
      apiError(422, "DOCUMENT_SCHEMA_OUTDATED"),
    );

    const first = await runGuestHandoff({ rejections, storage, teacher });
    expect(first).toEqual({ draft, kind: "rejected", reason: "permanent" });
    expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);
    expect(rejections.read()).toEqual({ cursor: draft.cursor, reason: "permanent" });
    const kept: StoredGuestDraft | null = await storage.load();
    expect(kept?.draft).toEqual(draft);

    const second = await runGuestHandoff({ rejections, storage, teacher });
    expect(second).toEqual({ draft, kind: "rejected", reason: "permanent" });
    expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);
    expect(failureToasts()).toEqual([]);
  });

  it("b) 422 VALIDATION_ERROR rejects permanent and never posts again", async () => {
    const { draft, rejections, storage, teacher } = await seedHarness();
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(apiError(422, "VALIDATION_ERROR"));

    await expect(runGuestHandoff({ rejections, storage, teacher })).resolves.toEqual({
      draft,
      kind: "rejected",
      reason: "permanent",
    });
    await expect(runGuestHandoff({ rejections, storage, teacher })).resolves.toEqual({
      draft,
      kind: "rejected",
      reason: "permanent",
    });
    expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);
    expect(rejections.read()).toEqual({ cursor: draft.cursor, reason: "permanent" });
    expect(failureToasts()).toEqual([]);
  });

  it("c) 413 PAYLOAD_TOO_LARGE rejects permanent and never posts again", async () => {
    const { draft, rejections, storage, teacher } = await seedHarness();
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(apiError(413, "PAYLOAD_TOO_LARGE"));

    await expect(runGuestHandoff({ rejections, storage, teacher })).resolves.toEqual({
      draft,
      kind: "rejected",
      reason: "permanent",
    });
    await expect(runGuestHandoff({ rejections, storage, teacher })).resolves.toEqual({
      draft,
      kind: "rejected",
      reason: "permanent",
    });
    expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);
    expect(failureToasts()).toEqual([]);
  });

  it("d) vault_full is remembered, skipped without posting, and retried only with the ignore option", async () => {
    const { draft, rejections, storage, teacher } = await seedHarness();
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(
      apiError(422, "VALIDATION_ERROR", { reason: "vault_full" }),
    );

    await expect(runGuestHandoff({ rejections, storage, teacher })).resolves.toEqual({
      draft,
      kind: "rejected",
      reason: "vault_full",
    });
    expect(rejections.read()).toEqual({ cursor: draft.cursor, reason: "vault_full" });

    await expect(runGuestHandoff({ rejections, storage, teacher })).resolves.toEqual({
      draft,
      kind: "rejected",
      reason: "vault_full",
    });
    expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);

    await expect(
      runGuestHandoff({ rejections, storage, teacher }, { ignoreRecordedRejection: true }),
    ).resolves.toEqual({ draft, kind: "rejected", reason: "vault_full" });
    expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(2);
    expect(failureToasts()).toEqual([]);
  });

  it("e) a declared picture with no stored bytes rejects permanent with zero POSTs", async () => {
    const storage = createInMemoryExamWorkspaceGuestDraftStorage();
    const rejections = createInMemoryGuestHandoffRejectionStorage();
    const { draft } = editedDraft();
    expect(await storage.replaceIf(null, {
      assets: { asset_a: new Blob(["a"]) },
      draft,
    })).toBe(true);
    const teacher = teacherMock();

    await expect(runGuestHandoff({ rejections, storage, teacher })).resolves.toEqual({
      draft,
      kind: "rejected",
      reason: "permanent",
    });
    expect(teacher.importExamWorkspaceGuestDraft).not.toHaveBeenCalled();
    expect(rejections.read()).toEqual({ cursor: draft.cursor, reason: "permanent" });
    expect(failureToasts()).toEqual([]);
  });

  it("f) a draft whose position snapshot is missing resolves rejected permanent with zero POSTs", async () => {
    const storage = createInMemoryExamWorkspaceGuestDraftStorage();
    const rejections = createInMemoryGuestHandoffRejectionStorage();
    const { draft } = editedDraft();
    const broken: ExamWorkspaceGuestDraft = { ...draft, position_step_id: "missing-step" };
    expect(await storage.replaceIf(null, { assets: {}, draft: broken })).toBe(true);
    const teacher = teacherMock();

    await expect(runGuestHandoff({ rejections, storage, teacher })).resolves.toEqual({
      draft: broken,
      kind: "rejected",
      reason: "permanent",
    });
    expect(teacher.importExamWorkspaceGuestDraft).not.toHaveBeenCalled();
    expect(rejections.read()).toEqual({ cursor: broken.cursor, reason: "permanent" });
    expect(failureToasts()).toEqual([]);
  });

  it.each([
    ["503", apiError(503, "SERVICE_UNAVAILABLE")],
    ["429", apiError(429, "RATE_LIMITED")],
    ["fetch TypeError", new TypeError("Failed to fetch")],
  ])("g) %s returns transient, records nothing, and posts again", async (_label, error) => {
    const { draft, rejections, storage, teacher } = await seedHarness();
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(error);

    await expect(runGuestHandoff({ rejections, storage, teacher })).resolves.toEqual({
      kind: "transient",
    });
    expect(rejections.read()).toBeNull();
    const kept = await storage.load();
    expect(kept?.draft).toEqual(draft);

    await expect(runGuestHandoff({ rejections, storage, teacher })).resolves.toEqual({
      kind: "transient",
    });
    expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(2);
    expect(failureToasts()).toEqual([]);
  });

  it("h) 401 returns deferred and records nothing", async () => {
    const { draft, rejections, storage, teacher } = await seedHarness();
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(apiError(401, "UNAUTHORIZED"));

    await expect(runGuestHandoff({ rejections, storage, teacher })).resolves.toEqual({
      kind: "deferred",
    });
    expect(rejections.read()).toBeNull();
    const kept = await storage.load();
    expect(kept?.draft).toEqual(draft);
    expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);
    expect(failureToasts()).toEqual([]);
  });

  it("i) a stale record for another cursor is cleared and the current draft is posted", async () => {
    const { draft, rejections, storage, teacher } = await seedHarness();
    rejections.write({ cursor: "other-cursor", reason: "permanent" });
    teacher.importExamWorkspaceGuestDraft.mockResolvedValue({
      conversion: null,
      document: draft.saved_document,
      export_blockers: [],
      history_cursor: draft.cursor,
      notes: [],
      saved_document: draft.saved_document,
      summary: {
        course_key: null,
        lineage_id: "lineage-new",
        name: draft.saved_document.title,
        saved_at: NOW,
        title: draft.saved_document.title,
        vault_file_id: "file-1",
        version: draft.saved_document.revision,
      },
    });

    await expect(runGuestHandoff({ rejections, storage, teacher })).resolves.toEqual({
      kind: "handed_off",
      lineageId: "lineage-new",
    });
    expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);
    expect(rejections.read()).toBeNull();
    expect(failureToasts()).toEqual([]);
  });

  it("j) success under the ignore option clears the draft and the record", async () => {
    const { draft, rejections, storage, teacher } = await seedHarness();
    rejections.write({ cursor: draft.cursor, reason: "permanent" });
    teacher.importExamWorkspaceGuestDraft.mockResolvedValue({
      conversion: null,
      document: draft.saved_document,
      export_blockers: [],
      history_cursor: draft.cursor,
      notes: [],
      saved_document: draft.saved_document,
      summary: {
        course_key: null,
        lineage_id: "lineage-new",
        name: draft.saved_document.title,
        saved_at: NOW,
        title: draft.saved_document.title,
        vault_file_id: "file-1",
        version: draft.saved_document.revision,
      },
    });

    await expect(
      runGuestHandoff({ rejections, storage, teacher }, { ignoreRecordedRejection: true }),
    ).resolves.toEqual({ kind: "handed_off", lineageId: "lineage-new" });
    expect(teacher.importExamWorkspaceGuestDraft).toHaveBeenCalledTimes(1);
    await expect(storage.load()).resolves.toBeNull();
    expect(rejections.read()).toBeNull();
    expect(failureToasts()).toEqual([]);
  });

  it("k) no toast is shown in any failure case", async () => {
    const { rejections, storage, teacher } = await seedHarness();
    teacher.importExamWorkspaceGuestDraft.mockRejectedValue(
      apiError(422, "DOCUMENT_SCHEMA_OUTDATED"),
    );

    await runGuestHandoff({ rejections, storage, teacher });
    await runGuestHandoff({ rejections, storage, teacher });
    expect(failureToasts()).toEqual([]);
  });
});
