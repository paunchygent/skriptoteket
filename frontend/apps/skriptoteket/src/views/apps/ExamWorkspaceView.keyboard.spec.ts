/**
 * Exam workspace keyboard shortcut behavior.
 *
 * Expected behavior:
 *   Ctrl/Cmd+S never reaches the browser's save page and stores a pending
 *   edit at once through the autosave history, and nothing when unchanged;
 *   Ctrl/Cmd+Z steps back outside text fields through the position move and
 *   leaves plain input fields alone. Inside the question text (an exam
 *   rich-text editor) it runs the workspace's Ångra once and never the
 *   browser's own undo.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { NativeExamDocument } from "../../api/examWorkspace";
import {
  arrangeViewApis,
  buildDocument,
  buildResponse,
  editPoints,
  importFixture,
  importsTheFixture,
  mountView,
  pressKey,
  unmountViews,
} from "./ExamWorkspaceView.specSupport";

import { arrangeStepHistory } from "./ExamWorkspaceHistory.specSupport";

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

afterEach(unmountViews);

beforeEach(() => {
  arrangeViewApis(apiMocks);
  arrangeStepHistory(apiMocks);
});

describe("ExamWorkspaceView keyboard shortcuts", () => {
  it.each([
    ["Ctrl+S", { ctrlKey: true }],
    ["Meta+S", { metaKey: true }],
  ])("%s never opens the browser's save page, with or without an exam, and stores nothing unchanged", async (_name, modifier) => {
    importsTheFixture(apiMocks);
    const wrapper = await mountView();

    expect(pressKey({ key: "s", ...modifier }).defaultPrevented).toBe(true);

    await importFixture(wrapper);

    expect(pressKey({ key: "s", ...modifier }).defaultPrevented).toBe(true);
    expect(pressKey({ key: "S", ...modifier }).defaultPrevented).toBe(true);
    await flushPromises();
    expect(apiMocks.storeExamWorkspaceUndoStep).not.toHaveBeenCalled();
    expect(pressKey({ key: "s" }).defaultPrevented).toBe(false);
  });

  it.each([
    ["Ctrl+S", { ctrlKey: true }],
    ["Meta+S", { metaKey: true }],
  ])("%s stores the changed exam as a step at once, then stores nothing unchanged", async (_name, modifier) => {
    importsTheFixture(apiMocks);
    const wrapper = await mountView();
    await importFixture(wrapper);
    await editPoints(wrapper, "7");
    expect(wrapper.find('[data-test="exam-workspace-save-state"]').text()).toBe("Sparar …");

    expect(pressKey({ key: "s", ...modifier }).defaultPrevented).toBe(true);
    await flushPromises();

    expect(apiMocks.storeExamWorkspaceUndoStep).toHaveBeenCalledTimes(1);
    const [lineageId, params] = apiMocks.storeExamWorkspaceUndoStep.mock.calls[0] as [
      string,
      { document: NativeExamDocument },
    ];
    expect(lineageId).toBe("lineage-1");
    expect(params.document.items[0]?.points).toBe(7);
    expect(wrapper.find('[data-test="exam-workspace-save-state"]').text()).toMatch(/^Sparat /);

    pressKey({ key: "s", ...modifier });
    await flushPromises();
    expect(apiMocks.storeExamWorkspaceUndoStep).toHaveBeenCalledTimes(1);
  });

  it("Ctrl+Z outside a text field moves the position back through the stored history", async () => {
    importsTheFixture(apiMocks);
    const baselineId = "step-baseline";
    const cursorStep = buildResponse().history_cursor;
    apiMocks.getExamWorkspaceHistory.mockResolvedValue({
      baseline_step_id: baselineId,
      cursor: cursorStep,
      position_step_id: cursorStep,
      step_ids: [cursorStep],
    });
    apiMocks.moveExamWorkspaceHistoryPosition.mockResolvedValueOnce({
      document: buildDocument(),
      export_blockers: [],
      history: {
        baseline_step_id: baselineId,
        cursor: "cursor-2",
        position_step_id: baselineId,
        step_ids: [cursorStep],
      },
    });
    const wrapper = await mountView();
    await importFixture(wrapper);

    const event = pressKey({ key: "z", ctrlKey: true }, document.body);
    await flushPromises();

    expect(event.defaultPrevented).toBe(true);
    expect(apiMocks.moveExamWorkspaceHistoryPosition).toHaveBeenCalledExactlyOnceWith("lineage-1", {
      expectedCursor: cursorStep,
      stepId: baselineId,
      tabId: expect.any(String),
    });
  });

  it("Ctrl+Z inside the question text runs the workspace Ångra once, as the button does", async () => {
    importsTheFixture(apiMocks);
    const baselineId = "step-baseline";
    const cursorStep = buildResponse().history_cursor;
    apiMocks.getExamWorkspaceHistory.mockResolvedValue({
      baseline_step_id: baselineId,
      cursor: cursorStep,
      position_step_id: cursorStep,
      step_ids: [cursorStep],
    });
    apiMocks.moveExamWorkspaceHistoryPosition.mockResolvedValueOnce({
      document: buildDocument(),
      export_blockers: [],
      history: {
        baseline_step_id: baselineId,
        cursor: "cursor-2",
        position_step_id: baselineId,
        step_ids: [cursorStep],
      },
    });
    const wrapper = await mountView();
    await importFixture(wrapper);
    await wrapper.find('[data-test="exam-workspace-row-item_001"]').trigger("click");
    await flushPromises();
    const surface = wrapper.get('[data-test="exam-workspace-body-editor-surface"]').element;
    // A browser reports a contenteditable surface as editable, which keeps the
    // window shortcut out of it; jsdom does not implement the property.
    Object.defineProperty(surface, "isContentEditable", { value: true });

    const event = pressKey({ key: "z", ctrlKey: true, keyCode: 90 }, surface);
    await flushPromises();

    expect(event.defaultPrevented).toBe(true);
    expect(apiMocks.moveExamWorkspaceHistoryPosition).toHaveBeenCalledExactlyOnceWith("lineage-1", {
      expectedCursor: cursorStep,
      stepId: baselineId,
      tabId: expect.any(String),
    });
  });

  it("Ctrl+Z inside a text field is left to the field and does not undo the exam", async () => {
    importsTheFixture(apiMocks);
    apiMocks.getExamWorkspaceHistory.mockResolvedValue({
      baseline_step_id: "step-baseline",
      cursor: buildResponse().history_cursor,
      position_step_id: buildResponse().history_cursor,
      step_ids: [buildResponse().history_cursor],
    });
    const wrapper = await mountView();
    await importFixture(wrapper);
    const field = document.createElement("input");
    document.body.append(field);

    const event = pressKey({ key: "z", ctrlKey: true }, field);
    const shifted = pressKey({ key: "z", ctrlKey: true, shiftKey: true }, field);
    await flushPromises();
    field.remove();

    expect(event.defaultPrevented).toBe(false);
    expect(shifted.defaultPrevented).toBe(false);
    expect(apiMocks.moveExamWorkspaceHistoryPosition).not.toHaveBeenCalled();
  });
});
