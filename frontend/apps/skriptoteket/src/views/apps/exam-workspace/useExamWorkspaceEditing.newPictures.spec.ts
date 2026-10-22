/**
 * Exam workspace editing session: a new picture travels from the editor
 * document to the autosave (TASK-SKRIPT-39-10-04, unit U7).
 *
 * Expected behavior:
 *   A picture declared through the real `useExamWorkspaceEditing` reaches
 *   the store exactly once: signed-in as `newPictures` on the
 *   `storeExamWorkspaceUndoStep` call, guest as a Blob in the stored
 *   draft's pictures. No registry or history doubles; transport is the
 *   named double of the server's step store signed-in, and the production
 *   in-memory guest bank in guest mode.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { NativeExamItem } from "../../../api/examWorkspace";
import { useExamWorkspaceEditing } from "./useExamWorkspaceEditing";
import { nullRouteProjection } from "./examWorkspaceRouteProjection.specSupport";
import { inScope, openEditing, stopScopes } from "./useExamWorkspaceEditing.history.specSupport";
import type { GuestEditLeaseChannel } from "./examWorkspaceGuestEditLease";
import { createGuestExamWorkspaceStore } from "./examWorkspaceGuestStore";
import {
  createExamWorkspaceGuestDraftStorage,
  createInMemoryExamWorkspaceGuestDraftStorage,
} from "./examWorkspaceGuestDraftStorage";
import { createInMemoryGuestEditLeaseStorage } from "./examWorkspaceGuestEditLeaseMemory";
import {
  createGuestPublicApiMocks,
  createIds,
  DOCUMENT_ID,
  exam as guestExam,
  installGuestStoreObjectUrls,
  LEASE_TAB_ID,
  liveAdmission,
} from "./examWorkspaceGuestStore.specSupport";
import { TRANSPARENT_PNG_PICTURE } from "./examWorkspacePictureFixtures.specSupport";

const api = vi.hoisted(() => ({
  changeExamWorkspaceItemType: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  moveExamWorkspaceHistoryPosition: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
}));
const toast = vi.hoisted(() => ({ failure: vi.fn(), warning: vi.fn() }));

vi.mock("../../../api/examWorkspace", async (original) => ({
  ...(await original<typeof import("../../../api/examWorkspace")>()),
  ...api,
}));
vi.mock("../../../api/examWorkspaceStructureCommands", async (original) => ({
  ...(await original<typeof import("../../../api/examWorkspaceStructureCommands")>()),
  changeExamWorkspaceItemType: api.changeExamWorkspaceItemType,
}));
vi.mock("../../../composables/useToast", () => ({ useToast: () => toast }));

installGuestStoreObjectUrls();

beforeEach(() => {
  for (const fn of [...Object.values(api), ...Object.values(toast)]) fn.mockReset();
});

afterEach(() => {
  stopScopes();
});

const PICTURE = TRANSPARENT_PNG_PICTURE.asset.asset_id;

function pictureBody(assetId: string): NativeExamItem["body"] {
  return [{ heading_level: null, segments: [{ kind: "asset", asset_id: assetId }] }];
}

function textBody(): NativeExamItem["body"] {
  return [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "Utan bild" }] }];
}

/** A no-op guest lease channel: takeover answers arrive only via the heartbeat poll. */
function channel(): GuestEditLeaseChannel {
  return {
    addEventListener() {},
    close() {},
    postMessage() {},
    removeEventListener() {},
  };
}

describe("a declared picture reaches the signed-in autosave once", () => {
  it("carries the picture's bytes on the first store and nothing on the next", async () => {
    const { editing } = await openEditing(api);
    const blob = TRANSPARENT_PNG_PICTURE.blob();
    const asset = TRANSPARENT_PNG_PICTURE.asset;

    editing.newPictures.declare(asset, blob);
    editing.updateItemBody("item_001", pictureBody(PICTURE), true);

    await vi.waitFor(() => expect(api.storeExamWorkspaceUndoStep).toHaveBeenCalledTimes(1));
    const first = api.storeExamWorkspaceUndoStep.mock.calls[0]![1];
    expect(first.newPictures).toEqual({ [PICTURE]: blob });
    expect(first.document.assets).toContainEqual(asset);

    editing.setTitle("With picture, edited");
    expect(await editing.save()).toBe(true);

    expect(api.storeExamWorkspaceUndoStep).toHaveBeenCalledTimes(2);
    expect(api.storeExamWorkspaceUndoStep.mock.calls[1]![1].newPictures).toEqual({});
  });

  it("carries the picture again when the first store fails", async () => {
    const { editing } = await openEditing(api);
    api.storeExamWorkspaceUndoStep.mockRejectedValueOnce(new Error("offline"));
    const blob = TRANSPARENT_PNG_PICTURE.blob();

    editing.newPictures.declare(TRANSPARENT_PNG_PICTURE.asset, blob);
    editing.updateItemBody("item_001", pictureBody(PICTURE), true);

    expect(await editing.save()).toBe(true);

    const calls = api.storeExamWorkspaceUndoStep.mock.calls;
    expect(calls).toHaveLength(2);
    expect(calls[0]![1].newPictures).toEqual({ [PICTURE]: blob });
    expect(calls[1]![1].newPictures).toEqual({ [PICTURE]: blob });
  });

  it("sends nothing when the picture is removed before the autosave runs", async () => {
    const { editing } = await openEditing(api);
    const blob = TRANSPARENT_PNG_PICTURE.blob();

    editing.newPictures.declare(TRANSPARENT_PNG_PICTURE.asset, blob);
    editing.updateItemBody("item_001", pictureBody(PICTURE), false);
    editing.updateItemBody("item_001", textBody(), false);

    expect(await editing.save()).toBe(true);

    expect(api.storeExamWorkspaceUndoStep).toHaveBeenCalledTimes(1);
    const sent = api.storeExamWorkspaceUndoStep.mock.calls[0]![1];
    expect(sent.newPictures).toEqual({});
    expect(sent.document.assets).toEqual([]);
    expect(editing.workspaceDocument.value?.assets).toEqual([]);
  });

  it("resends a picture re-added after undo and branching dropped its retained bytes", async () => {
    const { editing } = await openEditing(api);
    const blob = TRANSPARENT_PNG_PICTURE.blob();
    const asset = TRANSPARENT_PNG_PICTURE.asset;

    editing.newPictures.declare(asset, blob);
    editing.updateItemBody("item_001", pictureBody(PICTURE), true);
    expect(await editing.save()).toBe(true);
    await vi.waitFor(() => expect(api.storeExamWorkspaceUndoStep).toHaveBeenCalledTimes(1));
    expect(api.storeExamWorkspaceUndoStep.mock.calls[0]![1].newPictures).toEqual({ [PICTURE]: blob });

    await editing.history.undo();
    expect(editing.workspaceDocument.value?.assets).toEqual([]);

    editing.updateItemBody("item_001", textBody(), true);
    expect(await editing.save()).toBe(true);
    const branched = api.storeExamWorkspaceUndoStep.mock.calls[
      api.storeExamWorkspaceUndoStep.mock.calls.length - 1
    ]![1];
    expect(branched.newPictures).toEqual({});
    expect(branched.document.assets).toEqual([]);

    editing.newPictures.declare(asset, blob);
    editing.updateItemBody("item_001", pictureBody(PICTURE), true);
    expect(await editing.save()).toBe(true);

    const readded = api.storeExamWorkspaceUndoStep.mock.calls[
      api.storeExamWorkspaceUndoStep.mock.calls.length - 1
    ]![1];
    expect(readded.document.assets).toContainEqual(asset);
    expect(readded.newPictures).toEqual({ [PICTURE]: blob });
  });
});

describe("a declared picture reaches the guest draft store", () => {
  it("writes the Blob into the stored draft and resolves its URL", async () => {
    // The production route (ExamWorkspaceGuestHost): the store writes
    // through the factory, whose snapshot drops the editor's reactive
    // proxies the way IndexedDB would, instead of the raw in-memory port.
    const leaseStorage = createInMemoryGuestEditLeaseStorage();
    const publicMocks = createGuestPublicApiMocks();
    const storage = createExamWorkspaceGuestDraftStorage({
      port: createInMemoryExamWorkspaceGuestDraftStorage({ lease: leaseStorage }),
    });
    const guest = createGuestExamWorkspaceStore({
      api: publicMocks,
      ids: createIds(),
      leaseStorage,
      onLimit: vi.fn(),
      storage,
    });
    publicMocks.createPublicExamWorkspaceBlank.mockResolvedValue({
      document: guestExam("Original"),
      export_blockers: [],
    });
    await guest.startBlank(null, liveAdmission());
    const editing = inScope(() =>
      useExamWorkspaceEditing(guest.store, nullRouteProjection(), {
        guestStorage: leaseStorage,
        openGuestChannel: channel,
        tabId: LEASE_TAB_ID,
      }),
    );
    const opened = await guest.store.shared.getExamWorkspaceDocument(DOCUMENT_ID);
    editing.applyCommandResponse(opened);
    await vi.waitFor(() => expect(editing.editingLocked.value).toBe(false));

    const blob = TRANSPARENT_PNG_PICTURE.blob();
    const asset = TRANSPARENT_PNG_PICTURE.asset;
    editing.newPictures.declare(asset, blob);
    editing.updateItemBody("item_001", pictureBody(PICTURE), true);
    expect(await editing.save()).toBe(true);

    const stored = await storage.load();
    expect(stored?.assets[PICTURE]).toBe(blob);
    expect(editing.workspaceDocument.value?.assets.map((asset) => asset.asset_id)).toContain(PICTURE);
    expect(editing.assetUrls.value[PICTURE]).toBe("blob:picture");
  });

  it("keeps the re-added picture's bytes after undo and branching collected them", async () => {
    const leaseStorage = createInMemoryGuestEditLeaseStorage();
    const publicMocks = createGuestPublicApiMocks();
    const storage = createExamWorkspaceGuestDraftStorage({
      port: createInMemoryExamWorkspaceGuestDraftStorage({ lease: leaseStorage }),
    });
    const guest = createGuestExamWorkspaceStore({
      api: publicMocks,
      ids: createIds(),
      leaseStorage,
      onLimit: vi.fn(),
      storage,
    });
    publicMocks.createPublicExamWorkspaceBlank.mockResolvedValue({
      document: guestExam("Original"),
      export_blockers: [],
    });
    await guest.startBlank(null, liveAdmission());
    const editing = inScope(() =>
      useExamWorkspaceEditing(guest.store, nullRouteProjection(), {
        guestStorage: leaseStorage,
        openGuestChannel: channel,
        tabId: LEASE_TAB_ID,
      }),
    );
    const opened = await guest.store.shared.getExamWorkspaceDocument(DOCUMENT_ID);
    editing.applyCommandResponse(opened);
    await vi.waitFor(() => expect(editing.editingLocked.value).toBe(false));

    const blob = TRANSPARENT_PNG_PICTURE.blob();
    const asset = TRANSPARENT_PNG_PICTURE.asset;
    editing.newPictures.declare(asset, blob);
    editing.updateItemBody("item_001", pictureBody(PICTURE), true);
    expect(await editing.save()).toBe(true);
    expect((await storage.load())?.assets[PICTURE]).toBe(blob);

    await editing.history.undo();
    expect(editing.workspaceDocument.value?.assets).toEqual([]);

    editing.updateItemBody("item_001", textBody(), true);
    expect(await editing.save()).toBe(true);
    expect((await storage.load())?.assets[PICTURE]).toBeUndefined();

    editing.newPictures.declare(asset, blob);
    editing.updateItemBody("item_001", pictureBody(PICTURE), true);
    expect(await editing.save()).toBe(true);

    const stored = await storage.load();
    expect(stored?.assets[PICTURE]).toBe(blob);
    expect(editing.workspaceDocument.value?.assets).toContainEqual(asset);
  });
});
