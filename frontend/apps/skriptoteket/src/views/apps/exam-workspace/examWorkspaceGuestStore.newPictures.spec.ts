/**
 * Guest exam workspace store: new-picture bytes in the undo-step write
 * (TASK-SKRIPT-39-10-04, unit U5).
 *
 * Expected behavior:
 *   A store whose params carry `newPictures` writes the Blob into the stored
 *   draft's assets in the same conditional write as the step, and the
 *   picture's object URL appears through `examWorkspaceAssetUrl`. A later
 *   store without `newPictures` keeps the Blob while a retained step declares
 *   it, and guest Ångra/Gör om keeps it too.
 */

import { describe, expect, it } from "vitest";

import {
  DOCUMENT_ID,
  installGuestStoreObjectUrls,
  LEASE_TAB_ID,
  pictureExam,
  setupGuestStore,
  startBlank,
} from "./examWorkspaceGuestStore.specSupport";

installGuestStoreObjectUrls();

describe("examWorkspaceGuestStore new pictures", () => {
  it("writes new picture bytes in the same write as the step and serves them", async () => {
    const context = setupGuestStore();
    await startBlank(context, "Original");
    const opened = await context.store.store.shared.getExamWorkspaceDocument(DOCUMENT_ID);
    const blob = new Blob(["png!"], { type: "image/png" });

    const step = await context.store.store.shared.storeExamWorkspaceUndoStep(DOCUMENT_ID, {
      afterStepId: null,
      document: pictureExam("With picture"),
      expectedCursor: opened.history_cursor,
      newPictures: { asset_001: blob },
      tabId: LEASE_TAB_ID,
    });

    expect(step.document.assets.map((asset) => asset.asset_id)).toContain("asset_001");
    const stored = await context.storage.load();
    expect(stored?.assets["asset_001"]).toBe(blob);
    expect(context.store.store.shared.examWorkspaceAssetUrl(DOCUMENT_ID, "asset_001")).toBe(
      "blob:picture",
    );
  });

  it("keeps the bytes across later stores and undo/redo while a retained step declares them", async () => {
    const context = setupGuestStore();
    await startBlank(context, "Original");
    const opened = await context.store.store.shared.getExamWorkspaceDocument(DOCUMENT_ID);
    const blob = new Blob(["png!"], { type: "image/png" });

    const first = await context.store.store.shared.storeExamWorkspaceUndoStep(DOCUMENT_ID, {
      afterStepId: null,
      document: pictureExam("With picture"),
      expectedCursor: opened.history_cursor,
      newPictures: { asset_001: blob },
      tabId: LEASE_TAB_ID,
    });
    const second = await context.store.store.shared.storeExamWorkspaceUndoStep(DOCUMENT_ID, {
      afterStepId: null,
      document: pictureExam("With picture, edited"),
      expectedCursor: first.history.cursor,
      newPictures: {},
      tabId: LEASE_TAB_ID,
    });
    expect((await context.storage.load())?.assets["asset_001"]).toBe(blob);

    const undone = await context.store.moveToHistoryStep(DOCUMENT_ID, {
      expectedCursor: second.history.cursor,
      stepId: first.history.position_step_id,
      tabId: LEASE_TAB_ID,
    });
    expect((await context.storage.load())?.assets["asset_001"]).toBe(blob);
    expect(context.store.store.shared.examWorkspaceAssetUrl(DOCUMENT_ID, "asset_001")).toBe(
      "blob:picture",
    );

    const redone = await context.store.moveToHistoryStep(DOCUMENT_ID, {
      expectedCursor: undone.history.cursor,
      stepId: second.history.position_step_id,
      tabId: LEASE_TAB_ID,
    });
    expect(redone.history.position_step_id).toBe(second.history.position_step_id);
    expect((await context.storage.load())?.assets["asset_001"]).toBe(blob);
  });

  it("refuses a step that declares a picture the stored assets do not hold", async () => {
    const context = setupGuestStore();
    await startBlank(context, "Original");
    const opened = await context.store.store.shared.getExamWorkspaceDocument(DOCUMENT_ID);

    await expect(
      context.store.store.shared.storeExamWorkspaceUndoStep(DOCUMENT_ID, {
        afterStepId: null,
        document: pictureExam("With picture"),
        expectedCursor: opened.history_cursor,
        newPictures: {},
        tabId: LEASE_TAB_ID,
      }),
    ).rejects.toMatchObject({
      code: "VALIDATION_ERROR",
      details: { missing_assets: ["asset_001"] },
      message: "Dokumentet hänvisar till bilder som saknas.",
      status: 422,
    });

    const stored = await context.storage.load();
    expect(stored?.draft.cursor).toBe(opened.history_cursor);
    expect(stored?.draft.steps).toHaveLength(0);
    expect(stored?.assets).toEqual({});
  });
});
