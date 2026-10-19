/**
 * Guest mode inside the shared exam workspace: guest save controls.
 *
 * Expected behavior:
 *   A guest has no Spara button and no save menu (Spara som stays a
 *   signed-in control): a stored step is the save, and the header shows
 *   the guest status text (`Sparat i webbläsaren HH:MM`) after a store.
 */

import { flushPromises } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import {
  expectNoTeacherCalls,
  installGuestModeObjectUrls,
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

describe("ExamWorkspaceView guest mode save controls", () => {
  it("has no Spara button and no save menu while a stored step saves to the browser store", async () => {
    const { guest, storage } = setupGuest();
    const wrapper = await mountGuestView(guest.store);
    await wrapper.get('[data-test="exam-workspace-guest-blank"]').trigger("click");
    await flushPromises();

    expect(wrapper.find('[data-test="exam-workspace-save-menu"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-save"]').exists()).toBe(false);

    await wrapper.get('[data-test="exam-workspace-export"]').trigger("click");
    await flushPromises();
    expect(
      document.querySelectorAll('[data-test^="exam-workspace-export-save-"]').length,
    ).toBe(0);

    await wrapper.get('[data-test="exam-workspace-title"]').trigger("click");
    await flushPromises();
    expect(wrapper.find('[data-test="exam-workspace-metadata-name"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-metadata-rename"]').exists()).toBe(false);

    await wrapper.get('[data-test="exam-workspace-row-item_001"]').trigger("click");
    await wrapper.get('[data-test="exam-workspace-item-points-input"]').setValue("5");
    expect(wrapper.get('[data-test="exam-workspace-save-state"]').text()).toBe("Sparar …");

    window.dispatchEvent(
      new KeyboardEvent("keydown", { bubbles: true, cancelable: true, key: "s", ctrlKey: true }),
    );
    await flushPromises();

    expect(wrapper.get('[data-test="exam-workspace-save-state"]').text()).toMatch(
      /^Sparat i webbläsaren \d{2}:\d{2}$/,
    );
    const stored = await storage.load();
    const saved = stored?.draft.saved_document.items.find((item) => item.item_id === "item_001");
    expect(saved?.points).toBe(5);
    expectNoTeacherCalls(teacherMocks);
    wrapper.unmount();
  });
});
