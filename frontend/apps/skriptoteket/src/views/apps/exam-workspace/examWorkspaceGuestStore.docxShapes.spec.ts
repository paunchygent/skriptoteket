/**
 * Guest exam workspace store: Word shapes on a picture's asset
 * (TASK-SKRIPT-39-04-22, unit 4b, D10).
 *
 * Expected behavior:
 *   The guest draft carries asset records whole. A picture's `docx_shapes`
 *   survive the stored undo step, the document the store serves afterwards and
 *   guest Ångra/Gör om; a step that replaced the picture holds the new asset
 *   without shapes, and the older step keeps its own copy.
 */

import { describe, expect, it } from "vitest";

import type { NativeExamAsset, NativeExamDocument } from "../../../api/examWorkspace";
import {
  DOCUMENT_ID,
  exam,
  installGuestStoreObjectUrls,
  LEASE_TAB_ID,
  setupGuestStore,
  startBlank,
} from "./examWorkspaceGuestStore.specSupport";
import { withReferencedAssetsOnly } from "./examWorkspaceStructure";
import {
  RED_PNG_PICTURE,
  TRANSPARENT_PNG_PICTURE,
} from "./examWorkspacePictureFixtures.specSupport";

installGuestStoreObjectUrls();

const SHAPES = '<w:drawing xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>';
const DRAWN: NativeExamAsset = { ...TRANSPARENT_PNG_PICTURE.asset, docx_shapes: SHAPES };

function instructionsWith(asset: NativeExamAsset, title: string): NativeExamDocument {
  return {
    ...exam(title),
    assets: [asset],
    instructions: [{ heading_level: null, segments: [{ asset_id: asset.asset_id, kind: "asset" }] }],
  };
}

describe("examWorkspaceGuestStore Word shapes", () => {
  it("keeps a picture's shapes in the stored step, the served document and undo/redo", async () => {
    const context = setupGuestStore();
    await startBlank(context, "Original");
    const opened = await context.store.store.shared.getExamWorkspaceDocument(DOCUMENT_ID);

    const drawn = await context.store.store.shared.storeExamWorkspaceUndoStep(DOCUMENT_ID, {
      afterStepId: null,
      document: instructionsWith(DRAWN, "Drawn"),
      expectedCursor: opened.history_cursor,
      newPictures: { [DRAWN.asset_id]: TRANSPARENT_PNG_PICTURE.blob() },
      tabId: LEASE_TAB_ID,
    });
    expect(drawn.document.assets).toEqual([DRAWN]);

    const replaced = await context.store.store.shared.storeExamWorkspaceUndoStep(DOCUMENT_ID, {
      afterStepId: null,
      document: instructionsWith(RED_PNG_PICTURE.asset, "Replaced"),
      expectedCursor: drawn.history.cursor,
      newPictures: { [RED_PNG_PICTURE.asset.asset_id]: RED_PNG_PICTURE.blob() },
      tabId: LEASE_TAB_ID,
    });
    expect(replaced.document.assets).toEqual([RED_PNG_PICTURE.asset]);
    const served = await context.store.store.shared.getExamWorkspaceDocument(DOCUMENT_ID);
    expect(served.document.assets).toEqual([RED_PNG_PICTURE.asset]);
    expect(JSON.stringify(served.document)).not.toContain("w:drawing");

    const undone = await context.store.moveToHistoryStep(DOCUMENT_ID, {
      expectedCursor: replaced.history.cursor,
      stepId: drawn.history.position_step_id,
      tabId: LEASE_TAB_ID,
    });
    expect(undone.document.assets).toEqual([DRAWN]);
    expect(
      (await context.store.store.shared.getExamWorkspaceDocument(DOCUMENT_ID)).document.assets,
    ).toEqual([DRAWN]);

    const redone = await context.store.moveToHistoryStep(DOCUMENT_ID, {
      expectedCursor: undone.history.cursor,
      stepId: replaced.history.position_step_id,
      tabId: LEASE_TAB_ID,
    });
    expect(redone.document.assets).toEqual([RED_PNG_PICTURE.asset]);
  });

  it("stores and reloads a picture a retry source alone still cites without its shapes", async () => {
    const context = setupGuestStore();
    await startBlank(context, "Original");
    const opened = await context.store.store.shared.getExamWorkspaceDocument(DOCUMENT_ID);
    const base = exam("Retry");
    const item = {
      ...base.items[0]!,
      body: [{ heading_level: null, segments: [] }],
      retry_source: {
        chunks: [
          {
            anchor: "body:0001",
            images: [{ asset_id: DRAWN.asset_id, marked_offset: 0, offset: 0 }],
            kind: "question",
            marked_text: "Rita figuren.",
            missing_images: [],
            paragraphs: [],
            runs: [],
            text: "Rita figuren.",
          },
        ],
        context_chunks: [],
        key_chunks: [],
        label_kind: "free_text" as const,
        owned_context_anchors: [],
      },
    };
    const pruned = withReferencedAssetsOnly({
      ...base,
      assets: [DRAWN],
      items: [item, ...base.items.slice(1)],
    });

    await context.store.store.shared.storeExamWorkspaceUndoStep(DOCUMENT_ID, {
      afterStepId: null,
      document: pruned,
      expectedCursor: opened.history_cursor,
      newPictures: { [DRAWN.asset_id]: TRANSPARENT_PNG_PICTURE.blob() },
      tabId: LEASE_TAB_ID,
    });

    const served = await context.store.store.shared.getExamWorkspaceDocument(DOCUMENT_ID);
    expect(served.document.assets).toEqual([TRANSPARENT_PNG_PICTURE.asset]);
    expect(served.document.assets[0]?.docx_shapes).toBeUndefined();
    expect(served.document.items[0]?.retry_source?.chunks[0]?.images[0]?.asset_id).toBe(
      DRAWN.asset_id,
    );
  });
});
