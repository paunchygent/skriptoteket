/**
 * Guest exam workspace store: history and save.
 *
 * Expected behavior:
 *   A guest's exam lives only in the browser. Starting blank, autosaving,
 *   branching after an undo, dropping the redo steps, Spara and reopening a
 *   NEW store over the same storage reproduce the server's document/history
 *   state; a stale cursor on autosave or a parent command is the server's
 *   409 without persisting, and a refused Spara document its 422.
 */

import { describe, expect, it } from "vitest";

import { ApiError } from "../../../api/client";
import { newTeacherItem } from "./examWorkspaceItemEdits";
import { createGuestExamWorkspaceStore } from "./examWorkspaceGuestStore";
import {
  DOCUMENT_ID,
  exam,
  installGuestStoreObjectUrls,
  refusedExam,
  setupGuestStore,
  startBlank,
  type GuestStoreSetup,
} from "./examWorkspaceGuestStore.specSupport";

installGuestStoreObjectUrls();

async function startBlankSetup(title = "Original"): Promise<GuestStoreSetup> {
  const context = setupGuestStore();
  await startBlank(context, title);
  return context;
}

describe("examWorkspaceGuestStore history and save", () => {
  it("has no teacher services and starts a blank exam in the browser", async () => {
    const context = setupGuestStore();
    expect(await context.store.currentLineageId()).toBeNull();

    const lineageId = await startBlank(context, "Nytt prov");

    expect(context.store.store.teacher).toBeNull();
    expect(typeof context.store.store.guest?.startBlank).toBe("function");
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
    const context = await startBlankSetup();

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
    const context = await startBlankSetup();
    const lineageId = DOCUMENT_ID;
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

    const reloadedStore = createGuestExamWorkspaceStore({
      api: context.api,
      ids: context.ids,
      onLimit: context.onLimit,
      storage: context.storage,
    });
    const secondOpen = await reloadedStore.store.shared.getExamWorkspaceDocument(lineageId);
    const secondHistory = await reloadedStore.store.shared.getExamWorkspaceHistory(lineageId);

    expect(secondOpen).toEqual(firstOpen);
    expect(secondHistory).toEqual(firstHistory);
    expect(secondOpen.document.title).toBe("Sparad");
    expect(secondOpen.saved_document.title).toBe("Sparad");
    expect(secondOpen.saved_document.revision).toBe(2);
    expect(secondHistory.position_step_id).toBe(firstHistory.position_step_id);
  });

  it("rejects a stale cursor on autosave and a parent command without persisting", async () => {
    const context = await startBlankSetup();
    const lineageId = DOCUMENT_ID;
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
    const context = await startBlankSetup();
    const persisted = await context.storage.load();

    const error = await context.store.store.shared
      .saveExamWorkspaceDocument(DOCUMENT_ID, {
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
});
