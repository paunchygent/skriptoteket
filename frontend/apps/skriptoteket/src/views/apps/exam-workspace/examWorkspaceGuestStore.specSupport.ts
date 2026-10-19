/**
 * Shared fixtures for the guest exam workspace store specs.
 *
 * The store specs are split by responsibility (history/save, structural
 * commands, exports, concurrency); every split file builds its scenario
 * through this module so the fixtures stay identical.
 */

import { beforeAll, vi, type Mock } from "vitest";

import type { NativeExamDocument } from "../../../api/examWorkspace";
import { buildParentDocument } from "./examWorkspaceParentDocument.specSupport";
import {
  createGuestExamWorkspaceStore,
  type ExamWorkspaceGuestStoreDeps,
} from "./examWorkspaceGuestStore";
import type { ExamWorkspaceGuestDraftIdSource } from "./examWorkspaceGuestDraft";
import { createInMemoryExamWorkspaceGuestDraftStorage } from "./examWorkspaceGuestDraftStorage";

export type PublicApi = ExamWorkspaceGuestStoreDeps["api"];

export const DOCUMENT_ID = "00000000-0000-4000-8000-000000000001";
export const STALE_CURSOR = "99999999-9999-4999-8999-999999999999";
export const NOW = "2026-10-18T10:00:00.000Z";

/** Any current-schema document; scenarios override only the title. */
export function exam(title = "Original"): NativeExamDocument {
  return { ...buildParentDocument(), title };
}

export function pictureExam(title = "Bildprov"): NativeExamDocument {
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

export function refusedExam(): NativeExamDocument {
  const document = exam("Refused");
  return { ...document, items: [{ ...document.items[0]!, points: -1 }] };
}

export function createIds(): ExamWorkspaceGuestDraftIdSource {
  let counter = 0;
  return {
    now: () => NOW,
    uuid: () => {
      counter += 1;
      return `10000000-0000-4000-8000-${String(counter).padStart(12, "0")}`;
    },
  };
}

/** Mount the object-URL doubles once per spec file that mounts pictures. */
export function installGuestStoreObjectUrls(): void {
  beforeAll(() => {
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:picture");
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
  });
}

export type GuestStoreSetup = {
  api: PublicApi;
  ids: ExamWorkspaceGuestDraftIdSource;
  mocks: {
    addChild: Mock<PublicApi["addPublicExamWorkspaceChild"]>;
    catalog: Mock<PublicApi["getPublicExamCourseCatalog"]>;
    changeType: Mock<PublicApi["changePublicExamWorkspaceItemType"]>;
    createBlank: Mock<PublicApi["createPublicExamWorkspaceBlank"]>;
    createEmptyPart: Mock<PublicApi["createEmptyPublicExamWorkspacePart"]>;
    createParent: Mock<PublicApi["createPublicExamWorkspaceParent"]>;
    deleteChild: Mock<PublicApi["deletePublicExamWorkspaceChild"]>;
    deleteParent: Mock<PublicApi["deletePublicExamWorkspaceParent"]>;
    exportChecklist: Mock<PublicApi["getPublicExamWorkspaceExportChecklist"]>;
    exportDownload: Mock<PublicApi["downloadPublicExamWorkspaceExport"]>;
    groupItems: Mock<PublicApi["groupPublicExamWorkspaceItems"]>;
    misspellings: Mock<PublicApi["requestPublicExamWorkspaceAnswerMisspellings"]>;
    moveItem: Mock<PublicApi["movePublicExamWorkspaceItem"]>;
    reorderChildren: Mock<PublicApi["reorderPublicExamWorkspaceChildren"]>;
  };
  onLimit: Mock<() => void>;
  storage: ReturnType<typeof createInMemoryExamWorkspaceGuestDraftStorage>;
  store: ReturnType<typeof createGuestExamWorkspaceStore>;
};

export function setupGuestStore(): GuestStoreSetup {
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
  const onLimit = vi.fn();
  const store = createGuestExamWorkspaceStore({ api, ids, onLimit, storage });
  return { api, ids, mocks, onLimit, storage, store };
}

/** A second store instance over the same browser slot, like a second tab. */
export function openSecondTab(context: GuestStoreSetup): GuestStoreSetup["store"] {
  return createGuestExamWorkspaceStore({
    api: context.api,
    ids: createIds(),
    onLimit: context.onLimit,
    storage: context.storage,
  });
}

export async function startBlank(
  setup: GuestStoreSetup,
  title = "Original",
): Promise<string> {
  setup.mocks.createBlank.mockResolvedValue({
    document: exam(title),
    export_blockers: [],
  });
  return await setup.store.startBlank();
}
