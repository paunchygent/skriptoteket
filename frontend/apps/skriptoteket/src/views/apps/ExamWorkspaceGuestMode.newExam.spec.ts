/**
 * Guest mode inside the shared exam workspace: Nytt prov (TASK-SKRIPT-40-04-21, D8, D9).
 *
 * Expected behavior:
 *   With no open draft, or an empty one, "Nytt prov" starts the guest draft
 *   at once with no confirm. With a draft that has content it first shows
 *   the D9 confirm; Avbryt closes it and leaves the draft unchanged, Ersätt
 *   starts the new draft and opens it. The Öppna drawer has no "Tomt prov"
 *   control, and the empty state names Nytt prov first.
 */

import { flushPromises } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { ref } from "vue";

import type { NativeExamDocument } from "../../api/examWorkspace";
import type { PublicExamWorkspaceCommandResult } from "../../api/publicExamWorkspace";
import { useToastStore } from "../../stores/toast";
import { createTestRouter, mountWithContext } from "../../test/utils";
import ExamWorkspaceView from "./ExamWorkspaceView.vue";
import {
  blankDocument,
  installGuestModeObjectUrls,
  keylessItem,
  mountGuestView,
  resetGuestModeTestState,
  setupGuest,
  type TeacherApiMocks,
} from "./ExamWorkspaceGuestMode.specSupport";
import { createGuestExamWorkspaceStore } from "./exam-workspace/examWorkspaceGuestStore";
import type { ExamWorkspaceStore } from "./exam-workspace/examWorkspaceStore";
import { createInMemoryGuestEditLeaseStorage } from "./exam-workspace/examWorkspaceGuestEditLeaseMemory";
import { createIds } from "./exam-workspace/examWorkspaceGuestStore.specSupport";
import { deferred } from "./exam-workspace/useExamWorkspaceSyncGate.specSupport";
import { NEW_EXAM_FAILURE_COPY } from "./exam-workspace/examWorkspaceNewExam";
import {
  EXAM_WORKSPACE_LAYOUT_KEY,
  type ExamWorkspaceLayout,
} from "./exam-workspace/useExamWorkspaceLayout";
import { PENDING_SAVE_COPY } from "./exam-workspace/useExamWorkspaceSaveStatus";

const teacherMocks: TeacherApiMocks = vi.hoisted(() => ({
  addExamWorkspaceChild: vi.fn(),
  changeExamWorkspaceItemType: vi.fn(),
  copyExamWorkspaceDocument: vi.fn(),
  createEmptyExamWorkspacePart: vi.fn(),
  createExamWorkspaceParent: vi.fn(),
  createExamWorkspaceBlank: vi.fn(),
  deleteExamWorkspaceChild: vi.fn(),
  deleteExamWorkspaceParent: vi.fn(),
  downloadExamWorkspaceExport: vi.fn(),
  examWorkspaceAssetUrl: vi.fn(),
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamCourseCatalog: vi.fn(),
  getExamCourseContent: vi.fn(),
  getExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceContentSuggestions: vi.fn(),
  getExamWorkspaceConversionStatus: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceExportChecklist: vi.fn(),
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  groupExamWorkspaceItems: vi.fn(),
  importExamWorkspaceDigiExam: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  moveExamWorkspaceItem: vi.fn(),
  reorderExamWorkspaceChildren: vi.fn(),
  requestExamWorkspaceAnswerKeySuggestions: vi.fn(),
  requestExamWorkspaceAnswerMisspellings: vi.fn(),
  requestExamWorkspaceContentSuggestions: vi.fn(),
  retryExamWorkspaceItem: vi.fn(),
  saveExamWorkspaceDocument: vi.fn(),
  saveExamWorkspaceExport: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
  updateExamListOrdering: vi.fn(),
}));

vi.mock("../../api/examWorkspace", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../api/examWorkspace")>()),
  ...teacherMocks,
}));

vi.mock("../../api/examWorkspaceStructureCommands", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../api/examWorkspaceStructureCommands")>()),
  addExamWorkspaceChild: teacherMocks.addExamWorkspaceChild,
  changeExamWorkspaceItemType: teacherMocks.changeExamWorkspaceItemType,
  createEmptyExamWorkspacePart: teacherMocks.createEmptyExamWorkspacePart,
  createExamWorkspaceParent: teacherMocks.createExamWorkspaceParent,
  deleteExamWorkspaceChild: teacherMocks.deleteExamWorkspaceChild,
  deleteExamWorkspaceParent: teacherMocks.deleteExamWorkspaceParent,
  groupExamWorkspaceItems: teacherMocks.groupExamWorkspaceItems,
  moveExamWorkspaceItem: teacherMocks.moveExamWorkspaceItem,
  reorderExamWorkspaceChildren: teacherMocks.reorderExamWorkspaceChildren,
}));

vi.mock("../../api/vault", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../api/vault")>()),
  renameVaultFile: vi.fn(),
}));

installGuestModeObjectUrls();
resetGuestModeTestState(teacherMocks);

const EMPTY_STATE_COPY =
  "Skapa ett nytt prov, öppna ett sparat prov eller importera från Word eller DigiExam.";
const CONFIRM_COPY = "Det öppna provet ersätts av ett nytt. Exportera det först om du vill behålla det.";

/** The true blank shape: no title and one question with nothing in it. */
function emptyGuestDocument(): NativeExamDocument {
  return {
    ...blankDocument(),
    header: { tags: [] },
    instructions: [],
    items: [
      {
        ...keylessItem(1, "single_choice"),
        answer_key: { correct_choice_ids: [], match_pairs: [], origin: "absent" },
        body: [],
        choices: [],
      },
    ],
    title: "",
  };
}

describe("ExamWorkspaceView guest mode Nytt prov", () => {
  it("starts a new exam at once when no draft is open, with no confirm", async () => {
    const { guest, publicMocks } = setupGuest();
    const wrapper = await mountGuestView(guest.store);

    await wrapper.get('[data-test="exam-workspace-new-exam"]').trigger("click");
    await flushPromises();

    expect(publicMocks.createPublicExamWorkspaceBlank).toHaveBeenCalledTimes(1);
    expect(wrapper.find('[data-test="exam-workspace-new-exam-confirm"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-empty"]').exists()).toBe(false);
    wrapper.unmount();
  });

  it("starts a new exam at once over an empty draft, with no confirm", async () => {
    const { guest, publicMocks } = setupGuest();
    publicMocks.createPublicExamWorkspaceBlank.mockResolvedValue({
      document: emptyGuestDocument(),
      export_blockers: [],
    });
    const wrapper = await mountGuestView(guest.store);

    await wrapper.get('[data-test="exam-workspace-new-exam"]').trigger("click");
    await flushPromises();
    expect(wrapper.find('[data-test="exam-workspace-new-exam-confirm"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-empty"]').exists()).toBe(false);

    await wrapper.get('[data-test="exam-workspace-new-exam"]').trigger("click");
    await flushPromises();

    expect(publicMocks.createPublicExamWorkspaceBlank).toHaveBeenCalledTimes(2);
    expect(wrapper.find('[data-test="exam-workspace-new-exam-confirm"]').exists()).toBe(false);
    wrapper.unmount();
  });

  it("confirms before replacing a draft that has content", async () => {
    const { guest, publicMocks } = setupGuest();
    const wrapper = await mountGuestView(guest.store);

    await wrapper.get('[data-test="exam-workspace-new-exam"]').trigger("click");
    await flushPromises();
    expect(publicMocks.createPublicExamWorkspaceBlank).toHaveBeenCalledTimes(1);
    expect(wrapper.find('[data-test="exam-workspace-new-exam-confirm"]').exists()).toBe(false);

    await wrapper.get('[data-test="exam-workspace-new-exam"]').trigger("click");
    await flushPromises();

    const confirm = wrapper.get('[data-test="exam-workspace-new-exam-confirm"]');
    expect(confirm.text()).toContain("Nytt prov");
    expect(confirm.text()).toContain(CONFIRM_COPY);
    expect(
      wrapper.get('[data-test="exam-workspace-new-exam-confirm-cancel"]').text(),
    ).toBe("Avbryt");
    expect(
      wrapper.get('[data-test="exam-workspace-new-exam-confirm-replace"]').text(),
    ).toBe("Ersätt");
    expect(publicMocks.createPublicExamWorkspaceBlank).toHaveBeenCalledTimes(1);
    wrapper.unmount();
  });

  it("Avbryt closes the confirm and leaves the draft unchanged", async () => {
    const { guest, publicMocks } = setupGuest();
    const wrapper = await mountGuestView(guest.store);

    await wrapper.get('[data-test="exam-workspace-new-exam"]').trigger("click");
    await flushPromises();
    await wrapper.get('[data-test="exam-workspace-new-exam"]').trigger("click");
    await flushPromises();
    expect(wrapper.find('[data-test="exam-workspace-new-exam-confirm"]').exists()).toBe(true);

    await wrapper.get('[data-test="exam-workspace-new-exam-confirm-cancel"]').trigger("click");
    await flushPromises();

    expect(wrapper.find('[data-test="exam-workspace-new-exam-confirm"]').exists()).toBe(false);
    expect(publicMocks.createPublicExamWorkspaceBlank).toHaveBeenCalledTimes(1);
    expect(wrapper.find('[data-test="exam-workspace-empty"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-title"]').text()).toBe("Nytt prov");
    wrapper.unmount();
  });

  it("Ersätt starts the new draft and opens it", async () => {
    const { guest, publicMocks } = setupGuest();
    const wrapper = await mountGuestView(guest.store);

    await wrapper.get('[data-test="exam-workspace-new-exam"]').trigger("click");
    await flushPromises();
    await wrapper.get('[data-test="exam-workspace-new-exam"]').trigger("click");
    await flushPromises();
    await wrapper.get('[data-test="exam-workspace-new-exam-confirm-replace"]').trigger("click");
    await flushPromises();

    expect(publicMocks.createPublicExamWorkspaceBlank).toHaveBeenCalledTimes(2);
    expect(wrapper.find('[data-test="exam-workspace-new-exam-confirm"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-empty"]').exists()).toBe(false);
    wrapper.unmount();
  });

  it("names Nytt prov first in the empty state", async () => {
    const { guest } = setupGuest();
    const wrapper = await mountGuestView(guest.store);

    expect(wrapper.find('[data-test="exam-workspace-empty"]').text()).toContain(EMPTY_STATE_COPY);
    wrapper.unmount();
  });

  it("shows no Tomt prov control in the Öppna drawer", async () => {
    const { guest } = setupGuest();
    const wrapper = await mountGuestView(guest.store);

    expect(wrapper.find('[data-test="exam-workspace-drawer-open"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-workspace-guest-blank"]').exists()).toBe(false);
    expect(wrapper.text()).not.toContain("Tomt prov");
    wrapper.unmount();
  });
});

describe("ExamWorkspaceView guest mode Nytt prov protected replacement", () => {
  /**
   * The shared `mountGuestView` owns its pinia, so a toast spy needs a
   * mount that pins the same pinia as active first.
   */
  async function mountPinnedGuestView(store: ExamWorkspaceStore) {
    const pinia = createPinia();
    setActivePinia(pinia);
    const layout = ref<ExamWorkspaceLayout>("desktop");
    const wrapper = mountWithContext(ExamWorkspaceView, {
      props: { store },
      global: {
        plugins: [pinia, createTestRouter()],
        provide: { [EXAM_WORKSPACE_LAYOUT_KEY]: layout },
      },
    });
    await flushPromises();
    return wrapper;
  }

  it("locks the editor while the blank response is pending, refuses the attempted edit and opens the new exam", async () => {
    const { guest, publicMocks, storage } = setupGuest();
    publicMocks.createPublicExamWorkspaceBlank.mockResolvedValue({
      document: emptyGuestDocument(),
      export_blockers: [],
    });
    const wrapper = await mountGuestView(guest.store);

    await wrapper.get('[data-test="exam-workspace-new-exam"]').trigger("click");
    await flushPromises();
    expect(wrapper.find('[data-test="exam-workspace-empty"]').exists()).toBe(false);

    await wrapper.get('[data-test="exam-workspace-row-item_001"]').trigger("click");
    await flushPromises();

    const blank = deferred<PublicExamWorkspaceCommandResult>();
    publicMocks.createPublicExamWorkspaceBlank.mockReturnValueOnce(blank.promise);
    await wrapper.get('[data-test="exam-workspace-new-exam"]').trigger("click");
    await flushPromises();
    expect(publicMocks.createPublicExamWorkspaceBlank).toHaveBeenCalledTimes(2);

    // The D9 check saw an empty draft, so there is no confirm; the pending
    // creation locks the editor instead of leaving the doomed draft writable.
    expect(wrapper.find('[data-test="exam-workspace-new-exam-confirm"]').exists()).toBe(false);
    expect(
      wrapper.get('[data-test="exam-workspace-item-points-input"]').attributes("disabled"),
    ).toBeDefined();
    expect(wrapper.get('[data-test="exam-workspace-rename"]').attributes("disabled")).toBeDefined();

    await wrapper.get('[data-test="exam-workspace-item-points-input"]').setValue("5");
    await flushPromises();
    const kept = await storage.load();
    expect(
      kept?.draft.saved_document.items.find((item) => item.item_id === "item_001")?.points,
    ).toBe(2);

    blank.resolve({ document: emptyGuestDocument(), export_blockers: [] });
    await flushPromises();
    expect(wrapper.find('[data-test="exam-workspace-empty"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-new-exam-confirm"]').exists()).toBe(false);
    wrapper.unmount();
  });

  it("keeps the stored content-bearing draft when another tab stores before the slot is replaced", async () => {
    const { guest, publicMocks, storage } = setupGuest();
    publicMocks.createPublicExamWorkspaceBlank.mockResolvedValue({
      document: emptyGuestDocument(),
      export_blockers: [],
    });
    const wrapper = await mountPinnedGuestView(guest.store);
    const failure = vi.spyOn(useToastStore(), "failure");

    await wrapper.get('[data-test="exam-workspace-new-exam"]').trigger("click");
    await flushPromises();
    const checked = await storage.load();
    if (!checked) {
      throw new Error("expected the empty draft");
    }

    const blank = deferred<PublicExamWorkspaceCommandResult>();
    publicMocks.createPublicExamWorkspaceBlank.mockReturnValueOnce(blank.promise);
    await wrapper.get('[data-test="exam-workspace-new-exam"]').trigger("click");
    await flushPromises();
    expect(publicMocks.createPublicExamWorkspaceBlank).toHaveBeenCalledTimes(2);

    // Another tab stores content while the blank response is in flight: the
    // D9 check read the empty draft, but the slot no longer holds it.
    const other = createGuestExamWorkspaceStore({
      api: publicMocks,
      ids: createIds(),
      leaseStorage: createInMemoryGuestEditLeaseStorage(),
      onLimit: () => undefined,
      storage,
    });
    await other.store.shared.storeExamWorkspaceUndoStep(checked.draft.lineage_id, {
      afterStepId: null,
      document: { ...emptyGuestDocument(), title: "Behåll mig" },
      expectedCursor: checked.draft.cursor,
      tabId: "other-tab",
    });

    blank.resolve({ document: emptyGuestDocument(), export_blockers: [] });
    await flushPromises();

    expect(failure).toHaveBeenCalledWith(NEW_EXAM_FAILURE_COPY);
    const stored = await storage.load();
    expect(stored?.draft.saved_document.title).toBe("Behåll mig");
    expect(stored?.draft.cursor).not.toBe(checked.draft.cursor);
    expect(publicMocks.createPublicExamWorkspaceBlank).toHaveBeenCalledTimes(2);
    expect(wrapper.find('[data-test="exam-workspace-new-exam-confirm"]').exists()).toBe(false);
    wrapper.unmount();
  });

  it("Ersätt re-checks the gate: a blocked gate toasts and replaces nothing", async () => {
    const { guest, publicMocks } = setupGuest();
    const wrapper = await mountPinnedGuestView(guest.store);
    const failure = vi.spyOn(useToastStore(), "failure");

    await wrapper.get('[data-test="exam-workspace-new-exam"]').trigger("click");
    await flushPromises();
    await wrapper.get('[data-test="exam-workspace-new-exam"]').trigger("click");
    await flushPromises();
    expect(wrapper.find('[data-test="exam-workspace-new-exam-confirm"]').exists()).toBe(true);

    // An edit after the confirm blocks the gate: the open exam is not saved.
    await wrapper.get('[data-test="exam-workspace-row-item_001"]').trigger("click");
    await wrapper.get('[data-test="exam-workspace-item-points-input"]').setValue("5");
    await flushPromises();

    await wrapper.get('[data-test="exam-workspace-new-exam-confirm-replace"]').trigger("click");
    await flushPromises();

    expect(failure).toHaveBeenCalledWith(PENDING_SAVE_COPY);
    expect(publicMocks.createPublicExamWorkspaceBlank).toHaveBeenCalledTimes(1);
    expect(wrapper.find('[data-test="exam-workspace-new-exam-confirm"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-empty"]').exists()).toBe(false);
    wrapper.unmount();
  });
});
