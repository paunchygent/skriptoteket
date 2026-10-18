/**
 * Guest exam workspace store.
 *
 * Expected behavior:
 *   A guest's exam lives only in the browser. Starting blank, autosaving,
 *   branching after an undo, Spara and reopening a NEW store over the same
 *   storage reproduce the server's document/history state; a stale cursor or
 *   revision is the server's 409 and a refused draft its 422, neither
 *   changing what the browser holds; a parent command sends the editor's
 *   document, stores exactly one step and reports the public route's export
 *   blockers; an export sends the saved copy and exactly its declared picture
 *   bytes; and the public routes' 429 limit error is recognized by status.
 */

import { beforeAll, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../api/client";
import type { NativeExamDocument } from "../../../api/examWorkspace";
import { buildParentDocument } from "./examWorkspaceParentDocument.specSupport";
import {
  createGuestExamWorkspaceStore,
  isGuestLimitError,
} from "./examWorkspaceGuestStore";
import {
  newGuestDraft,
  type ExamWorkspaceGuestDraftIdSource,
} from "./examWorkspaceGuestDraft";
import { createInMemoryExamWorkspaceGuestDraftStorage } from "./examWorkspaceGuestDraftStorage";
import { newTeacherItem } from "./examWorkspaceItemEdits";

type PublicApi = typeof import("../../../api/publicExamWorkspace");

const DOCUMENT_ID = "00000000-0000-4000-8000-000000000001";
const STALE_CURSOR = "99999999-9999-4999-8999-999999999999";
const NOW = "2026-10-18T10:00:00.000Z";

beforeAll(() => {
  vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:picture");
  vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
});

/** Any current-schema document; scenarios override only the title. */
function exam(title = "Original"): NativeExamDocument {
  return { ...buildParentDocument(), title };
}

function pictureExam(title = "Bildprov"): NativeExamDocument {
  return {
    ...exam(title),
    assets: [
      {
        asset_id: "asset_001",
        byte_length: 4,
        height: 1,
        media_type: "image/png",
        sha256: "a".repeat(64),
        width: 1,
      },
    ],
    instructions: [
      { heading_level: null, segments: [{ asset_id: "asset_001", kind: "asset" }] },
    ],
  };
}

function refusedExam(): NativeExamDocument {
  const document = exam("Refused");
  return { ...document, items: [{ ...document.items[0]!, points: -1 }] };
}

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

function setup() {
  const storage = createInMemoryExamWorkspaceGuestDraftStorage();
  const ids = createIds();
  const mocks = {
    addChild: vi.fn(),
    catalog: vi.fn(),
    changeType: vi.fn(),
    createBlank: vi.fn(),
    createEmptyPart: vi.fn(),
    createParent: vi.fn(),
    deleteChild: vi.fn(),
    deleteParent: vi.fn(),
    exportChecklist: vi.fn(),
    exportDownload: vi.fn(),
    groupItems: vi.fn(),
    misspellings: vi.fn(),
    moveItem: vi.fn(),
    reorderChildren: vi.fn(),
  };
  const api: PublicApi = {
    addPublicExamWorkspaceChild: mocks.addChild,
    changePublicExamWorkspaceItemType: mocks.changeType,
    createEmptyPublicExamWorkspacePart: mocks.createEmptyPart,
    createPublicExamWorkspaceBlank: mocks.createBlank,
    createPublicExamWorkspaceParent: mocks.createParent,
    deletePublicExamWorkspaceChild: mocks.deleteChild,
    deletePublicExamWorkspaceParent: mocks.deleteParent,
    downloadPublicExamWorkspaceExport: mocks.exportDownload,
    getPublicExamCourseCatalog: mocks.catalog,
    getPublicExamWorkspaceExportChecklist: mocks.exportChecklist,
    groupPublicExamWorkspaceItems: mocks.groupItems,
    movePublicExamWorkspaceItem: mocks.moveItem,
    reorderPublicExamWorkspaceChildren: mocks.reorderChildren,
    requestPublicExamWorkspaceAnswerMisspellings: mocks.misspellings,
  };
  const store = createGuestExamWorkspaceStore({ api, ids, storage });
  return { api, ids, mocks, storage, store };
}

async function startBlank(setupResult: ReturnType<typeof setup>, title = "Original"): Promise<string> {
  setupResult.mocks.createBlank.mockResolvedValue({
    document: exam(title),
    export_blockers: [],
  });
  return await setupResult.store.startBlank();
}

describe("examWorkspaceGuestStore", () => {
  it("has no teacher services and starts a blank exam in the browser", async () => {
    const context = setup();
    expect(await context.store.currentLineageId()).toBeNull();

    const lineageId = await startBlank(context, "Nytt prov");

    expect(context.store.store.teacher).toBeNull();
    expect(lineageId).toBe(DOCUMENT_ID);
    expect(await context.store.currentLineageId()).toBe(DOCUMENT_ID);
    const opened = await context.store.store.shared.getExamWorkspaceDocument(lineageId);
    expect(opened.document.title).toBe("Nytt prov");
    expect(opened.document.revision).toBe(1);
    expect(opened.export_blockers).toEqual([]);
    expect(opened.summary.lineage_id).toBe(DOCUMENT_ID);
    expect(await context.storage.load()).not.toBeNull();
  });

  it("reports an unknown lineage as the server's 404", async () => {
    const context = setup();
    await startBlank(context);

    const error = await context.store.store.shared
      .getExamWorkspaceDocument("99999999-9999-4999-8999-999999999999")
      .catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      code: "NOT_FOUND",
      details: { lineage_id: "99999999-9999-4999-8999-999999999999" },
      status: 404,
    });
  });

  it("reproduces autosave, an undo branch, redo-drop, Spara and a reload over the same storage", async () => {
    const context = setup();
    const lineageId = await startBlank(context);
    const opened = await context.store.store.shared.getExamWorkspaceDocument(lineageId);
    const history = await context.store.store.shared.getExamWorkspaceHistory(lineageId);

    const autosaved = await context.store.store.shared.storeExamWorkspaceUndoStep(lineageId, {
      afterStepId: null,
      document: exam("A"),
      expectedCursor: opened.history_cursor,
    });

    // Undo is a pure read of the baseline; nothing moves until the next write.
    const baseline = await context.store.store.shared.getExamWorkspaceHistoryStep(
      lineageId,
      history.baseline_step_id,
    );
    expect(baseline.document.title).toBe("Original");

    const branched = await context.store.store.shared.storeExamWorkspaceUndoStep(lineageId, {
      afterStepId: history.baseline_step_id,
      document: exam("B"),
      expectedCursor: autosaved.history.cursor,
    });
    // A branch after the baseline drops the redo step A.
    expect(branched.history.step_ids).toEqual([branched.history.position_step_id]);
    expect(branched.document.title).toBe("B");

    const saved = await context.store.store.shared.saveExamWorkspaceDocument(lineageId, {
      document: exam("Sparad"),
      expectedRevision: 1,
      positionStepId: branched.history.position_step_id,
    });
    expect(saved.saved_document.revision).toBe(2);
    expect(saved.document.title).toBe("Sparad");

    const firstOpen = await context.store.store.shared.getExamWorkspaceDocument(lineageId);
    const firstHistory = await context.store.store.shared.getExamWorkspaceHistory(lineageId);

    const reloaded = createGuestExamWorkspaceStore({
      api: context.api,
      ids: context.ids,
      storage: context.storage,
    });
    const secondOpen = await reloaded.store.shared.getExamWorkspaceDocument(lineageId);
    const secondHistory = await reloaded.store.shared.getExamWorkspaceHistory(lineageId);

    expect(secondOpen).toEqual(firstOpen);
    expect(secondHistory).toEqual(firstHistory);
    expect(secondOpen.document.title).toBe("Sparad");
    expect(secondOpen.saved_document.title).toBe("Sparad");
    expect(secondOpen.saved_document.revision).toBe(2);
    expect(secondHistory.position_step_id).toBe(firstHistory.position_step_id);
  });

  it("rejects a stale cursor on autosave and a parent command without persisting", async () => {
    const context = setup();
    const lineageId = await startBlank(context);
    const persisted = await context.storage.load();

    const autosaveError = await context.store.store.shared
      .storeExamWorkspaceUndoStep(lineageId, {
        afterStepId: null,
        document: exam("X"),
        expectedCursor: "99999999-9999-4999-8999-999999999999",
      })
      .catch((caught: unknown) => caught);

    expect(autosaveError).toBeInstanceOf(ApiError);
    expect(autosaveError).toMatchObject({ code: "CONFLICT", status: 409 });
    expect(await context.storage.load()).toBe(persisted);

    const parentError = await context.store.store.shared
      .createExamWorkspaceParent(lineageId, {
        child: newTeacherItem("item_002", 2, "free_text"),
        expected_cursor: "99999999-9999-4999-8999-999999999999",
        instruction: [],
        position: 0,
      })
      .catch((caught: unknown) => caught);

    expect(parentError).toBeInstanceOf(ApiError);
    expect(parentError).toMatchObject({ code: "CONFLICT", status: 409 });
    expect(context.mocks.createParent).not.toHaveBeenCalled();
    expect(await context.storage.load()).toBe(persisted);
  });

  it("rejects Spara with the server's 422 for a document the save rules refuse", async () => {
    const context = setup();
    const lineageId = await startBlank(context);
    const persisted = await context.storage.load();

    const error = await context.store.store.shared
      .saveExamWorkspaceDocument(lineageId, {
        document: refusedExam(),
        expectedRevision: 1,
        positionStepId: DOCUMENT_ID,
      })
      .catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ code: "VALIDATION_ERROR", status: 422 });
    expect((error as ApiError).message).not.toBe("");
    expect(await context.storage.load()).toBe(persisted);
  });

  it("sends the editor's document with a parent command, stores one step and reports the blockers", async () => {
    const context = setup();
    const lineageId = await startBlank(context);
    const opened = await context.store.store.shared.getExamWorkspaceDocument(lineageId);
    const blocker = { item_id: null, reason: "title_without_text" as const };
    context.mocks.createParent.mockResolvedValue({
      document: exam("Med instruktion"),
      export_blockers: [blocker],
    });
    const child = newTeacherItem("item_002", 2, "free_text");
    const instruction = [
      { heading_level: null, segments: [{ kind: "text" as const, marks: [], text: "Läs." }] },
    ];

    const response = await context.store.store.shared.createExamWorkspaceParent(lineageId, {
      child,
      expected_cursor: opened.history_cursor,
      instruction,
      position: 0,
    });

    expect(context.mocks.createParent).toHaveBeenCalledWith({
      child,
      document: opened.document,
      instruction,
      position: 0,
    });
    expect(response.export_blockers).toEqual([blocker]);
    expect(response.document.title).toBe("Med instruktion");
    expect(response.history_cursor).not.toBe(opened.history_cursor);
    const history = await context.store.store.shared.getExamWorkspaceHistory(lineageId);
    expect(history.step_ids).toHaveLength(1);
    expect(history.step_ids[0]).toBe(history.position_step_id);
    expect(history.position_step_id).toBe(response.history_cursor);
  });

  it("runs group, empty part and move as one public call and one undo step each", async () => {
    const context = setup();
    const lineageId = await startBlank(context);
    const opened = await context.store.store.shared.getExamWorkspaceDocument(lineageId);
    context.mocks.groupItems.mockResolvedValue({
      created_parent_id: "parent_002",
      document: exam("Grupperad"),
      export_blockers: [],
    });
    context.mocks.createEmptyPart.mockResolvedValue({
      created_parent_id: "parent_003",
      document: exam("Ny del"),
      export_blockers: [],
    });
    context.mocks.moveItem.mockResolvedValue({ document: exam("Flyttad"), export_blockers: [] });

    const grouped = await context.store.store.shared.groupExamWorkspaceItems(lineageId, [
      "item_004",
    ], opened.history_cursor);
    expect(context.mocks.groupItems).toHaveBeenCalledTimes(1);
    expect(context.mocks.groupItems.mock.calls[0]![0]).toEqual(opened.document);
    expect(context.mocks.groupItems).toHaveBeenCalledWith(expect.anything(), ["item_004"]);
    expect(grouped.created_parent_id).toBe("parent_002");
    expect(grouped.document.title).toBe("Grupperad");
    expect(grouped.export_blockers).toEqual([]);
    let history = await context.store.store.shared.getExamWorkspaceHistory(lineageId);
    expect(history.step_ids).toHaveLength(1);
    expect(history.step_ids[0]).toBe(history.position_step_id);
    expect(history.position_step_id).toBe(grouped.history_cursor);
    expect((await context.storage.load())?.draft.cursor).toBe(grouped.history_cursor);

    const emptied = await context.store.store.shared.createEmptyExamWorkspacePart(
      lineageId,
      2,
      grouped.history_cursor,
    );
    expect(context.mocks.createEmptyPart).toHaveBeenCalledTimes(1);
    expect(context.mocks.createEmptyPart.mock.calls[0]![0]).toEqual(grouped.document);
    expect(context.mocks.createEmptyPart).toHaveBeenCalledWith(expect.anything(), 2);
    expect(emptied.created_parent_id).toBe("parent_003");
    expect(emptied.document.title).toBe("Ny del");
    history = await context.store.store.shared.getExamWorkspaceHistory(lineageId);
    expect(history.step_ids).toHaveLength(2);
    expect(history.position_step_id).toBe(emptied.history_cursor);
    expect((await context.storage.load())?.draft.cursor).toBe(emptied.history_cursor);

    const moved = await context.store.store.shared.moveExamWorkspaceItem(
      lineageId,
      "item_004",
      "parent_002",
      emptied.history_cursor,
    );
    expect(context.mocks.moveItem).toHaveBeenCalledTimes(1);
    expect(context.mocks.moveItem.mock.calls[0]![0]).toEqual(emptied.document);
    expect(context.mocks.moveItem).toHaveBeenCalledWith(expect.anything(), "item_004", "parent_002");
    expect(moved.document.title).toBe("Flyttad");
    history = await context.store.store.shared.getExamWorkspaceHistory(lineageId);
    expect(history.step_ids).toHaveLength(3);
    expect(history.position_step_id).toBe(moved.history_cursor);
    expect((await context.storage.load())?.draft.cursor).toBe(moved.history_cursor);
  });

  it("refuses a stale cursor on the part commands without calling or persisting", async () => {
    const context = setup();
    const lineageId = await startBlank(context);
    const persisted = await context.storage.load();

    const attempts = [
      () =>
        context.store.store.shared.groupExamWorkspaceItems(lineageId, ["item_004"], STALE_CURSOR),
      () => context.store.store.shared.createEmptyExamWorkspacePart(lineageId, 0, STALE_CURSOR),
      () =>
        context.store.store.shared.moveExamWorkspaceItem(lineageId, "item_004", null, STALE_CURSOR),
    ];
    for (const attempt of attempts) {
      const error = await attempt().catch((caught: unknown) => caught);
      expect(error).toBeInstanceOf(ApiError);
      expect(error).toMatchObject({ code: "CONFLICT", status: 409 });
    }

    expect(context.mocks.groupItems).not.toHaveBeenCalled();
    expect(context.mocks.createEmptyPart).not.toHaveBeenCalled();
    expect(context.mocks.moveItem).not.toHaveBeenCalled();
    expect(await context.storage.load()).toBe(persisted);
  });

  it("keeps the draft on a 422 from a part route and reports a 429 as the guest limit", async () => {
    const context = setup();
    const lineageId = await startBlank(context);
    const opened = await context.store.store.shared.getExamWorkspaceDocument(lineageId);
    const persisted = await context.storage.load();

    const refusal = new ApiError({
      code: "VALIDATION_ERROR",
      message: "Provet måste ha minst en fråga.",
      status: 422,
    });
    context.mocks.moveItem.mockRejectedValue(refusal);
    const refused = await context.store.store.shared
      .moveExamWorkspaceItem(lineageId, "item_004", null, opened.history_cursor)
      .catch((caught: unknown) => caught);
    expect(refused).toBe(refusal);
    expect(await context.storage.load()).toBe(persisted);

    const limit = new ApiError({
      code: "TOO_MANY_REQUESTS",
      details: { bucket: "guest_edit", reason: "caller_limit" },
      message: "Gränsen för gäster är nådd. Logga in för att fortsätta.",
      status: 429,
    });
    context.mocks.groupItems.mockRejectedValue(limit);
    const limited = await context.store.store.shared
      .groupExamWorkspaceItems(lineageId, ["item_004"], opened.history_cursor)
      .catch((caught: unknown) => caught);
    expect(limited).toBe(limit);
    expect(isGuestLimitError(limited)).toBe(true);
    expect(await context.storage.load()).toBe(persisted);
  });

  it("exports the saved copy and exactly its declared picture bytes", async () => {
    const context = setup();
    const png = new Blob(["png-bytes"], { type: "image/png" });
    const unused = new Blob(["unused"], { type: "image/png" });
    const saved = pictureExam("Sparad");
    const seeded = newGuestDraft(saved, createIds());
    await context.storage.save({ assets: { asset_001: png, unused }, draft: seeded });

    // The editor's working copy drops the picture; the saved copy still declares it.
    const step = await context.store.store.shared.storeExamWorkspaceUndoStep(DOCUMENT_ID, {
      afterStepId: null,
      document: exam("Utkast"),
      expectedCursor: seeded.cursor,
    });
    expect(step.document.title).toBe("Utkast");

    context.mocks.exportDownload.mockResolvedValueOnce({
      blob: new Blob(["zip"]),
      contentType: "application/zip",
      filename: "prov.zip",
    });
    const result = await context.store.store.shared.downloadExamWorkspaceExport(
      DOCUMENT_ID,
      "qti",
      1,
    );

    const [target, request] = context.mocks.exportDownload.mock.calls[0]!;
    expect(target).toBe("qti");
    expect(request.document).toEqual(saved);
    expect(request.document.title).toBe("Sparad");
    expect(Object.keys(request.assets)).toEqual(["asset_001"]);
    expect(request.assets["asset_001"]).toBe(png);
    expect(result.filename).toBe("prov.zip");

    context.mocks.exportDownload.mockClear();
    const stale = await context.store.store.shared
      .downloadExamWorkspaceExport(DOCUMENT_ID, "qti", 99)
      .catch((caught: unknown) => caught);
    expect(stale).toBeInstanceOf(ApiError);
    expect(stale).toMatchObject({ code: "CONFLICT", status: 409 });
    expect(context.mocks.exportDownload).not.toHaveBeenCalled();
  });

  it("returns the checklist only for the saved revision", async () => {
    const context = setup();
    await startBlank(context);
    const checklist = { entries: [] };
    context.mocks.exportChecklist.mockResolvedValueOnce(checklist);

    expect(
      await context.store.store.shared.getExamWorkspaceExportChecklist(DOCUMENT_ID, 1),
    ).toBe(checklist);

    const stale = await context.store.store.shared
      .getExamWorkspaceExportChecklist(DOCUMENT_ID, 2)
      .catch((caught: unknown) => caught);
    expect(stale).toBeInstanceOf(ApiError);
    expect(stale).toMatchObject({ status: 409 });
    expect(context.mocks.exportChecklist).toHaveBeenCalledTimes(1);
  });

  it("propagates a public 429 unchanged and recognizes only the limit status", async () => {
    const context = setup();
    await startBlank(context);
    const limit = new ApiError({
      code: "TOO_MANY_REQUESTS",
      details: { bucket: "guest_edit", reason: "caller_limit" },
      message: "Gränsen för gäster är nådd. Logga in för att fortsätta.",
      status: 429,
    });
    context.mocks.misspellings.mockRejectedValue(limit);

    const error = await context.store.store.shared
      .requestExamWorkspaceAnswerMisspellings({
        accepted_values: ["Göteborg"],
        document_text: "Göteborg",
        other_gold_answers: [],
      })
      .catch((caught: unknown) => caught);

    expect(error).toBe(limit);
    expect(isGuestLimitError(error)).toBe(true);
    expect(
      isGuestLimitError(new ApiError({ code: "VALIDATION_ERROR", message: "x", status: 422 })),
    ).toBe(false);
    expect(isGuestLimitError(new Error("429"))).toBe(false);
  });

  it("maps the open draft's stored pictures to object URLs and clears them", async () => {
    const context = setup();
    const png = new Blob(["png-bytes"], { type: "image/png" });
    const draft = newGuestDraft(pictureExam(), createIds());
    await context.storage.save({ assets: { asset_001: png }, draft });

    await context.store.store.shared.getExamWorkspaceDocument(DOCUMENT_ID);

    expect(context.store.store.shared.examWorkspaceAssetUrl(DOCUMENT_ID, "asset_001")).toBe(
      "blob:picture",
    );
    expect(context.store.store.shared.examWorkspaceAssetUrl(DOCUMENT_ID, "missing")).toBe("");
    expect(context.store.store.shared.examWorkspaceAssetUrl("other", "asset_001")).toBe("");

    await context.store.clear();

    expect(context.store.store.shared.examWorkspaceAssetUrl(DOCUMENT_ID, "asset_001")).toBe("");
    expect(await context.storage.load()).toBeNull();
  });
});
