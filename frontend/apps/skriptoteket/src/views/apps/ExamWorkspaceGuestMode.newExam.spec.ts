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

import type { NativeExamDocument } from "../../api/examWorkspace";
import {
  blankDocument,
  installGuestModeObjectUrls,
  keylessItem,
  mountGuestView,
  resetGuestModeTestState,
  setupGuest,
  type TeacherApiMocks,
} from "./ExamWorkspaceGuestMode.specSupport";

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

    await wrapper.get('[data-test="exam-workspace-new"]').trigger("click");
    await flushPromises();

    expect(publicMocks.createPublicExamWorkspaceBlank).toHaveBeenCalledTimes(1);
    expect(wrapper.find('[data-test="exam-workspace-new-confirm"]').exists()).toBe(false);
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

    await wrapper.get('[data-test="exam-workspace-new"]').trigger("click");
    await flushPromises();
    expect(wrapper.find('[data-test="exam-workspace-new-confirm"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-empty"]').exists()).toBe(false);

    await wrapper.get('[data-test="exam-workspace-new"]').trigger("click");
    await flushPromises();

    expect(publicMocks.createPublicExamWorkspaceBlank).toHaveBeenCalledTimes(2);
    expect(wrapper.find('[data-test="exam-workspace-new-confirm"]').exists()).toBe(false);
    wrapper.unmount();
  });

  it("confirms before replacing a draft that has content", async () => {
    const { guest, publicMocks } = setupGuest();
    const wrapper = await mountGuestView(guest.store);

    await wrapper.get('[data-test="exam-workspace-new"]').trigger("click");
    await flushPromises();
    expect(publicMocks.createPublicExamWorkspaceBlank).toHaveBeenCalledTimes(1);
    expect(wrapper.find('[data-test="exam-workspace-new-confirm"]').exists()).toBe(false);

    await wrapper.get('[data-test="exam-workspace-new"]').trigger("click");
    await flushPromises();

    const confirm = wrapper.get('[data-test="exam-workspace-new-confirm"]');
    expect(confirm.text()).toContain("Nytt prov");
    expect(confirm.text()).toContain(CONFIRM_COPY);
    expect(
      wrapper.get('[data-test="exam-workspace-new-confirm-cancel"]').text(),
    ).toBe("Avbryt");
    expect(
      wrapper.get('[data-test="exam-workspace-new-confirm-replace"]').text(),
    ).toBe("Ersätt");
    expect(publicMocks.createPublicExamWorkspaceBlank).toHaveBeenCalledTimes(1);
    wrapper.unmount();
  });

  it("Avbryt closes the confirm and leaves the draft unchanged", async () => {
    const { guest, publicMocks } = setupGuest();
    const wrapper = await mountGuestView(guest.store);

    await wrapper.get('[data-test="exam-workspace-new"]').trigger("click");
    await flushPromises();
    await wrapper.get('[data-test="exam-workspace-new"]').trigger("click");
    await flushPromises();
    expect(wrapper.find('[data-test="exam-workspace-new-confirm"]').exists()).toBe(true);

    await wrapper.get('[data-test="exam-workspace-new-confirm-cancel"]').trigger("click");
    await flushPromises();

    expect(wrapper.find('[data-test="exam-workspace-new-confirm"]').exists()).toBe(false);
    expect(publicMocks.createPublicExamWorkspaceBlank).toHaveBeenCalledTimes(1);
    expect(wrapper.find('[data-test="exam-workspace-empty"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-title"]').text()).toBe("Nytt prov");
    wrapper.unmount();
  });

  it("Ersätt starts the new draft and opens it", async () => {
    const { guest, publicMocks } = setupGuest();
    const wrapper = await mountGuestView(guest.store);

    await wrapper.get('[data-test="exam-workspace-new"]').trigger("click");
    await flushPromises();
    await wrapper.get('[data-test="exam-workspace-new"]').trigger("click");
    await flushPromises();
    await wrapper.get('[data-test="exam-workspace-new-confirm-replace"]').trigger("click");
    await flushPromises();

    expect(publicMocks.createPublicExamWorkspaceBlank).toHaveBeenCalledTimes(2);
    expect(wrapper.find('[data-test="exam-workspace-new-confirm"]').exists()).toBe(false);
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
