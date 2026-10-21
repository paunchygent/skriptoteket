/**
 * Guest mode inside the shared exam workspace: guest intake.
 *
 * Expected behavior:
 *   With a guest store (teacher null, guest startBlank present) the same view
 *   starts a blank exam through "Nytt prov" and a QTI .zip through the file
 *   picker or a drop; the DigiExam/Word import shows the sign-in prompt instead
 *   of calling. With the server store nothing changes (covered by the frame,
 *   saveAs, exports, enrichment, retry and conversion slices).
 */

import { flushPromises } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import {
  blankDocument,
  chooseGuestFile,
  expectNoTeacherCalls,
  installGuestModeObjectUrls,
  mountGuestView,
  promptText,
  resetGuestModeTestState,
  setupGuest,
  type TeacherApiMocks,
} from "./ExamWorkspaceGuestMode.specSupport";
import {
  GUEST_IMPORT_SIGN_IN,
} from "./exam-workspace/examWorkspaceGuestCopy";

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

describe("ExamWorkspaceView guest mode intake", () => {
  it("starts blank through Nytt prov and keeps the teacher-only list and course choice hidden", async () => {
    const { guest, publicMocks } = setupGuest();
    const wrapper = await mountGuestView(guest.store);

    expect(wrapper.find('[data-test="exam-workspace-empty"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-workspace-empty"]').text()).toContain(
      "Skapa ett nytt prov, öppna ett sparat prov eller importera från Word eller DigiExam.",
    );
    expect(wrapper.find('[data-test="exam-workspace-sign-in-prompt"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-new-exam"]').exists()).toBe(true);
    expect(wrapper.text()).toContain("Word (.docx)");
    expect(wrapper.text()).toContain("DigiExam (.dxe)");
    expect(wrapper.text()).toContain("QTI (.zip)");
    expect(wrapper.get(".drop__formats").findAll(".xw-chip")).toHaveLength(0);
    expect(
      wrapper.get(".drop__formats").findAll(".drop__format").map((node) => node.text()),
    ).toEqual(["Word (.docx)", "DigiExam (.dxe)", "QTI (.zip)"]);
    expect(wrapper.find('[data-test="exam-workspace-saved-documents"]').exists()).toBe(false);
    expect(document.querySelector("#exam-workspace-import-course")).toBeNull();

    await wrapper.get('[data-test="exam-workspace-new-exam"]').trigger("click");
    await flushPromises();

    expect(publicMocks.createPublicExamWorkspaceBlank).toHaveBeenCalledTimes(1);
    expect(wrapper.find('[data-test="exam-workspace-empty"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-row-item_001"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-workspace-title"]').text()).toBe("Nytt prov");
    expectNoTeacherCalls(teacherMocks);
    wrapper.unmount();
  });

  it("shows the import sign-in prompt for a chosen or dropped .docx without importing", async () => {
    const { guest, publicMocks } = setupGuest();
    const wrapper = await mountGuestView(guest.store);

    await chooseGuestFile(wrapper, new File(["prov"], "NO_Prov_HT25.docx"));
    await flushPromises();

    expect(promptText(wrapper)).toContain(GUEST_IMPORT_SIGN_IN);

    await wrapper.get('[data-test="exam-workspace-drop-zone"]').trigger("drop", {
      dataTransfer: { files: [new File(["prov"], "NO_Prov_HT25.docx")] },
    });
    await flushPromises();

    expect(promptText(wrapper)).toContain(GUEST_IMPORT_SIGN_IN);
    expect(wrapper.find('[data-test="exam-workspace-empty"]').exists()).toBe(true);
    expect(publicMocks.importPublicExamWorkspaceQti).not.toHaveBeenCalled();
    expectNoTeacherCalls(teacherMocks);
    wrapper.unmount();
  });

  it("shows the import sign-in prompt for a dropped .dxe without importing", async () => {
    const { guest, publicMocks } = setupGuest();
    const wrapper = await mountGuestView(guest.store);

    await wrapper.get('[data-test="exam-workspace-drop-zone"]').trigger("drop", {
      dataTransfer: { files: [new File(["dxe"], "Prov_HT25.dxe")] },
    });
    await flushPromises();

    expect(promptText(wrapper)).toContain(GUEST_IMPORT_SIGN_IN);
    expect(wrapper.find('[data-test="exam-workspace-empty"]').exists()).toBe(true);
    expect(publicMocks.importPublicExamWorkspaceQti).not.toHaveBeenCalled();
    expectNoTeacherCalls(teacherMocks);
    wrapper.unmount();
  });

  it("accepts a guest .zip chosen in the picker and opens the parsed exam", async () => {
    const { guest, publicMocks } = setupGuest();
    publicMocks.importPublicExamWorkspaceQti.mockResolvedValue({
      assets: {},
      document: blankDocument(),
      notes: [],
    });
    const wrapper = await mountGuestView(guest.store);

    await chooseGuestFile(wrapper, new File(["qti"], "Prov_HT25.zip", { type: "application/zip" }));
    await flushPromises();

    expect(publicMocks.importPublicExamWorkspaceQti).toHaveBeenCalledTimes(1);
    const [file, courseKey] = publicMocks.importPublicExamWorkspaceQti.mock.calls[0]!;
    expect(file.name).toBe("Prov_HT25.zip");
    expect(courseKey).toBeNull();
    expect(wrapper.find('[data-test="exam-workspace-empty"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-title"]').text()).toBe("Nytt prov");
    expect(wrapper.find('[data-test="exam-workspace-row-item_001"]').exists()).toBe(true);
    expectNoTeacherCalls(teacherMocks);
    wrapper.unmount();
  });

  it("accepts a dropped guest .zip and opens the parsed exam", async () => {
    const { guest, publicMocks } = setupGuest();
    publicMocks.importPublicExamWorkspaceQti.mockResolvedValue({
      assets: {},
      document: blankDocument(),
      notes: [],
    });
    const wrapper = await mountGuestView(guest.store);

    await wrapper.get('[data-test="exam-workspace-drop-zone"]').trigger("drop", {
      dataTransfer: { files: [new File(["qti"], "Prov_HT25.zip", { type: "application/zip" })] },
    });
    await flushPromises();

    expect(publicMocks.importPublicExamWorkspaceQti).toHaveBeenCalledTimes(1);
    expect(wrapper.find('[data-test="exam-workspace-empty"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-title"]').text()).toBe("Nytt prov");
    expectNoTeacherCalls(teacherMocks);
    wrapper.unmount();
  });
});
