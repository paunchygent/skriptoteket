/**
 * Guest exam workspace store: the one save model.
 *
 * Expected behavior (TASK-SKRIPT-40-04-14 behaviour item 8, unit K7):
 *   A stored step updates the saved draft, so reopening shows the stored
 *   edit with a bumped revision. Ångra and Gör om move the draft to the
 *   retained step through the store's position move, without storing a new
 *   step. The status after a store reads `Sparat i webbläsaren HH:MM`.
 */

import { describe, expect, it } from "vitest";

import { examWorkspaceGuestSaveStatus } from "./examWorkspaceGuestDraft";
import {
  DOCUMENT_ID,
  exam,
  installGuestStoreObjectUrls,
  setupGuestStore,
  startBlank,
} from "./examWorkspaceGuestStore.specSupport";

installGuestStoreObjectUrls();

describe("examWorkspaceGuestStore one save model", () => {
  it("updates the saved draft on every stored step", async () => {
    const context = setupGuestStore();
    await startBlank(context, "Original");
    const opened = await context.store.store.shared.getExamWorkspaceDocument(DOCUMENT_ID);

    const step = await context.store.store.shared.storeExamWorkspaceUndoStep(DOCUMENT_ID, {
      afterStepId: null,
      document: exam("A"),
      expectedCursor: opened.history_cursor,
    });

    expect(step.document.title).toBe("A");
    const reopened = await context.store.store.shared.getExamWorkspaceDocument(DOCUMENT_ID);
    expect(reopened.document.title).toBe("A");
    expect(reopened.saved_document.title).toBe("A");
    expect(reopened.saved_document.revision).toBe(2);
    expect(reopened.summary.version).toBe(2);
  });

  it("moves the draft to the retained step on undo and back on redo", async () => {
    const context = setupGuestStore();
    await startBlank(context, "Original");
    const lineageId = DOCUMENT_ID;
    const opened = await context.store.store.shared.getExamWorkspaceDocument(lineageId);
    const history = await context.store.store.shared.getExamWorkspaceHistory(lineageId);

    const first = await context.store.store.shared.storeExamWorkspaceUndoStep(lineageId, {
      afterStepId: null,
      document: exam("A"),
      expectedCursor: opened.history_cursor,
    });
    const second = await context.store.store.shared.storeExamWorkspaceUndoStep(lineageId, {
      afterStepId: null,
      document: exam("B"),
      expectedCursor: first.history.cursor,
    });

    const undone = await context.store.moveToHistoryStep(lineageId, {
      expectedCursor: second.history.cursor,
      stepId: first.history.position_step_id,
    });
    expect(undone.history.step_ids).toHaveLength(2);
    const undoneOpen = await context.store.store.shared.getExamWorkspaceDocument(lineageId);
    expect(undoneOpen.document.title).toBe("A");
    expect(undoneOpen.saved_document.title).toBe("A");

    const redone = await context.store.moveToHistoryStep(lineageId, {
      expectedCursor: undone.history.cursor,
      stepId: second.history.position_step_id,
    });
    expect(redone.history.position_step_id).toBe(second.history.position_step_id);
    const redoneOpen = await context.store.store.shared.getExamWorkspaceDocument(lineageId);
    expect(redoneOpen.document.title).toBe("B");
    expect(redoneOpen.saved_document.title).toBe("B");

    const historyAfter = await context.store.store.shared.getExamWorkspaceHistory(lineageId);
    expect(historyAfter.step_ids).toHaveLength(2);
    expect(historyAfter.baseline_step_id).toBe(history.baseline_step_id);
  });

  it("reads the guest status as Sparat i webbläsaren HH:MM after a store", async () => {
    const context = setupGuestStore();
    await startBlank(context, "Original");
    const opened = await context.store.store.shared.getExamWorkspaceDocument(DOCUMENT_ID);
    await context.store.store.shared.storeExamWorkspaceUndoStep(DOCUMENT_ID, {
      afterStepId: null,
      document: exam("A"),
      expectedCursor: opened.history_cursor,
    });

    const reopened = await context.store.store.shared.getExamWorkspaceDocument(DOCUMENT_ID);
    const status = examWorkspaceGuestSaveStatus(reopened.summary.saved_at);

    expect(status).toMatch(/^Sparat i webbläsaren \d{2}:\d{2}$/);
  });
});
