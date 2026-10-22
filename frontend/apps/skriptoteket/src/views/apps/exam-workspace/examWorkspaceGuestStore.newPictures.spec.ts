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

import type { NativeExamDocument } from "../../../api/examWorkspace";
import {
  DOCUMENT_ID,
  exam,
  installGuestStoreObjectUrls,
  LEASE_TAB_ID,
  pictureExam,
  setupGuestStore,
  startBlank,
} from "./examWorkspaceGuestStore.specSupport";
import { TRANSPARENT_PNG_PICTURE } from "./examWorkspacePictureFixtures.specSupport";

installGuestStoreObjectUrls();

/** An accepted-case picture exam: the real fixture asset declared in the exam instruction. */
function coherentPictureExam(title: string): NativeExamDocument {
  const asset = TRANSPARENT_PNG_PICTURE.asset;
  return {
    ...exam(title),
    assets: [asset],
    instructions: [{ heading_level: null, segments: [{ asset_id: asset.asset_id, kind: "asset" }] }],
  };
}

describe("examWorkspaceGuestStore new pictures", () => {
  it("writes new picture bytes in the same write as the step and serves them", async () => {
    const context = setupGuestStore();
    await startBlank(context, "Original");
    const opened = await context.store.store.shared.getExamWorkspaceDocument(DOCUMENT_ID);
    const pictureId = TRANSPARENT_PNG_PICTURE.asset.asset_id;
    const blob = TRANSPARENT_PNG_PICTURE.blob();

    const step = await context.store.store.shared.storeExamWorkspaceUndoStep(DOCUMENT_ID, {
      afterStepId: null,
      document: coherentPictureExam("With picture"),
      expectedCursor: opened.history_cursor,
      newPictures: { [pictureId]: blob },
      tabId: LEASE_TAB_ID,
    });

    expect(step.document.assets.map((asset) => asset.asset_id)).toContain(pictureId);
    const stored = await context.storage.load();
    expect(stored?.assets[pictureId]).toBe(blob);
    expect(context.store.store.shared.examWorkspaceAssetUrl(DOCUMENT_ID, pictureId)).toBe(
      "blob:picture",
    );
  });

  it("keeps the bytes across later stores and undo/redo while a retained step declares them", async () => {
    const context = setupGuestStore();
    await startBlank(context, "Original");
    const opened = await context.store.store.shared.getExamWorkspaceDocument(DOCUMENT_ID);
    const pictureId = TRANSPARENT_PNG_PICTURE.asset.asset_id;
    const blob = TRANSPARENT_PNG_PICTURE.blob();

    const first = await context.store.store.shared.storeExamWorkspaceUndoStep(DOCUMENT_ID, {
      afterStepId: null,
      document: coherentPictureExam("With picture"),
      expectedCursor: opened.history_cursor,
      newPictures: { [pictureId]: blob },
      tabId: LEASE_TAB_ID,
    });
    const second = await context.store.store.shared.storeExamWorkspaceUndoStep(DOCUMENT_ID, {
      afterStepId: null,
      document: coherentPictureExam("With picture, edited"),
      expectedCursor: first.history.cursor,
      newPictures: {},
      tabId: LEASE_TAB_ID,
    });
    expect((await context.storage.load())?.assets[pictureId]).toBe(blob);

    const undone = await context.store.moveToHistoryStep(DOCUMENT_ID, {
      expectedCursor: second.history.cursor,
      stepId: first.history.position_step_id,
      tabId: LEASE_TAB_ID,
    });
    expect((await context.storage.load())?.assets[pictureId]).toBe(blob);
    expect(context.store.store.shared.examWorkspaceAssetUrl(DOCUMENT_ID, pictureId)).toBe(
      "blob:picture",
    );

    const redone = await context.store.moveToHistoryStep(DOCUMENT_ID, {
      expectedCursor: undone.history.cursor,
      stepId: second.history.position_step_id,
      tabId: LEASE_TAB_ID,
    });
    expect(redone.history.position_step_id).toBe(second.history.position_step_id);
    expect((await context.storage.load())?.assets[pictureId]).toBe(blob);
  });

  // Rejection case, deliberately malformed: `pictureExam` declares
  // `asset_001` with a placeholder digest while no stored Blob backs it, so
  // the store must refuse the step.
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
