/**
 * Shared fixtures for the guest exam workspace store specs.
 *
 * The store specs are split by responsibility (history/save, structural
 * commands, exports, concurrency); every split file builds its scenario
 * through this module so the fixtures stay identical.
 */

import { beforeAll, expect, vi, type Mock } from "vitest";

import type { ExamWorkspaceDocumentResponse, NativeExamDocument } from "../../../api/examWorkspace";
import { buildParentDocument } from "./examWorkspaceParentDocument.specSupport";
import {
  createGuestExamWorkspaceStore,
  type ExamWorkspaceGuestStoreDeps,
} from "./examWorkspaceGuestStore";
import type { ExamWorkspaceGuestDraftIdSource } from "./examWorkspaceGuestDraft";
import type { GuestSlotAdmission } from "./examWorkspaceStore";
import { createInMemoryExamWorkspaceGuestDraftStorage } from "./examWorkspaceGuestDraftStorage";
import {
  createInMemoryGuestEditLeaseStorage,
  type InMemoryGuestEditLeaseStorage,
} from "./examWorkspaceGuestEditLeaseMemory";

export type PublicApi = ExamWorkspaceGuestStoreDeps["api"];

/** One typed spy per public route, keyed by the real member name. */
export type GuestPublicApiMocks = {
  [Member in keyof PublicApi]: Mock<PublicApi[Member]>;
};

/**
 * Build one typed spy per public route. Every spec that fakes the guest
 * public API uses this factory, so a renamed member or a changed signature
 * fails the type check instead of hiding behind a cast.
 */
export function createGuestPublicApiMocks(): GuestPublicApiMocks {
  return {
    addPublicExamWorkspaceChild: vi.fn<PublicApi["addPublicExamWorkspaceChild"]>(),
    changePublicExamWorkspaceItemType: vi.fn<PublicApi["changePublicExamWorkspaceItemType"]>(),
    createEmptyPublicExamWorkspacePart: vi.fn<PublicApi["createEmptyPublicExamWorkspacePart"]>(),
    createPublicExamWorkspaceBlank: vi.fn<PublicApi["createPublicExamWorkspaceBlank"]>(),
    createPublicExamWorkspaceParent: vi.fn<PublicApi["createPublicExamWorkspaceParent"]>(),
    deletePublicExamWorkspaceChild: vi.fn<PublicApi["deletePublicExamWorkspaceChild"]>(),
    deletePublicExamWorkspaceParent: vi.fn<PublicApi["deletePublicExamWorkspaceParent"]>(),
    downloadPublicExamWorkspaceExport: vi.fn<PublicApi["downloadPublicExamWorkspaceExport"]>(),
    getPublicExamCourseCatalog: vi.fn<PublicApi["getPublicExamCourseCatalog"]>(),
    getPublicExamWorkspaceLimits: vi.fn<PublicApi["getPublicExamWorkspaceLimits"]>(),
    getPublicExamWorkspaceExportChecklist:
      vi.fn<PublicApi["getPublicExamWorkspaceExportChecklist"]>(),
    groupPublicExamWorkspaceItems: vi.fn<PublicApi["groupPublicExamWorkspaceItems"]>(),
    importPublicExamWorkspaceQti: vi.fn<PublicApi["importPublicExamWorkspaceQti"]>(),
    movePublicExamWorkspaceItem: vi.fn<PublicApi["movePublicExamWorkspaceItem"]>(),
    reorderPublicExamWorkspaceChildren: vi.fn<PublicApi["reorderPublicExamWorkspaceChildren"]>(),
    requestPublicExamWorkspaceAnswerMisspellings:
      vi.fn<PublicApi["requestPublicExamWorkspaceAnswerMisspellings"]>(),
  };
}

export const DOCUMENT_ID = "00000000-0000-4000-8000-000000000001";
export const STALE_CURSOR = "99999999-9999-4999-8999-999999999999";
/** The tab id the guest store specs write with; the lease slot starts empty. */
export const LEASE_TAB_ID = "20000000-0000-4000-8000-000000000001";
export const NOW = "2026-10-18T10:00:00.000Z";

/** A creation that keeps its replacement authority, writing as the spec tab. */
export function liveAdmission(tabId = LEASE_TAB_ID): GuestSlotAdmission {
  return { isLive: () => true, tabId };
}

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
    importQti: Mock<PublicApi["importPublicExamWorkspaceQti"]>;
    misspellings: Mock<PublicApi["requestPublicExamWorkspaceAnswerMisspellings"]>;
    moveItem: Mock<PublicApi["movePublicExamWorkspaceItem"]>;
    reorderChildren: Mock<PublicApi["reorderPublicExamWorkspaceChildren"]>;
  };
  onLimit: Mock<() => void>;
  storage: ReturnType<typeof createInMemoryExamWorkspaceGuestDraftStorage>;
  leaseStorage: InMemoryGuestEditLeaseStorage;
  store: ReturnType<typeof createGuestExamWorkspaceStore>;
};

export function setupGuestStore(overrides?: {
  leaseStorage?: InMemoryGuestEditLeaseStorage;
}): GuestStoreSetup {
  // The draft and the lease share one browser database, so the slot
  // replacement reads the same lease slot the stores check.
  const leaseStorage = overrides?.leaseStorage ?? createInMemoryGuestEditLeaseStorage();
  const storage = createInMemoryExamWorkspaceGuestDraftStorage({ lease: leaseStorage });
  const ids = createIds();
  const publicMocks = createGuestPublicApiMocks();
  const mocks: GuestStoreSetup["mocks"] = {
    addChild: publicMocks.addPublicExamWorkspaceChild,
    catalog: publicMocks.getPublicExamCourseCatalog,
    changeType: publicMocks.changePublicExamWorkspaceItemType,
    createBlank: publicMocks.createPublicExamWorkspaceBlank,
    createEmptyPart: publicMocks.createEmptyPublicExamWorkspacePart,
    createParent: publicMocks.createPublicExamWorkspaceParent,
    deleteChild: publicMocks.deletePublicExamWorkspaceChild,
    deleteParent: publicMocks.deletePublicExamWorkspaceParent,
    exportChecklist: publicMocks.getPublicExamWorkspaceExportChecklist,
    exportDownload: publicMocks.downloadPublicExamWorkspaceExport,
    groupItems: publicMocks.groupPublicExamWorkspaceItems,
    importQti: publicMocks.importPublicExamWorkspaceQti,
    misspellings: publicMocks.requestPublicExamWorkspaceAnswerMisspellings,
    moveItem: publicMocks.movePublicExamWorkspaceItem,
    reorderChildren: publicMocks.reorderPublicExamWorkspaceChildren,
  };
  const api: PublicApi = publicMocks;
  const onLimit = vi.fn();
  const store = createGuestExamWorkspaceStore({ api, ids, leaseStorage, onLimit, storage });
  return { api, ids, leaseStorage, mocks, onLimit, storage, store };
}

/** A second store instance over the same browser slot, like a second tab. */
export function openSecondTab(context: GuestStoreSetup): GuestStoreSetup["store"] {
  return createGuestExamWorkspaceStore({
    api: context.api,
    ids: createIds(),
    leaseStorage: context.leaseStorage,
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
  const current = await setup.storage.load();
  return await setup.store.startBlank(current?.draft.cursor ?? null, liveAdmission());
}

/**
 * Seed the slot with a retained draft C: a picture exam plus one stored
 * history step, while `tabId` holds the lease. Returns C as it reads now.
 */
export async function seedRetainedPictureDraft(
  context: GuestStoreSetup,
  tabId = LEASE_TAB_ID,
): Promise<{ lineageId: string; opened: ExamWorkspaceDocumentResponse }> {
  await context.leaseStorage.claim(tabId, Date.now());
  context.mocks.importQti.mockResolvedValueOnce({
    assets: { asset_001: new Blob(["png!"], { type: "image/png" }) },
    document: pictureExam("Keep this exam"),
    notes: [],
  });
  const lineageId = await context.store.startFromQti(
    new File(["zip"], "Prov.zip", { type: "application/zip" }),
    null,
    liveAdmission(tabId),
  );
  const loaded = await context.store.store.shared.getExamWorkspaceDocument(lineageId);
  await context.store.store.shared.storeExamWorkspaceUndoStep(lineageId, {
    afterStepId: null,
    document: { ...loaded.document, title: "Keep this exam, edited" },
    expectedCursor: loaded.history_cursor,
    tabId,
    newPictures: {},
  });
  const opened = await context.store.store.shared.getExamWorkspaceDocument(lineageId);
  return { lineageId, opened };
}

/**
 * C is intact (lineage, cursor, history step and picture bytes), and the new
 * owner `tabId` stores its first edit of `loaded` against the unchanged cursor.
 */
export async function expectRetainedAndNewOwnerStores(
  context: GuestStoreSetup,
  owner: { store: GuestStoreSetup["store"]; tabId: string },
  lineageId: string,
  loaded: ExamWorkspaceDocumentResponse,
): Promise<void> {
  const kept = await context.storage.load();
  expect(kept?.draft.lineage_id).toBe(lineageId);
  expect(kept?.draft.cursor).toBe(loaded.history_cursor);
  expect(kept?.draft.saved_document.title).toBe("Keep this exam, edited");
  expect(kept?.draft.steps).toHaveLength(1);
  expect(Object.keys(kept?.assets ?? {})).toEqual(["asset_001"]);
  const step = await owner.store.store.shared.storeExamWorkspaceUndoStep(lineageId, {
    afterStepId: loaded.history_cursor,
    document: { ...loaded.document, title: "B's first edit" },
    expectedCursor: loaded.history_cursor,
    tabId: owner.tabId,
    newPictures: {},
  });
  const stored = await context.storage.load();
  expect(stored?.draft.lineage_id).toBe(lineageId);
  expect(stored?.draft.cursor).toBe(step.history.cursor);
  expect(stored?.draft.saved_document.title).toBe("B's first edit");
  expect(Object.keys(stored?.assets ?? {})).toEqual(["asset_001"]);
}
