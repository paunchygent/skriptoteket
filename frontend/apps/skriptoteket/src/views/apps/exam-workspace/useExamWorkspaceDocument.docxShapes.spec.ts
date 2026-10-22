/**
 * Word shapes on a picture's asset in the open exam (TASK-SKRIPT-39-04-22, unit 4b, D10).
 *
 * Expected behavior:
 *   A picture's asset carries its original Word shapes in `docx_shapes`. When the
 *   teacher replaces the picture through the picture service or removes it from
 *   the text, the asset record leaves the document with its shapes, unless
 *   another reference still uses it; the replacement is a new asset that carries
 *   no shapes. An asset the teacher does not touch keeps its shapes through
 *   other edits.
 */

import { flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { effectScope } from "vue";

import type {
  ExamWorkspaceDocumentResponse,
  NativeExamAsset,
  NativeExamBodyParagraph,
} from "../../../api/examWorkspace";
import { serverExamWorkspaceStore } from "./examWorkspaceStore";
import { createSyncFence } from "./examWorkspaceSyncFence";
import { readPicture } from "./examWorkspacePictureIntake";
import { createExamWorkspacePictureService } from "./examWorkspacePictureService";
import {
  LIMIT,
  pictureFile,
  stubTarget,
} from "./examWorkspacePictureService.specSupport";
import {
  RED_PNG_PICTURE,
  TRANSPARENT_PNG_PICTURE,
} from "./examWorkspacePictureFixtures.specSupport";
import { useExamWorkspaceDocument } from "./useExamWorkspaceDocument";
import { buildResponse } from "./useExamWorkspaceDocument.specSupport";

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

const SHAPES = '<w:drawing xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>';

/** The imported picture: the transparent fixture, drawn from Word shapes. */
const DRAWN: NativeExamAsset = { ...TRANSPARENT_PNG_PICTURE.asset, docx_shapes: SHAPES };
const REPLACEMENT_FILE = RED_PNG_PICTURE;

beforeAll(() => {
  let next = 0;
  vi.spyOn(URL, "createObjectURL").mockImplementation(() => `blob:mock-${(next += 1)}`);
  vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
});

beforeEach(() => {
  setActivePinia(createPinia());
  apiMocks.getExamWorkspaceDocument.mockReset();
});

function bodyWith(assetId: string): NativeExamBodyParagraph[] {
  return [{ heading_level: null, segments: [{ kind: "asset", asset_id: assetId }] }];
}

/** An opened exam whose question 1 shows the drawn picture, and optionally its instruction too. */
function drawnResponse(options: { alsoInInstructions: boolean }): ExamWorkspaceDocumentResponse {
  const base = buildResponse();
  const item = { ...base.document.items[0]!, body: bodyWith(DRAWN.asset_id) };
  const document = {
    ...base.document,
    assets: [DRAWN],
    instructions: options.alsoInInstructions ? bodyWith(DRAWN.asset_id) : [],
    items: [item],
  };
  return { ...base, document, saved_document: document };
}

async function openDrawn(options: { alsoInInstructions: boolean }) {
  apiMocks.getExamWorkspaceDocument.mockResolvedValue(drawnResponse(options));
  const fence = createSyncFence();
  const state = effectScope().run(() =>
    useExamWorkspaceDocument({
      getFence: () => fence,
      onEdit: () => undefined,
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
  return state;
}

type DocumentState = Awaited<ReturnType<typeof openDrawn>>;

/**
 * The real picture service over the open document: `readPicture` hashes the chosen
 * file, the registry declares it, and the selected picture's body is rewritten as
 * the editor's `placePicture` does.
 */
function replaceDrawnPicture(state: DocumentState) {
  const target = stubTarget();
  target.selectedPictureId.value = DRAWN.asset_id;
  target.placePicture.mockImplementation((assetId: string) => {
    state.updateItemBody("item_001", bodyWith(assetId), true);
  });
  const service = createExamWorkspacePictureService({
    document: () => state.workspaceDocument.value,
    newPictures: state.newPictures,
    canEdit: () => true,
    opening: () => ({ lineageId: "lineage-1" }),
    isOpen: () => true,
    maxExamBytes: async () => LIMIT,
    read: (file, document, options) =>
      readPicture(file, document, options, {
        decodeSize: async () => ({ width: 1, height: 1 }),
        digest: (bytes) => crypto.subtle.digest("SHA-256", bytes),
      }),
  });
  return { service, target };
}

describe("a picture's Word shapes in the open exam", () => {
  it("opens with the drawn asset's shapes", async () => {
    const state = await openDrawn({ alsoInInstructions: false });

    expect(state.workspaceDocument.value?.assets).toEqual([DRAWN]);
  });

  it("replacing the picture removes the old asset with its shapes and the new asset carries none", async () => {
    const state = await openDrawn({ alsoInInstructions: false });
    const { service, target } = replaceDrawnPicture(state);

    await service.add(target, [pictureFile(REPLACEMENT_FILE)]);

    const assets = state.workspaceDocument.value?.assets ?? [];
    expect(assets).toEqual([REPLACEMENT_FILE.asset]);
    expect(assets.some((asset) => asset.docx_shapes !== undefined && asset.docx_shapes !== null)).toBe(
      false,
    );
    expect(JSON.stringify(state.workspaceDocument.value)).not.toContain("w:drawing");
  });

  it("removing the picture removes its asset with its shapes", async () => {
    const state = await openDrawn({ alsoInInstructions: false });

    state.updateItemBody("item_001", [{ heading_level: null, segments: [] }], true);

    expect(state.workspaceDocument.value?.assets).toEqual([]);
    expect(JSON.stringify(state.workspaceDocument.value)).not.toContain("w:drawing");
  });

  it("keeps the shapes for a second reference when one reference is replaced", async () => {
    const state = await openDrawn({ alsoInInstructions: true });
    const { service, target } = replaceDrawnPicture(state);

    await service.add(target, [pictureFile(REPLACEMENT_FILE)]);

    expect(state.workspaceDocument.value?.assets).toEqual([DRAWN, REPLACEMENT_FILE.asset]);
    expect(state.workspaceDocument.value?.assets[0]?.docx_shapes).toBe(SHAPES);
    expect(state.workspaceDocument.value?.assets[1]?.docx_shapes).toBeUndefined();
  });

  it("keeps the shapes for a second reference when one reference is removed", async () => {
    const state = await openDrawn({ alsoInInstructions: true });

    state.updateItemBody("item_001", [{ heading_level: null, segments: [] }], true);

    expect(state.workspaceDocument.value?.assets).toEqual([DRAWN]);
  });

  it("keeps an untouched picture's shapes through an edit elsewhere", async () => {
    const state = await openDrawn({ alsoInInstructions: false });

    state.setExamInstructions(
      [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "Läs noga." }] }],
      true,
    );

    expect(state.workspaceDocument.value?.assets).toEqual([DRAWN]);
  });

  it("removing the picture and adding the same file again yields an asset without shapes", async () => {
    const state = await openDrawn({ alsoInInstructions: false });
    state.updateItemBody("item_001", [{ heading_level: null, segments: [] }], true);
    const { service, target } = replaceDrawnPicture(state);
    target.selectedPictureId.value = null;

    await service.add(target, [pictureFile(TRANSPARENT_PNG_PICTURE)]);

    expect(state.workspaceDocument.value?.assets).toEqual([TRANSPARENT_PNG_PICTURE.asset]);
    expect(state.workspaceDocument.value?.assets[0]?.docx_shapes).toBeUndefined();
  });
});
