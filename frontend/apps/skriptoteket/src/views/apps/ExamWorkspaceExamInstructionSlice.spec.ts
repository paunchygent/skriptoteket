/**
 * The exam instruction is edited from the question list (TASK-SKRIPT-40-04-06
 * D4, D5): an exam with one shows "Instruktioner" with a preview, an exam
 * without one shows a quiet "Lägg till instruktioner"; both open the same
 * editor in the main column. Typing stores the text, clearing it brings the
 * quiet entry back while the editor stays open, and choosing a question
 * leaves the instruction.
 */
import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ExamWorkspaceConversionStatus, NativeExamDocument } from "../../api/examWorkspace";
import { HISTORY_BASELINE_STEP_ID, arrangeStepHistory } from "./ExamWorkspaceHistory.specSupport";
import {
  buildDocument,
  buildResponse,
  importFixtureDocument,
  mountExamWorkspace,
  selectItemRow,
  type ViewWrapper,
} from "./ExamWorkspaceSlice.specSupport";
import { editorBehind, press, settleEditors, surfaceOf } from "./exam-workspace/ExamWorkspaceRichTextEntry.specSupport";
import type { ExamWorkspaceLayout } from "./exam-workspace/useExamWorkspaceLayout";

const apiMocks = vi.hoisted(() => ({
  downloadExamWorkspaceExport: vi.fn(),
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
  getExamWorkspaceExportChecklist: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceConversionStatus: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  saveExamWorkspaceDocument: vi.fn(),
}));
vi.mock("../../api/examWorkspace", async (original) => ({
  ...(await original<typeof import("../../api/examWorkspace")>()),
  ...apiMocks,
  getExamCourseCatalog: (await import("../../test/examCourseCatalog")).getExamCourseCatalog,
}));

const succeeded: ExamWorkspaceConversionStatus = {
  job_id: "job-1", lineage_id: "lineage-1", state: "succeeded", error_message: null, summary: null,
  document_revision: 1, questions_total: 0, questions_done: 0, units: [],
};
const mounted: ViewWrapper[] = [];
const ENTRY = '[data-test="exam-workspace-exam-instructions-entry"]';
const ADD = '[data-test="exam-workspace-exam-instructions-add"]';
const EDITOR = '[data-test="exam-workspace-exam-instruction-editor"]';
const TEXT = "exam-workspace-exam-instruction-text";
const QUESTION_EDITOR = '[data-test="exam-workspace-item-editor"]';

function withInstructions(instructions: NativeExamDocument["instructions"]): NativeExamDocument {
  return { ...buildDocument(), instructions };
}

async function openDocument(document: NativeExamDocument, layout: ExamWorkspaceLayout = "desktop") {
  apiMocks.getExamWorkspaceDocument.mockResolvedValue({
    ...buildResponse({ version: 1, conversion: succeeded }),
    document,
    saved_document: document,
  });
  // The shell's top bar slot receives the header's title and Spara on a phone.
  const slot = globalThis.document.createElement("div");
  slot.id = "app-topbar-page-slot";
  globalThis.document.body.append(slot);
  const host = globalThis.document.createElement("div");
  globalThis.document.body.append(host);
  arrangeStepHistory(apiMocks).documents.set(HISTORY_BASELINE_STEP_ID, document);
  const { wrapper } = await mountExamWorkspace({}, layout, host);
  mounted.push(wrapper);
  await importFixtureDocument(wrapper);
  return wrapper;
}

async function openEditor(wrapper: ViewWrapper, selector: string) {
  await wrapper.get(selector).trigger("click");
  await settleEditors();
}

function typeInstruction(wrapper: ViewWrapper, text: string) {
  editorBehind(wrapper, TEXT).commands.insertContent(text);
}

async function clearInstruction(wrapper: ViewWrapper) {
  editorBehind(wrapper, TEXT).commands.selectAll();
  press(surfaceOf(wrapper, TEXT), "Backspace");
  await flushPromises();
}

beforeEach(() => {
  for (const mock of Object.values(apiMocks)) mock.mockReset();
  apiMocks.listExamWorkspaceDocuments.mockResolvedValue({ documents: [], ordering: "course" });
  apiMocks.getExamWorkspaceConversionStatus.mockResolvedValue(succeeded);
  apiMocks.importExamWorkspaceDocument.mockResolvedValue({ ...succeeded, state: "queued", document_revision: null });
  apiMocks.getExamWorkspaceExportChecklist.mockResolvedValue({ entries: [] });
});
afterEach(() => {
  for (const wrapper of mounted.splice(0)) wrapper.unmount();
  globalThis.document.body.replaceChildren();
});

describe("exam with an instruction", () => {
  it("shows the Instruktioner entry with a preview and no add entry", async () => {
    const wrapper = await openDocument(buildDocument());

    expect(wrapper.get(ENTRY).text()).toContain("Instruktioner");
    expect(wrapper.get(ENTRY).text()).toContain("Besvara alla frågor.");
    expect(wrapper.find(ADD).exists()).toBe(false);
    expect(wrapper.find(EDITOR).exists()).toBe(false);
  });

  it("opens the instruction text and picture in the main editor and leaves it for a question", async () => {
    const document = withInstructions([
      { heading_level: null, segments: [{ kind: "text", marks: [], text: "Se bilden. " }, { kind: "asset", asset_id: "asset_001" }] },
    ]);
    document.assets = [{ asset_id: "asset_001", byte_length: 10, media_type: "image/png", sha256: "0".repeat(64) }];
    const wrapper = await openDocument(document);

    await openEditor(wrapper, ENTRY);

    expect(wrapper.get(EDITOR).text()).toContain("Instruktioner");
    expect(wrapper.get(EDITOR).text()).toContain("Texten skrivs ut före den första frågan.");
    expect(surfaceOf(wrapper, TEXT).textContent).toContain("Se bilden.");
    expect(wrapper.find(`[data-test="${TEXT}"] [data-asset-id="asset_001"]`).exists()).toBe(true);
    expect(wrapper.get(ENTRY).attributes("aria-current")).toBe("true");
    expect(wrapper.find(QUESTION_EDITOR).exists()).toBe(false);

    await selectItemRow(wrapper, "item_002");

    expect(wrapper.find(EDITOR).exists()).toBe(false);
    expect(wrapper.get(ENTRY).attributes("aria-current")).toBeUndefined();
    expect(wrapper.get('[data-test="exam-workspace-row-item_002"]').attributes("aria-selected")).toBe("true");
  });

  it("shows a picture-only instruction as Bild in the preview", async () => {
    const document = withInstructions([{ heading_level: null, segments: [{ kind: "asset", asset_id: "asset_001" }] }]);
    document.assets = [{ asset_id: "asset_001", byte_length: 10, media_type: "image/png", sha256: "0".repeat(64) }];
    const wrapper = await openDocument(document);

    expect(wrapper.get(ENTRY).text()).toContain("Bild");
  });

  it("selecting the same question again after the instruction reopens the question", async () => {
    const wrapper = await openDocument(buildDocument());
    await selectItemRow(wrapper, "item_001");
    await openEditor(wrapper, ENTRY);
    expect(wrapper.find(QUESTION_EDITOR).exists()).toBe(false);

    await selectItemRow(wrapper, "item_001");

    expect(wrapper.find(EDITOR).exists()).toBe(false);
    expect(wrapper.find(QUESTION_EDITOR).exists()).toBe(true);
  });

  it("brings back Lägg till instruktioner when the text is cleared and keeps the editor open", async () => {
    const wrapper = await openDocument(buildDocument());
    await openEditor(wrapper, ENTRY);

    await clearInstruction(wrapper);

    expect(wrapper.find(ENTRY).exists()).toBe(false);
    expect(wrapper.get(ADD).text()).toBe("Lägg till instruktioner");
    expect(wrapper.find(EDITOR).exists()).toBe(true);
    expect(wrapper.get(ADD).attributes("aria-current")).toBe("true");
  });
});

describe("exam without an instruction", () => {
  it("shows only Lägg till instruktioner and opens an empty editor from it", async () => {
    const wrapper = await openDocument(withInstructions([]));

    expect(wrapper.get(ADD).text()).toBe("Lägg till instruktioner");
    expect(wrapper.find(ENTRY).exists()).toBe(false);

    await openEditor(wrapper, ADD);

    expect(wrapper.find(EDITOR).exists()).toBe(true);
    expect(surfaceOf(wrapper, TEXT).textContent).toBe("");
  });

  it("lists the typed text as Instruktioner while the editor stays open", async () => {
    const wrapper = await openDocument(withInstructions([]));
    await openEditor(wrapper, ADD);

    typeInstruction(wrapper, "Läs alla frågor noga.");
    await flushPromises();

    expect(wrapper.find(ADD).exists()).toBe(false);
    expect(wrapper.get(ENTRY).text()).toContain("Läs alla frågor noga.");
    expect(wrapper.get(ENTRY).attributes("aria-current")).toBe("true");
    expect(wrapper.find(EDITOR).exists()).toBe(true);
  });

  it("Ångra after typing removes the instruction again", async () => {
    const wrapper = await openDocument(withInstructions([]));
    await openEditor(wrapper, ADD);
    typeInstruction(wrapper, "Läs alla frågor noga.");
    await flushPromises();
    expect(wrapper.find(ENTRY).exists()).toBe(true);

    await wrapper.get('[data-test="exam-workspace-undo"]').trigger("click");
    await flushPromises();

    expect(wrapper.find(ENTRY).exists()).toBe(false);
    expect(wrapper.get(ADD).text()).toBe("Lägg till instruktioner");
  });
});

describe("exam instruction on a phone", () => {
  it("names the open instruction in the question strip", async () => {
    const wrapper = await openDocument(buildDocument(), "phone");

    await openEditor(wrapper, ENTRY);

    expect(wrapper.get('[data-test="exam-workspace-phone-list"]').text()).toContain("Instruktioner");
    expect(wrapper.find(EDITOR).exists()).toBe(true);
  });
});
