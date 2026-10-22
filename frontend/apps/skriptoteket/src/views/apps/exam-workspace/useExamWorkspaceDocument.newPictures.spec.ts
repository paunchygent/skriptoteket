/**
 * New pictures in the open exam (TASK-SKRIPT-39-10-04, unit U3).
 *
 * Expected behavior:
 *   Placing a declared picture in a question body declares its asset record
 *   in the same edit (one undo step, one autosave); replacing it drops the
 *   old record; instruction edits behave the same; the picture shows from
 *   its own bytes at once; opening another exam forgets it.
 */

import { flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { effectScope } from "vue";

import type {
  ExamWorkspaceDocumentResponse,
  NativeExamAsset,
  NativeExamBodyParagraph,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import { serverExamWorkspaceStore } from "./examWorkspaceStore";
import { createSyncFence, type SyncFence } from "./examWorkspaceSyncFence";
import { useExamWorkspaceDocument } from "./useExamWorkspaceDocument";
import {
  buildResponse,
  buildSavedExamSummary,
} from "./useExamWorkspaceDocument.specSupport";

const apiMocks = vi.hoisted(() => ({
  getExamWorkspaceConversionStatus: vi.fn(),
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  copyExamWorkspaceDocument: vi.fn(),
  examWorkspaceAssetUrl: vi.fn(
    (lineageId: string, assetId: string, revision?: number) =>
      `/api/lineage/${lineageId}/assets/${assetId}${revision === undefined ? "" : `?revision=${revision}`}`,
  ),
}));
const exportApiMocks = vi.hoisted(() => ({
  downloadExamWorkspaceExport: vi.fn(),
}));

vi.mock("../../../api/examWorkspaceExports", () => exportApiMocks);
vi.mock("../../../api/examWorkspace", async () => ({
  ...apiMocks,
  getExamCourseCatalog: (await import("../../../test/examCourseCatalog")).getExamCourseCatalog,
}));

beforeAll(() => {
  let next = 0;
  vi.spyOn(URL, "createObjectURL").mockImplementation(() => `blob:mock-${(next += 1)}`);
  vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
});

beforeEach(() => {
  setActivePinia(createPinia());
  apiMocks.getExamWorkspaceDocument.mockReset();
});

function picture(id: string): NativeExamAsset {
  return {
    asset_id: id,
    byte_length: 10,
    height: 20,
    media_type: "image/png",
    sha256: "c".repeat(64),
    width: 30,
  };
}

function bodyWith(assetId: string): NativeExamBodyParagraph[] {
  return [{ heading_level: null, segments: [{ kind: "asset", asset_id: assetId }] }];
}

function lineageResponse(lineageId: string): ExamWorkspaceDocumentResponse {
  const base = buildResponse();
  return {
    ...base,
    summary: buildSavedExamSummary({
      lineage_id: lineageId,
      name: `${lineageId}.provdokument.zip`,
      title: lineageId,
    }),
  };
}

type DocumentState = ReturnType<typeof useExamWorkspaceDocument>;

async function openDocument(
  onEdit: (structural: boolean, before: NativeExamDocument | null) => void = () => undefined,
): Promise<{ fence: SyncFence; state: DocumentState }> {
  apiMocks.getExamWorkspaceDocument.mockResolvedValue(lineageResponse("lineage-1"));
  const fence = createSyncFence();
  const state = effectScope().run(() =>
    useExamWorkspaceDocument({
      getFence: () => fence,
      onEdit,
      store: serverExamWorkspaceStore,
      submitRoute: () => Promise.resolve("failed"),
      noteInstallingCursor: () => undefined,
      tabId: () => "",
    }),
  );
  if (!state) {
    throw new Error("expected the document state to be created");
  }
  await state.openDocument("lineage-1", fence.begin());
  await flushPromises();
  return { fence, state };
}

describe("new pictures in useExamWorkspaceDocument", () => {
  it("declares a placed picture in the same body edit", async () => {
    const onEdit = vi.fn();
    const { state } = await openDocument(onEdit);
    const asset = picture("asset_aaaaaaaaaaaaaaaa");
    state.newPictures.declare(asset, new Blob(["bytes"], { type: "image/png" }));

    state.updateItemBody("item_001", bodyWith(asset.asset_id), true);

    expect(state.workspaceDocument.value?.assets).toEqual([asset]);
    expect(onEdit).toHaveBeenCalledTimes(1);
  });

  it("replacing the picture drops the old record and adds the new one", async () => {
    const { state } = await openDocument(vi.fn());
    const first = picture("asset_aaaaaaaaaaaaaaaa");
    const second = picture("asset_bbbbbbbbbbbbbbbb");
    state.newPictures.declare(first, new Blob(["one"], { type: "image/png" }));
    state.newPictures.declare(second, new Blob(["two"], { type: "image/png" }));
    state.updateItemBody("item_001", bodyWith(first.asset_id), true);

    state.updateItemBody("item_001", bodyWith(second.asset_id), true);

    expect(state.workspaceDocument.value?.assets).toEqual([second]);
  });

  it("declares a placed picture in the same instruction edit", async () => {
    const onEdit = vi.fn();
    const { state } = await openDocument(onEdit);
    const asset = picture("asset_aaaaaaaaaaaaaaaa");
    state.newPictures.declare(asset, new Blob(["bytes"], { type: "image/png" }));

    state.setExamInstructions(bodyWith(asset.asset_id), true);

    expect(state.workspaceDocument.value?.assets).toEqual([asset]);
    expect(onEdit).toHaveBeenCalledTimes(1);
  });

  it("shows the new picture from its own bytes at once", async () => {
    const { state } = await openDocument(vi.fn());
    const asset = picture("asset_aaaaaaaaaaaaaaaa");
    state.newPictures.declare(asset, new Blob(["bytes"], { type: "image/png" }));
    const url = state.newPictures.urls.value[asset.asset_id];
    expect(url).toBeDefined();

    state.updateItemBody("item_001", bodyWith(asset.asset_id), true);

    expect(state.assetUrls.value[asset.asset_id]).toBe(url);
  });

  it("opening another exam resets the registry", async () => {
    const { fence, state } = await openDocument(vi.fn());
    const asset = picture("asset_aaaaaaaaaaaaaaaa");
    state.newPictures.declare(asset, new Blob(["bytes"], { type: "image/png" }));
    state.updateItemBody("item_001", bodyWith(asset.asset_id), true);

    apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(lineageResponse("lineage-2"));
    await state.openDocument("lineage-2", fence.begin());
    await flushPromises();

    expect(state.newPictures.urls.value).toEqual({});
    expect(state.workspaceDocument.value?.assets).toEqual([]);
  });

  it("prunes sent when an edit stops declaring the picture, so re-adding resends its bytes", async () => {
    const { state } = await openDocument(vi.fn());
    const asset = picture("asset_aaaaaaaaaaaaaaaa");
    const bytes = new Blob(["bytes"], { type: "image/png" });
    state.newPictures.declare(asset, bytes);
    state.updateItemBody("item_001", bodyWith(asset.asset_id), true);
    expect(state.workspaceDocument.value?.assets).toEqual([asset]);

    state.newPictures.noteSent([asset.asset_id]);
    if (state.workspaceDocument.value === null) {
      throw new Error("expected an open document");
    }
    expect(state.newPictures.bytesFor(state.workspaceDocument.value)).toEqual({});

    state.updateItemBody("item_001", [{ heading_level: null, segments: [] }], true);
    expect(state.workspaceDocument.value?.assets).toEqual([]);

    state.newPictures.declare(asset, bytes);
    state.updateItemBody("item_001", bodyWith(asset.asset_id), true);
    if (state.workspaceDocument.value === null) {
      throw new Error("expected an open document");
    }
    expect(state.newPictures.bytesFor(state.workspaceDocument.value)).toEqual({
      [asset.asset_id]: bytes,
    });
  });
});
