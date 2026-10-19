/**
 * Exam workspace editing session: the exam instruction as one document.
 *
 * Expected behavior (TASK-SKRIPT-40-04-06 D4, D5):
 *   - Typing in the exam instruction editor stores the whole text as
 *     `instructions`; clearing it stores `[]`.
 *   - Ångra after an instruction edit restores the previous instructions.
 *   - Deleting a picture from the instruction drops its asset record unless
 *     another body still references it.
 *
 * The edit is made through the real exam instruction editor mounted on the
 * production editing session; transport is the named double of the server's
 * step store.
 */

import { mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { computed, defineComponent, h, nextTick } from "vue";

import type { NativeExamBodyParagraph, NativeExamDocument } from "../../../api/examWorkspace";
import ExamWorkspaceExamInstructionEditor from "./ExamWorkspaceExamInstructionEditor.vue";
import {
  editorBehind,
  press,
  settleEditors,
  surfaceOf,
} from "./ExamWorkspaceRichTextEntry.specSupport";
import { exam, openEditing, stopScopes } from "./useExamWorkspaceEditing.history.specSupport";

const api = vi.hoisted(() => ({
  changeExamWorkspaceItemType: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  moveExamWorkspaceHistoryPosition: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
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

const TEXT = "exam-workspace-exam-instruction-text";

beforeEach(() => {
  for (const fn of [...Object.values(api), ...Object.values(toast)]) fn.mockReset();
});

afterEach(() => {
  stopScopes();
  document.body.innerHTML = "";
});

function paragraph(text: string): NativeExamBodyParagraph {
  return { heading_level: null, segments: [{ kind: "text", marks: [], text, kept_gap_id: null }] };
}

function asset(assetId: string): NativeExamDocument["assets"][number] {
  return { asset_id: assetId, byte_length: 10, media_type: "image/png", sha256: "0".repeat(64) };
}

function baseline(overrides: Partial<NativeExamDocument> = {}): NativeExamDocument {
  return { ...exam("Prov", 2), ...overrides };
}

/** The exam instruction editor wired as the editor pane wires it: edits go to `setExamInstructions`. */
async function mountEditor(editing: Awaited<ReturnType<typeof openEditing>>["editing"], disabled = false) {
  const Host = defineComponent({
    setup() {
      const instructions = computed(() => editing.workspaceDocument.value!.instructions);
      return () =>
        h(ExamWorkspaceExamInstructionEditor, {
          instructions: instructions.value,
          disabled,
          onUpdateInstructions: editing.setExamInstructions,
        });
    },
  });
  const wrapper = mount(Host, { attachTo: document.body });
  await settleEditors();
  return wrapper as VueWrapper;
}

describe("exam instruction edits", () => {
  it("stores typed text in an exam that had no instruction", async () => {
    const { editing } = await openEditing(api, baseline());
    const wrapper = await mountEditor(editing);

    editorBehind(wrapper, TEXT).commands.insertContent("Läs alla frågor noga.");
    await nextTick();

    expect(editing.workspaceDocument.value!.instructions).toEqual([paragraph("Läs alla frågor noga.")]);
    wrapper.unmount();
  });

  it("stores [] when the whole text is cleared and keeps the editor mounted", async () => {
    const { editing } = await openEditing(api, baseline({ instructions: [paragraph("Läs alla frågor noga.")] }));
    const wrapper = await mountEditor(editing);
    editorBehind(wrapper, TEXT).commands.selectAll();

    press(surfaceOf(wrapper, TEXT), "Backspace");
    await nextTick();

    expect(editing.workspaceDocument.value!.instructions).toEqual([]);
    expect(wrapper.find(`[data-test="${TEXT}"]`).exists()).toBe(true);
    wrapper.unmount();
  });

  it("restores the previous instructions with Ångra", async () => {
    const original = [paragraph("Läs alla frågor noga.")];
    const { editing } = await openEditing(api, baseline({ instructions: original }));
    const wrapper = await mountEditor(editing);
    editorBehind(wrapper, TEXT).commands.selectAll();
    press(surfaceOf(wrapper, TEXT), "Backspace");
    await nextTick();
    expect(editing.workspaceDocument.value!.instructions).toEqual([]);

    await editing.history.undo();

    expect(editing.workspaceDocument.value!.instructions).toEqual(original);
    wrapper.unmount();
  });

  it("does not edit while the workspace is busy", async () => {
    const { editing } = await openEditing(api, baseline({ instructions: [paragraph("Läs noga.")] }));
    const wrapper = await mountEditor(editing, true);
    editorBehind(wrapper, TEXT).commands.selectAll();

    press(surfaceOf(wrapper, TEXT), "Backspace");
    await nextTick();

    expect(surfaceOf(wrapper, TEXT).getAttribute("contenteditable")).toBe("false");
    expect(editing.workspaceDocument.value!.instructions).toEqual([paragraph("Läs noga.")]);
    wrapper.unmount();
  });
});

describe("pictures in the exam instruction", () => {
  const pictureInstruction: NativeExamBodyParagraph[] = [
    {
      heading_level: null,
      segments: [
        { kind: "text", marks: [], text: "Se " },
        { kind: "asset", asset_id: "asset_001" },
      ],
    },
  ];

  it("drops the asset record with a deleted picture and returns it with Ångra", async () => {
    const start = baseline({ assets: [asset("asset_001")], instructions: pictureInstruction });
    const { editing } = await openEditing(api, start);
    const wrapper = await mountEditor(editing);
    editorBehind(wrapper, TEXT).commands.selectAll();

    press(surfaceOf(wrapper, TEXT), "Backspace");
    await nextTick();
    expect(editing.workspaceDocument.value!.instructions).toEqual([]);
    expect(editing.workspaceDocument.value!.assets).toEqual([]);

    await editing.history.undo();
    expect(editing.workspaceDocument.value!.instructions).toEqual(pictureInstruction);
    expect(editing.workspaceDocument.value!.assets).toEqual(start.assets);
    wrapper.unmount();
  });

  it("keeps the asset record another question still references", async () => {
    const start = baseline({ assets: [asset("asset_001")], instructions: pictureInstruction });
    start.items[0] = {
      ...start.items[0]!,
      body: [{ heading_level: null, segments: [{ kind: "asset", asset_id: "asset_001" }] }],
    };
    const { editing } = await openEditing(api, start);
    const wrapper = await mountEditor(editing);
    editorBehind(wrapper, TEXT).commands.selectAll();

    press(surfaceOf(wrapper, TEXT), "Backspace");
    await nextTick();

    expect(editing.workspaceDocument.value!.instructions).toEqual([]);
    expect(editing.workspaceDocument.value!.assets.map((entry) => entry.asset_id)).toEqual(["asset_001"]);
    wrapper.unmount();
  });
});
