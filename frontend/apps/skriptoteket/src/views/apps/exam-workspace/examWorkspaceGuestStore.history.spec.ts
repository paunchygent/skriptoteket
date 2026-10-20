/**
 * Guest exam workspace store: history and the one save model.
 *
 * Expected behavior:
 *   A guest's exam lives only in the browser. Starting blank, autosaving,
 *   branching after an undo, dropping the redo steps, moving the position
 *   for Ångra and Gör om and reopening a NEW store over the same storage
 *   reproduce the server's document/history state; a stale cursor on
 *   autosave or a parent command is the server's 409 without persisting,
 *   and a refused autosave document its 422.
 */

import { describe, expect, it } from "vitest";

import { ApiError } from "../../../api/client";
import { newTeacherItem } from "./examWorkspaceItemEdits";
import { createGuestExamWorkspaceStore } from "./examWorkspaceGuestStore";
import {
  DOCUMENT_ID,
  exam,
  installGuestStoreObjectUrls,
  LEASE_TAB_ID,
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

    const lineageId = await startBlank(context, "Nytt prov");

    expect(context.store.store.teacher).toBeNull();
    expect(typeof context.store.store.guest?.startBlank).toBe("function");
    expect(lineageId).toBe(DOCUMENT_ID);
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

  it("reproduces autosave, an undo branch, redo-drop, a position move and a reload over the same storage", async () => {
    const context = await startBlankSetup();
    const lineageId = DOCUMENT_ID;
    const opened = await context.store.store.shared.getExamWorkspaceDocument(lineageId);
    const history = await context.store.store.shared.getExamWorkspaceHistory(lineageId);
    // A stored step is the save: the saved draft follows the step at once.
    expect(opened.saved_document.revision).toBe(1);

    const autosaved = await context.store.store.shared.storeExamWorkspaceUndoStep(lineageId, {
      afterStepId: null,
      document: exam("A"),
      expectedCursor: opened.history_cursor,
      tabId: LEASE_TAB_ID,
    });
    expect(autosaved.document.title).toBe("A");

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
      tabId: LEASE_TAB_ID,
    });
    // A branch after the baseline drops the redo step A.
    expect(branched.history.step_ids).toEqual([branched.history.position_step_id]);
    expect(branched.document.title).toBe("B");

    // Ångra moves the position to the baseline and the saved draft follows.
    const undone = await context.store.moveToHistoryStep(lineageId, {
      expectedCursor: branched.history.cursor,
      tabId: LEASE_TAB_ID,
      stepId: history.baseline_step_id,
    });
    expect(undone.history.step_ids).toEqual([branched.history.position_step_id]);
    const undoneOpen = await context.store.store.shared.getExamWorkspaceDocument(lineageId);
    expect(undoneOpen.document.title).toBe("Original");
    expect(undoneOpen.saved_document.title).toBe("Original");

    // Gör om moves back to the step without storing anything new.
    const redone = await context.store.moveToHistoryStep(lineageId, {
      expectedCursor: undone.history.cursor,
      tabId: LEASE_TAB_ID,
      stepId: branched.history.position_step_id,
    });
    expect(redone.history.step_ids).toEqual([branched.history.position_step_id]);

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
    expect(secondOpen.document.title).toBe("B");
    expect(secondOpen.saved_document.title).toBe("B");
    expect(secondOpen.saved_document.revision).toBe(5);
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
        tabId: LEASE_TAB_ID,
      })
      .catch((caught: unknown) => caught);

    expect(autosaveError).toBeInstanceOf(ApiError);
    expect(autosaveError).toMatchObject({ code: "CONFLICT", status: 409 });
    expect(await context.storage.load()).toEqual(persisted);

    const parentError = await context.store.store.shared
      .createExamWorkspaceParent(lineageId, {
        child: newTeacherItem("item_002", 2, "free_text"),
        expected_cursor: "99999999-9999-4999-8999-999999999999",
        tab_id: LEASE_TAB_ID,
        instruction: [],
        position: 0,
      })
      .catch((caught: unknown) => caught);

    expect(parentError).toBeInstanceOf(ApiError);
    expect(parentError).toMatchObject({ code: "CONFLICT", status: 409 });
    expect(context.mocks.createParent).not.toHaveBeenCalled();
    expect(await context.storage.load()).toEqual(persisted);
  });

  it("rejects an autosave the save rules refuse with the server's 422", async () => {
    const context = await startBlankSetup();
    const persisted = await context.storage.load();
    const opened = await context.store.store.shared.getExamWorkspaceDocument(DOCUMENT_ID);

    const error = await context.store.store.shared
      .storeExamWorkspaceUndoStep(DOCUMENT_ID, {
        afterStepId: null,
        document: refusedExam(),
        expectedCursor: opened.history_cursor,
      tabId: LEASE_TAB_ID,
      })
      .catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ code: "VALIDATION_ERROR", status: 422 });
    if (!(error instanceof ApiError)) {
      throw new Error("expected an ApiError");
    }
    expect(error.message).not.toBe("");
    expect(await context.storage.load()).toEqual(persisted);
  });
});
