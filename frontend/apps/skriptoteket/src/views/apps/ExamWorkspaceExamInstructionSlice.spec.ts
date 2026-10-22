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
  resetSliceApiMocks,
  selectItemRow,
  type ViewWrapper,
} from "./ExamWorkspaceSlice.specSupport";
import { editorBehind, press, settleEditors, surfaceOf } from "./exam-workspace/ExamWorkspaceRichTextEntry.specSupport";
import type { ExamWorkspaceLayout } from "./exam-workspace/useExamWorkspaceLayout";

const apiMocks = vi.hoisted(() => ({
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  moveExamWorkspaceHistoryPosition: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceConversionStatus: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
}));
const exportApiMocks = vi.hoisted(() => ({
  downloadExamWorkspaceExport: vi.fn(),
  getExamWorkspaceExportChecklist: vi.fn(),
}));
vi.mock("../../api/examWorkspaceExports", () => exportApiMocks);
vi.mock("../../api/examWorkspace", async (original) => ({
  ...(await original<typeof import("../../api/examWorkspace")>()),
  ...apiMocks,
  getExamCourseCatalog: (await import("../../test/examCourseCatalog")).getExamCourseCatalog,
}));

const succeeded: ExamWorkspaceConversionStatus = {
  job_id: "job-1", lineage_id: "lineage-1", state: "succeeded", error_message: null, summary: null,
  document_revision: 1, phase: null, phase_started_at: null, questions_total: 0, questions_done: 0, units: [],
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
  resetSliceApiMocks(apiMocks);
  for (const mock of Object.values(exportApiMocks)) mock.mockReset();
  apiMocks.listExamWorkspaceDocuments.mockResolvedValue({ documents: [], ordering: "course" });
  apiMocks.getExamWorkspaceConversionStatus.mockResolvedValue(succeeded);
  apiMocks.importExamWorkspaceDocument.mockResolvedValue({ ...succeeded, state: "queued", document_revision: null });
  exportApiMocks.getExamWorkspaceExportChecklist.mockResolvedValue({ entries: [] });
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

describe("an instruction that prints nothing counts as absent", () => {
  const blankInstructions = [
    { name: "spaces", segments: [{ kind: "text" as const, marks: [], text: "   " }] },
    { name: "a hard break", segments: [{ kind: "text" as const, marks: [], text: "\n" }] },
    { name: "spaces around a hard break", segments: [{ kind: "text" as const, marks: [], text: " \n  " }] },
  ];

  it.each(blankInstructions)("treats an instruction of $name as none", async ({ segments }) => {
    const wrapper = await openDocument(withInstructions([{ heading_level: null, segments }]));

    expect(wrapper.get(ADD).text()).toBe("Lägg till instruktioner");
    expect(wrapper.find(ENTRY).exists()).toBe(false);
    expect(wrapper.text()).not.toContain("Bild");
  });

  it.each(blankInstructions)("ArrowUp from the first question skips an instruction of $name", async ({ segments }) => {
    const wrapper = await openDocument(withInstructions([{ heading_level: null, segments }]));
    const first = wrapper.find('[role="row"][aria-selected="true"]').attributes("data-entry-id") ?? null;

    window.dispatchEvent(new KeyboardEvent("keydown", { bubbles: true, key: "ArrowUp" }));
    await flushPromises();

    expect(wrapper.find(EDITOR).exists()).toBe(false);
    expect(wrapper.find('[role="row"][aria-selected="true"]').attributes("data-entry-id") ?? null).toBe(first);
  });

  it("keeps the editor open and brings back the quiet entry when the text is cleared down to a hard break", async () => {
    const wrapper = await openDocument(buildDocument());
    await openEditor(wrapper, ENTRY);

    editorBehind(wrapper, TEXT).chain().selectAll().deleteSelection().setHardBreak().run();
    await flushPromises();

    expect(wrapper.find(ENTRY).exists()).toBe(false);
    expect(wrapper.get(ADD).text()).toBe("Lägg till instruktioner");
    expect(wrapper.text()).not.toContain("Bild");
    expect(wrapper.find(EDITOR).exists()).toBe(true);
    expect(wrapper.get(ADD).attributes("aria-current")).toBe("true");
  });

  it("shows Bild only for an instruction whose text is blank but holds a picture", async () => {
    const document = withInstructions([
      {
        heading_level: null,
        segments: [{ kind: "text", marks: [], text: " \n " }, { kind: "asset", asset_id: "asset_001" }],
      },
    ]);
    document.assets = [{ asset_id: "asset_001", byte_length: 10, media_type: "image/png", sha256: "0".repeat(64) }];
    const wrapper = await openDocument(document);

    expect(wrapper.find(ADD).exists()).toBe(false);
    expect(wrapper.get(ENTRY).text()).toContain("Bild");
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

describe("arrow keys and the exam instruction", () => {
  const arrow = async (key: "ArrowDown" | "ArrowUp") => {
    window.dispatchEvent(new KeyboardEvent("keydown", { bubbles: true, key }));
    await flushPromises();
  };
  const selectedRow = (wrapper: ViewWrapper) =>
    wrapper.find('[role="row"][aria-selected="true"]').attributes("data-entry-id") ?? null;

  it("walks from the instruction to the first question and back, and stops at the instruction", async () => {
    const wrapper = await openDocument(buildDocument());
    await openEditor(wrapper, ENTRY);
    const first = wrapper.get('[role="row"]').attributes("data-entry-id");

    await arrow("ArrowDown");
    expect(wrapper.find(EDITOR).exists()).toBe(false);
    expect(selectedRow(wrapper)).toBe(first);

    await arrow("ArrowUp");
    expect(wrapper.find(EDITOR).exists()).toBe(true);
    expect(wrapper.get(ENTRY).attributes("aria-current")).toBe("true");

    await arrow("ArrowUp");
    expect(wrapper.find(EDITOR).exists()).toBe(true);
  });

  it("does not open the empty instruction from the first question of an exam without one", async () => {
    const wrapper = await openDocument(withInstructions([]));
    const first = selectedRow(wrapper);

    await arrow("ArrowUp");

    expect(wrapper.find(EDITOR).exists()).toBe(false);
    expect(selectedRow(wrapper)).toBe(first);
  });
});
