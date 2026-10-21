/**
 * Guest mode inside the shared exam workspace: AI sign-in prompts.
 *
 * Expected behavior:
 *   With a guest store every AI control (header, export-blocker controls,
 *   Föreslå innehåll, Konvertera igen) shows the sign-in prompt instead of
 *   calling. AI controls stay enabled and show no admin-only note.
 */

import { flushPromises } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import { AI_ADMIN_ONLY_NOTE } from "../../composables/useAiAccess";
import {
  expectNoTeacherCalls,
  installGuestModeObjectUrls,
  mountGuestView,
  promptText,
  resetGuestModeTestState,
  setupGuest,
  type TeacherApiMocks,
} from "./ExamWorkspaceGuestMode.specSupport";
import {
  GUEST_AI_SIGN_IN,
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

describe("ExamWorkspaceView guest mode AI sign-in prompts", () => {
  it("shows the AI sign-in prompt from the header control without calling", async () => {
    const { guest } = setupGuest();
    const wrapper = await mountGuestView(guest.store);
    await wrapper.get('[data-test="exam-workspace-new"]').trigger("click");
    await flushPromises();

    const suggest = wrapper.get('[data-test="exam-workspace-suggest-all"]');
    expect(suggest.attributes("disabled")).toBeUndefined();
    await suggest.trigger("click");
    await flushPromises();

    expect(promptText(wrapper)).toContain(GUEST_AI_SIGN_IN);
    expectNoTeacherCalls(teacherMocks);
    wrapper.unmount();
  });

  it("shows the AI sign-in prompt from both export-blocker controls without calling", async () => {
    const { guest } = setupGuest();
    const wrapper = await mountGuestView(guest.store);
    await wrapper.get('[data-test="exam-workspace-new"]').trigger("click");
    await flushPromises();

    await wrapper.get('[data-test="exam-workspace-export"]').trigger("click");
    await flushPromises();

    const suggestAll = document.querySelector<HTMLElement>(
      '[data-test="exam-workspace-blocker-suggest-all"]',
    )!;
    expect(suggestAll.hasAttribute("disabled")).toBe(false);
    suggestAll.click();
    await flushPromises();
    expect(promptText(wrapper)).toContain(GUEST_AI_SIGN_IN);

    const fix = document.querySelector<HTMLElement>(
      '[data-test="exam-workspace-blocker-fix-item_001"]',
    )!;
    expect(fix.hasAttribute("disabled")).toBe(false);
    fix.click();
    await flushPromises();
    expect(promptText(wrapper)).toContain(GUEST_AI_SIGN_IN);
    expectNoTeacherCalls(teacherMocks);
    wrapper.unmount();
  });

  it("shows the AI sign-in prompt from Föreslå innehåll without calling", async () => {
    const { guest } = setupGuest();
    const wrapper = await mountGuestView(guest.store);
    await wrapper.get('[data-test="exam-workspace-new"]').trigger("click");
    await flushPromises();

    await wrapper.get('[data-test="exam-workspace-details"]').trigger("click");
    await flushPromises();

    const suggest = wrapper.get('[data-test="exam-workspace-content-suggest"]');
    expect(suggest.attributes("disabled")).toBeUndefined();
    await suggest.trigger("click");
    await flushPromises();

    expect(promptText(wrapper)).toContain(GUEST_AI_SIGN_IN);
    expectNoTeacherCalls(teacherMocks);
    wrapper.unmount();
  });

  it("shows the AI sign-in prompt from Konvertera igen without calling", async () => {
    const { guest } = setupGuest();
    const wrapper = await mountGuestView(guest.store);
    await wrapper.get('[data-test="exam-workspace-new"]').trigger("click");
    await flushPromises();

    await wrapper.get('[data-test="exam-workspace-row-item_003"]').trigger("click");
    await wrapper.get('[data-test="exam-workspace-import-toggle"]').trigger("click");
    await flushPromises();

    const retry = wrapper.get('[data-test="exam-workspace-retry"]');
    expect(retry.attributes("disabled")).toBeUndefined();
    expect(wrapper.get('[data-test="exam-workspace-retry-kind"]').attributes("disabled")).toBeUndefined();
    await retry.trigger("click");
    await flushPromises();

    expect(promptText(wrapper)).toContain(GUEST_AI_SIGN_IN);
    expectNoTeacherCalls(teacherMocks);
    wrapper.unmount();
  });

  it("renders no admin-only note and leaves every AI control enabled", async () => {
    const { guest } = setupGuest();
    const wrapper = await mountGuestView(guest.store);
    await wrapper.get('[data-test="exam-workspace-new"]').trigger("click");
    await flushPromises();

    expect(wrapper.text()).not.toContain(AI_ADMIN_ONLY_NOTE);
    expect(document.body.textContent ?? "").not.toContain(AI_ADMIN_ONLY_NOTE);
    expect(wrapper.get('[data-test="exam-workspace-suggest-all"]').attributes("disabled")).toBeUndefined();

    await wrapper.get('[data-test="exam-workspace-export"]').trigger("click");
    await flushPromises();
    expect(document.body.textContent ?? "").not.toContain(AI_ADMIN_ONLY_NOTE);

    await wrapper.get('[data-test="exam-workspace-details"]').trigger("click");
    await flushPromises();
    expect(wrapper.get('[data-test="exam-workspace-content-suggest"]').attributes("disabled")).toBeUndefined();

    await wrapper.get('[data-test="exam-workspace-row-item_003"]').trigger("click");
    await wrapper.get('[data-test="exam-workspace-import-toggle"]').trigger("click");
    await flushPromises();
    expect(wrapper.get('[data-test="exam-workspace-retry"]').attributes("disabled")).toBeUndefined();
    expect(wrapper.text()).not.toContain(AI_ADMIN_ONLY_NOTE);
    wrapper.unmount();
  });
});
