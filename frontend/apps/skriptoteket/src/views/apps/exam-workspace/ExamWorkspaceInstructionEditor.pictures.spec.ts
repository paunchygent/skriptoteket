/**
 * Exam workspace instruction editor, pictures.
 *
 * Expected behavior:
 *   A declared picture in the instruction body renders as the picture when
 *   its asset URL is known, exactly as in a question text, and keeps the
 *   "Bild" placeholder atom when it is not. Editing the text keeps the
 *   picture, and clearing the instruction emits the empty body.
 */

import { mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import ExamWorkspaceInstructionEditor from "./ExamWorkspaceInstructionEditor.vue";
import {
  editorBehind,
  press,
  selectText,
  settleEditors,
  surfaceOf,
} from "./ExamWorkspaceRichTextEntry.specSupport";
import { buildRecordedParent } from "./examWorkspaceParentDocument.specSupport";

const URL = "https://gateway.test/assets/asset_001";
const INSTRUCTION = "exam-workspace-instruction-text";

let mounted: VueWrapper | null = null;

afterEach(() => {
  mounted?.unmount();
  mounted = null;
  document.body.innerHTML = "";
});

async function mountEditor(assetUrls?: Record<string, string>, disabled = false) {
  const parent = buildRecordedParent();
  parent.instruction = [
    {
      heading_level: null,
      segments: [
        { kind: "text", marks: [], text: "Se " },
        { kind: "asset", asset_id: "asset_001" },
      ],
    },
  ];
  mounted = mount(ExamWorkspaceInstructionEditor, {
    attachTo: document.body,
    props: { parent, label: "1", children: [], subtotal: 0, printedTotal: null, disabled, notice: null, assetUrls },
  });
  await settleEditors();
  return mounted;
}

describe("ExamWorkspaceInstructionEditor pictures", () => {
  it("shows the declared picture in the instruction", async () => {
    const wrapper = await mountEditor({ asset_001: URL });

    expect(wrapper.get('[data-asset-id="asset_001"] img').attributes("src")).toBe(URL);
  });

  it("keeps the placeholder atom without a mapped URL", async () => {
    const wrapper = await mountEditor();

    // ProseMirror appends its own separator <img> after a trailing atom.
    expect(wrapper.find("img.xw-picture__image").exists()).toBe(false);
    expect(wrapper.find('[data-atom="asset"][data-asset-id="asset_001"]').exists()).toBe(true);
  });

  it("keeps the picture when only the instruction text is edited", async () => {
    const wrapper = await mountEditor({ asset_001: URL });
    const editor = editorBehind(wrapper, INSTRUCTION);

    selectText(editor, "Se ", 1, 3);
    press(surfaceOf(wrapper, INSTRUCTION), "Backspace");

    expect(wrapper.emitted("updateInstruction")!.at(-1)).toEqual([
      [
        {
          heading_level: null,
          segments: [
            { kind: "text", marks: [], text: "S" },
            { kind: "asset", asset_id: "asset_001" },
          ],
        },
      ],
    ]);
    expect(wrapper.find('[data-asset-id="asset_001"] img').attributes("src")).toBe(URL);
  });

  it("emits the empty instruction when everything is deleted", async () => {
    const wrapper = await mountEditor({ asset_001: URL });
    editorBehind(wrapper, INSTRUCTION).commands.selectAll();

    press(surfaceOf(wrapper, INSTRUCTION), "Backspace");

    expect(wrapper.emitted("updateInstruction")).toEqual([[[]]]);
  });

  it("does not edit the instruction while the editor is locked", async () => {
    const wrapper = await mountEditor({ asset_001: URL }, true);
    editorBehind(wrapper, INSTRUCTION).commands.selectAll();

    press(surfaceOf(wrapper, INSTRUCTION), "Backspace");

    expect(surfaceOf(wrapper, INSTRUCTION).getAttribute("contenteditable")).toBe("false");
    expect(wrapper.emitted("updateInstruction")).toBeUndefined();
  });

  it("bolds the instruction selection through its own toolbar", async () => {
    const wrapper = await mountEditor();
    const editor = editorBehind(wrapper, INSTRUCTION);
    surfaceOf(wrapper, INSTRUCTION).focus();
    selectText(editor, "Se ", 0, 2);

    await wrapper.get('[data-test="exam-workspace-body-mark-bold"]').trigger("click");

    expect(wrapper.emitted("updateInstruction")!.at(-1)![0]).toEqual([
      {
        heading_level: null,
        segments: [
          { kind: "text", marks: ["bold"], text: "Se" },
          { kind: "text", marks: [], text: " " },
          { kind: "asset", asset_id: "asset_001" },
        ],
      },
    ]);
  });
});
