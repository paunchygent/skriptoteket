/**
 * Exam workspace history: the new-picture save seam (TASK-SKRIPT-39-10-04, unit U5).
 *
 * Expected behavior:
 *   The history store passes `deps.newPictures.bytesFor(document)` as the
 *   store's `newPictures`, and marks the carried ids sent only after the
 *   transport answered with a committed step: the next store of a changed
 *   document passes nothing. A failed store (network error) or a 409
 *   conflict keeps the picture, and the retry passes it again.
 */

import { flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../api/client";
import type { NativeExamDocument } from "../../../api/examWorkspace";
import { buildParentDocument } from "./examWorkspaceParentDocument.specSupport";
import { setupHistory, type HistorySetupHooks } from "./useExamWorkspaceHistory.specSupport";
import { TRANSPARENT_PNG_PICTURE } from "./examWorkspacePictureFixtures.specSupport";

const apiMocks = vi.hoisted(() => ({
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  moveExamWorkspaceHistoryPosition: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
}));

vi.mock("../../../api/examWorkspace", () => apiMocks);

function setup(hooks: HistorySetupHooks = {}) {
  return setupHistory(apiMocks, false, hooks);
}

beforeEach(() => {
  setActivePinia(createPinia());
  for (const mock of Object.values(apiMocks)) mock.mockReset();
});

afterEach(() => {
  vi.useRealTimers();
});

const PICTURE_ASSET = TRANSPARENT_PNG_PICTURE.asset;

/** A registry double that only reports the picture while the document declares it unsent. */
function registryDouble(blob: Blob) {
  const sent = new Set<string>();
  const seen: NativeExamDocument[] = [];
  const noteSentCalls: string[][] = [];
  return {
    seen,
    noteSentCalls,
    bytesFor: (document: NativeExamDocument): Record<string, Blob> => {
      seen.push(document);
      const declares = document.assets.some((asset) => asset.asset_id === PICTURE_ASSET.asset_id);
      if (declares && !sent.has(PICTURE_ASSET.asset_id)) {
        return { [PICTURE_ASSET.asset_id]: blob };
      }
      return {};
    },
    noteSent: (assetIds: readonly string[]): void => {
      for (const assetId of assetIds) {
        sent.add(assetId);
      }
      noteSentCalls.push([...assetIds]);
    },
  };
}

function declarePicture(document: NativeExamDocument, title: string): NativeExamDocument {
  return {
    ...document,
    assets: [...document.assets, { ...PICTURE_ASSET }],
    title,
  };
}

describe("history new-picture save seam", () => {
  it("carries a declared new picture once, then never again", async () => {
    const blob = TRANSPARENT_PNG_PICTURE.blob();
    const newPictures = registryDouble(blob);
    const { history, workspaceDocument } = await setup({ newPictures });
    await flushPromises();

    workspaceDocument.value = declarePicture(workspaceDocument.value!, "With picture");
    await expect(history.flush(false)).resolves.toBe(true);

    expect(apiMocks.storeExamWorkspaceUndoStep).toHaveBeenCalledOnce();
    const first = apiMocks.storeExamWorkspaceUndoStep.mock.calls[0]![1];
    expect(first.newPictures).toEqual({ [PICTURE_ASSET.asset_id]: blob });
    expect(newPictures.seen[0]!.title).toBe("With picture");
    expect(newPictures.noteSentCalls).toEqual([[PICTURE_ASSET.asset_id]]);

    workspaceDocument.value = { ...workspaceDocument.value!, title: "With picture, edited" };
    await expect(history.flush(false)).resolves.toBe(true);

    expect(apiMocks.storeExamWorkspaceUndoStep).toHaveBeenCalledTimes(2);
    const second = apiMocks.storeExamWorkspaceUndoStep.mock.calls[1]![1];
    expect(second.newPictures).toEqual({});
  });

  it("keeps the picture across a failed store and passes it again on retry", async () => {
    const blob = TRANSPARENT_PNG_PICTURE.blob();
    const newPictures = registryDouble(blob);
    const { history, workspaceDocument } = await setup({ newPictures });
    await flushPromises();

    apiMocks.storeExamWorkspaceUndoStep.mockRejectedValueOnce(new Error("offline"));
    workspaceDocument.value = declarePicture(workspaceDocument.value!, "With picture");
    await expect(history.flush(false)).resolves.toBe(false);

    expect(newPictures.noteSentCalls).toEqual([]);

    await expect(history.flush(false)).resolves.toBe(true);
    const retry = apiMocks.storeExamWorkspaceUndoStep.mock.lastCall![1];
    expect(retry.newPictures).toEqual({ [PICTURE_ASSET.asset_id]: blob });
    expect(newPictures.noteSentCalls).toEqual([[PICTURE_ASSET.asset_id]]);
  });

  it("keeps the picture across a 409 conflict and passes it again once re-declared", async () => {
    const blob = TRANSPARENT_PNG_PICTURE.blob();
    const newPictures = registryDouble(blob);
    const { history, workspaceDocument } = await setup({ newPictures });
    await flushPromises();

    apiMocks.storeExamWorkspaceUndoStep.mockRejectedValueOnce(
      new ApiError({ code: "CONFLICT", message: "Dokumentet har ändrats sedan det öppnades.", status: 409 }),
    );
    workspaceDocument.value = declarePicture(workspaceDocument.value ?? buildParentDocument(), "With picture");
    await expect(history.flush(false)).resolves.toBe(false);
    await flushPromises();

    // The failed attempt marked nothing sent.
    expect(newPictures.noteSentCalls).toEqual([]);

    // The decided 409 policy replaces the pending edit on reload, so the
    // picture is re-declared before the next store carries it again.
    workspaceDocument.value = declarePicture(workspaceDocument.value ?? buildParentDocument(), "With picture");
    await expect(history.flush(false)).resolves.toBe(true);
    const retry = apiMocks.storeExamWorkspaceUndoStep.mock.lastCall![1];
    expect(retry.newPictures).toEqual({ [PICTURE_ASSET.asset_id]: blob });
    expect(newPictures.noteSentCalls).toEqual([[PICTURE_ASSET.asset_id]]);
  });
});
