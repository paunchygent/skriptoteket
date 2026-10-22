/**
 * Exam workspace picture control saves: an accepted picture reaching the save.
 *
 * Expected behavior (TASK-SKRIPT-39-10-04, unit U6):
 *   - The signed-in pane carries an accepted picture to the autosave once.
 *   - The guest workspace carries it through the production
 *     `useExamWorkspaceEditing` with the guest store into the draft storage.
 *
 * The question body editor cases live in `ExamWorkspacePictureControl`; where
 * a refusal shows and clears lives in `.notices`.
 */

import { mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import type { storeExamWorkspaceUndoStep } from "../../../api/examWorkspace";
import ExamWorkspaceEditorPane from "./ExamWorkspaceEditorPane.vue";
import {
  RED_PNG_PICTURE,
  TRANSPARENT_PNG_PICTURE,
} from "./examWorkspacePictureFixtures.specSupport";
import {
  createGuestPublicApiMocks,
  createIds,
  DOCUMENT_ID,
  exam as guestExam,
  installGuestStoreObjectUrls,
  LEASE_TAB_ID,
  liveAdmission,
} from "./examWorkspaceGuestStore.specSupport";
import { createGuestExamWorkspaceStore } from "./examWorkspaceGuestStore";
import { examWorkspaceProvidersPlugin } from "./examWorkspaceProviders.specSupport";
import {
  channel,
  choosePicture,
  entryFor,
  LIMIT_BYTES,
  limitStore,
  pictureFile,
  read,
  stubTarget,
} from "./examWorkspacePictureControl.specSupport";
import { createExamWorkspacePictureService } from "./examWorkspacePictureService";
import { createExamWorkspaceGuestDraftStorage } from "./examWorkspaceGuestDraftStorage";
import { createInMemoryExamWorkspaceGuestDraftStorage } from "./examWorkspaceGuestDraftStorage";
import { createInMemoryGuestEditLeaseStorage } from "./examWorkspaceGuestEditLeaseMemory";
import { useExamWorkspaceEditing } from "./useExamWorkspaceEditing";
import { inScope, openEditing, stopScopes } from "./useExamWorkspaceEditing.history.specSupport";
import { nullRouteProjection } from "./examWorkspaceRouteProjection.specSupport";

const api = vi.hoisted(() => ({
  changeExamWorkspaceItemType: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  moveExamWorkspaceHistoryPosition: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn<typeof storeExamWorkspaceUndoStep>(),
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

let mounted: VueWrapper | null = null;

beforeEach(() => {
  for (const fn of [...Object.values(api), ...Object.values(toast)]) fn.mockReset();
});

afterEach(() => {
  mounted?.unmount();
  mounted = null;
  document.body.innerHTML = "";
  stopScopes();
  vi.unstubAllGlobals();
});

describe("ExamWorkspacePictureControl saves", () => {
  it("carries an accepted picture to the signed-in autosave from the pane", async () => {
    vi.stubGlobal(
      "createImageBitmap",
      async () => ({ width: 8, height: 8, close: () => undefined }),
    );
    const { editing } = await openEditing(api);
    const stored = () => editing.workspaceDocument.value!;
    const selected = () => stored().items.find((entry) => entry.item_id === "item_001")!;
    mounted = mount(ExamWorkspaceEditorPane, {
      attachTo: document.body,
      global: { plugins: [examWorkspaceProvidersPlugin({ store: limitStore() })] },
      props: {
        editing,
        workspaceDocument: stored(),
        examInstructionsSelected: false,
        selectedParent: null,
        selectedParentEntry: null,
        parentChildren: [],
        entries: [entryFor(selected())],
        selectedItem: selected(),
        itemEntry: entryFor(selected()),
        itemParent: null,
        itemChild: null,
        itemNotice: null,
        converting: false,
        disabled: false,
        importOpen: false,
        openDrawerShown: true,
      },
    });
    await nextTick();
    await nextTick();

    await choosePicture(mounted, pictureFile(TRANSPARENT_PNG_PICTURE, "sparad.png"));

    await vi.waitFor(() => expect(api.storeExamWorkspaceUndoStep).toHaveBeenCalled());
    const sent = api.storeExamWorkspaceUndoStep.mock.calls[0]![1];
    const assetIds = Object.keys(sent.newPictures);
    expect(assetIds).toHaveLength(1);
    expect(sent.newPictures[assetIds[0]!]!).toBeInstanceOf(Blob);
    expect(sent.document.assets.map((entry) => entry.asset_id)).toEqual(assetIds);
    expect(stored().assets.map((entry) => entry.asset_id)).toEqual(assetIds);
  });

  it("carries an accepted picture to the guest draft store through the guest editing session", async () => {
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

    const service = createExamWorkspacePictureService({
      document: () => editing.workspaceDocument.value,
      newPictures: editing.newPictures,
      canEdit: () => true,
      opening: () => editing.openExam.value,
      isOpen: editing.isOpen,
      maxExamBytes: async () => LIMIT_BYTES,
      read,
    });
    const { placePicture, target } = stubTarget();
    await service.add(target, [pictureFile(RED_PNG_PICTURE, "gast.png")]);
    expect(placePicture).toHaveBeenCalledTimes(1);
    const assetId = placePicture.mock.calls[0]![0] as string;
    expect(assetId).toMatch(/^asset_[0-9a-f]{16}$/);

    editing.updateItemBody("item_001", [
      { heading_level: null, segments: [{ kind: "asset", asset_id: assetId }] },
    ], true);
    expect(await editing.save()).toBe(true);

    const draft = await storage.load();
    expect(draft?.assets[assetId]).toBeInstanceOf(Blob);
    expect(editing.workspaceDocument.value?.assets.map((entry) => entry.asset_id)).toContain(assetId);
    expect(editing.assetUrls.value[assetId]).toBe("blob:picture");
  });
});
