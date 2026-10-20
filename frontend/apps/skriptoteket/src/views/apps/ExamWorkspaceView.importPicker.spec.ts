/**
 * Exam workspace header Importera behavior.
 *
 * Expected behavior:
 *   Importera in the header opens the Öppna drawer and clicks its file input
 *   once, whether the drawer was closed or already open. While importing is
 *   blocked (unsaved edit) it opens the drawer but never the picker. The
 *   request is consumed, so the next click asks again.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  arrangeViewApis,
  editPoints,
  importFixture,
  importsTheFixture,
  mountView,
  unmountViews,
  type ViewWrapper,
} from "./ExamWorkspaceView.specSupport";


const apiMocks = vi.hoisted(() => ({
  copyExamWorkspaceDocument: vi.fn(),
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  moveExamWorkspaceHistoryPosition: vi.fn(),
  importExamWorkspaceDigiExam: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceConversionStatus: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
}));
const exportApiMocks = vi.hoisted(() => ({
  downloadExamWorkspaceExport: vi.fn(),
}));

vi.mock("../../api/examWorkspaceExports", () => exportApiMocks);
vi.mock("../../api/examWorkspace", async () => ({
  ...apiMocks,
  getExamCourseCatalog: (await import("../../test/examCourseCatalog")).getExamCourseCatalog,
}));

const OPEN_DRAWER = '[data-test="exam-workspace-drawer-open"]';
const IMPORT = '[data-test="exam-workspace-import"]';
const SOURCE_INPUT = '[data-test="exam-workspace-source-file-input"]';

let inputClick: ReturnType<typeof vi.spyOn>;

afterEach(() => {
  inputClick.mockRestore();
  unmountViews();
});

beforeEach(() => {
  arrangeViewApis(apiMocks);
  inputClick = vi.spyOn(HTMLInputElement.prototype, "click").mockImplementation(() => undefined);
});

/** How many times the Öppna drawer's file input was clicked. */
function pickerClicks(): number {
  return inputClick.mock.contexts.filter(
    (input: unknown) => (input as HTMLInputElement).dataset.test === "exam-workspace-source-file-input",
  ).length;
}

async function clickImportera(wrapper: ViewWrapper): Promise<void> {
  await wrapper.get(IMPORT).trigger("click");
  await flushPromises();
}

describe("header Importera", () => {
  it("opens the closed Öppna drawer and clicks its file input once", async () => {
    importsTheFixture(apiMocks);
    const wrapper = await mountView();
    await importFixture(wrapper);
    await wrapper.get('[data-test="exam-workspace-open"]').trigger("click");
    expect(wrapper.find(OPEN_DRAWER).exists()).toBe(false);
    expect(pickerClicks()).toBe(0);

    await clickImportera(wrapper);

    expect(wrapper.find(OPEN_DRAWER).exists()).toBe(true);
    expect(pickerClicks()).toBe(1);
  });

  it("clicks the file input of an already open Öppna drawer once, and again on the next request", async () => {
    const wrapper = await mountView();
    expect(wrapper.find(OPEN_DRAWER).exists()).toBe(true);
    expect(wrapper.find(SOURCE_INPUT).exists()).toBe(true);

    await clickImportera(wrapper);
    expect(pickerClicks()).toBe(1);

    await clickImportera(wrapper);
    expect(pickerClicks()).toBe(2);
  });

  it("opens Öppna but not the picker while an unsaved edit blocks importing", async () => {
    importsTheFixture(apiMocks);
    const wrapper = await mountView();
    await importFixture(wrapper);
    await editPoints(wrapper, "7");
    await flushPromises();

    await clickImportera(wrapper);

    expect(wrapper.find(OPEN_DRAWER).exists()).toBe(true);
    expect(wrapper.get<HTMLInputElement>(SOURCE_INPUT).element.disabled).toBe(true);
    expect(pickerClicks()).toBe(0);
  });
});
