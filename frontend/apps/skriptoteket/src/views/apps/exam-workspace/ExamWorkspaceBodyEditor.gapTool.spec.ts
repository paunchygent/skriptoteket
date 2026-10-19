/**
 * Exam workspace question-text editor: the gap tool wiring.
 *
 * Expected behavior (TASK-SKRIPT-40-04-09 G4):
 *   The toolbar Luckverktyg toggle and Ctrl+Alt+G switch one tool per
 *   question on; while it is on, word clicks become gaps at once with no
 *   popover and no floating button. The tool ends by its toggle, its
 *   shortcut, Escape with no popover open, a move to another question,
 *   disabling, or the gap_999 cap. Escape with a popover open closes the
 *   popover first and keeps the tool on. Free text shows no toggle and the
 *   shortcut does nothing there; Kort svar renders no toggle either.
 *
 * jsdom has no layout, so selections are set through TipTap commands, word
 * clicks reach the view through its own click handler, Ctrl+Alt+G is a real
 * `keydown` with the key code ProseMirror's keymap reads, and the popover
 * is teleported to `document.body`, so specs query the document for it.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { Editor } from "@tiptap/core";
import { afterEach, describe, expect, it } from "vitest";
import { defineComponent, h, nextTick, ref } from "vue";

import type {
  NativeExamBodyParagraph,
  NativeExamItem,
} from "../../../api/examWorkspace";
import ExamWorkspaceBodyEditor from "./ExamWorkspaceBodyEditor.vue";
import ExamWorkspaceRichTextEditor from "./ExamWorkspaceRichTextEditor.vue";
import ExamWorkspaceShortAnswerField from "./ExamWorkspaceShortAnswerField.vue";
import {
  buildGapItem,
  popoverExists,
  posIn,
} from "./ExamWorkspaceBodyEditor.specSupport";
import { withBody, newTeacherItem } from "./examWorkspaceItemEdits";
import { buildGap } from "./examWorkspaceKeyedItems.specSupport";
import { withNewGap } from "./examWorkspaceGapEdits";
import { plainBody } from "./examWorkspaceRichText";

const TOOLBAR_GAP_TOOL = '[data-test="exam-workspace-toolbar-gap-tool"]';
const FLOATING_GAP = '[data-test="exam-workspace-make-gap"]';
const GAP_AT_CAP = "Högst 999 luckor";

/** Mount the body editor inside a small owner that applies each edit like the real store. */
function mountHarness(item: NativeExamItem) {
  const current = ref(item);
  const locked = ref(false);
  const Host = defineComponent({
    setup() {
      return () =>
        h(ExamWorkspaceBodyEditor, {
          item: current.value,
          disabled: locked.value,
          onCreateGap: (
            itemId: string,
            body: NativeExamBodyParagraph[],
            gapId: string,
            seed: string,
          ) => {
            current.value = withNewGap(current.value, body, gapId, seed);
            void itemId;
          },
          onUpdateBody: (
            itemId: string,
            body: NativeExamBodyParagraph[],
            structural: boolean,
          ) => {
            current.value = withBody(current.value, body);
            void itemId;
            void structural;
          },
        });
    },
  });
  const host = mount(Host, { attachTo: document.body });
  mounted.push(host);
  return {
    host,
    setItem: (next: NativeExamItem): void => {
      current.value = next;
    },
    setDisabled: (value: boolean): void => {
      locked.value = value;
    },
  };
}

type Harness = ReturnType<typeof mountHarness>;

const mounted: Array<{ unmount: () => void }> = [];

afterEach(() => {
  while (mounted.length > 0) {
    mounted.pop()?.unmount();
  }
  document.body.innerHTML = "";
});

function track<T extends { unmount: () => void }>(wrapper: T): T {
  mounted.push(wrapper);
  return wrapper;
}

function bodyEditorOf(harness: Harness) {
  return harness.host.findComponent(ExamWorkspaceBodyEditor);
}

function richEditorOf(harness: Harness) {
  return harness.host.findComponent(ExamWorkspaceRichTextEditor);
}

function creationsOf(harness: Harness): unknown[][] {
  return bodyEditorOf(harness).emitted("createGap") ?? [];
}

function updatesOf(harness: Harness): unknown[][] {
  return bodyEditorOf(harness).emitted("updateBody") ?? [];
}

function toolToggle(harness: Harness) {
  return harness.host.find(TOOLBAR_GAP_TOOL);
}

function toolPressed(harness: Harness): string | undefined {
  return toolToggle(harness).attributes("aria-pressed");
}

function surfaceOf(harness: Harness): HTMLElement {
  const surface = harness.host.get('[data-test="exam-workspace-body-editor-surface"]').element;
  if (!(surface instanceof HTMLElement)) {
    throw new Error("the question text editor surface is not an element");
  }
  return surface;
}

function innerEditor(harness: Harness): Editor {
  const surface = surfaceOf(harness);
  if (!("editor" in surface)) {
    throw new Error("the question text editor did not mount");
  }
  const candidate = surface.editor;
  if (!(candidate instanceof Editor)) {
    throw new Error("the question text editor did not mount");
  }
  return candidate;
}

/** A primary click at `pos` that leaves the caret behind, as a mousedown would. */
function clickAt(editor: Editor, pos: number): void {
  editor.view.someProp("handleClick", (handler) =>
    handler(editor.view, pos, new MouseEvent("click", { bubbles: true, cancelable: true })),
  );
}

/** Click the word, setting the caret first as a real pointer press would. */
function clickWord(harness: Harness, word: string): void {
  const editor = innerEditor(harness);
  const pos = posIn(editor, word, 1);
  editor.commands.setTextSelection(pos);
  clickAt(editor, pos);
}

/** Ctrl+Alt+G as ProseMirror's keymap reads it: the key code comes from `keyCode`, as browsers set it. */
function pressGapShortcut(target: HTMLElement): void {
  const event = new KeyboardEvent("keydown", {
    key: "g",
    bubbles: true,
    cancelable: true,
    ctrlKey: true,
    altKey: true,
  });
  Object.defineProperty(event, "keyCode", { value: 71 });
  Object.defineProperty(event, "which", { value: 71 });
  target.dispatchEvent(event);
}

function pressEscape(target: HTMLElement): void {
  target.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true }));
}

/** Activate a gap as a click on its chip does, through the view's own click handler. */
function clickGapChip(harness: Harness, gapId: string): void {
  const editor = innerEditor(harness);
  let pos = -1;
  editor.state.doc.descendants((node, nodePos) => {
    if (pos < 0 && node.type.name === "examGap" && node.attrs.gapId === gapId) {
      pos = nodePos;
    }
    return pos < 0;
  });
  if (pos < 0) {
    throw new Error(`no gap ${gapId}`);
  }
  const node = editor.state.doc.nodeAt(pos);
  if (!node) {
    throw new Error(`no gap ${gapId}`);
  }
  editor.view.someProp("handleClickOn", (handler) =>
    handler(editor.view, pos, node, pos, new MouseEvent("click"), true),
  );
}

async function settle(): Promise<void> {
  await nextTick();
  await nextTick();
  await flushPromises();
}

function plainGapItem(): NativeExamItem {
  return buildGapItem({
    body: [
      {
        heading_level: null,
        segments: [
          { kind: "text", marks: [], text: "Solen är en stjärna och månen en satellit." },
        ],
      },
    ],
    gaps: [],
  });
}

function capItem(): NativeExamItem {
  return buildGapItem({
    body: [
      {
        heading_level: null,
        segments: [
          { kind: "text", marks: [], text: "Svar " },
          { gap_id: "gap_999", kind: "gap" },
        ],
      },
    ],
    gaps: [buildGap("gap_999", ["hundra"])],
  });
}

describe("ExamWorkspaceBodyEditor gap tool", () => {
  it("turns three word clicks into three gaps with no popover while the tool is on", async () => {
    const harness = mountHarness(plainGapItem());
    await settle();

    await toolToggle(harness).trigger("click");
    await settle();
    expect(toolPressed(harness)).toBe("true");
    expect(richEditorOf(harness).props("gapTool")).toBe(true);

    for (const [index, word] of ["Solen", "stjärna", "satellit"].entries()) {
      clickWord(harness, word);
      await settle();

      const creations = creationsOf(harness);
      expect(creations).toHaveLength(index + 1);
      expect(updatesOf(harness)).toHaveLength(0);
      const [itemId, , gapId, seed] = creations[index]!;
      expect(itemId).toBe("item_001");
      expect(gapId).toBe(`gap_00${index + 1}`);
      expect(seed).toBe(word);
      expect(popoverExists()).toBe(false);
      expect(document.querySelector(FLOATING_GAP)).toBeNull();
    }
  });

  it("shows the floating button again after the tool is switched off", async () => {
    const harness = mountHarness(plainGapItem());
    await settle();

    await toolToggle(harness).trigger("click");
    await settle();
    expect(toolPressed(harness)).toBe("true");
    await toolToggle(harness).trigger("click");
    await settle();
    expect(toolPressed(harness)).toBe("false");
    expect(richEditorOf(harness).props("gapTool")).toBe(false);

    clickWord(harness, "stjärna");
    await settle();

    expect(document.querySelector(FLOATING_GAP)).not.toBeNull();
    expect(creationsOf(harness)).toHaveLength(0);
    expect(popoverExists()).toBe(false);
  });

  it("toggles the tool with Ctrl+Alt+G and follows with the toolbar pressed state", async () => {
    const harness = mountHarness(plainGapItem());
    await settle();

    pressGapShortcut(surfaceOf(harness));
    await settle();
    expect(toolPressed(harness)).toBe("true");
    expect(richEditorOf(harness).props("gapTool")).toBe(true);

    pressGapShortcut(surfaceOf(harness));
    await settle();
    expect(toolPressed(harness)).toBe("false");
    expect(richEditorOf(harness).props("gapTool")).toBe(false);
    expect(creationsOf(harness)).toHaveLength(0);
  });

  it("closes an open popover on Escape first and the tool on the next Escape", async () => {
    const harness = mountHarness(buildGapItem());
    await settle();

    await toolToggle(harness).trigger("click");
    await settle();
    clickGapChip(harness, "gap_001");
    await settle();
    expect(popoverExists()).toBe(true);

    pressEscape(surfaceOf(harness));
    await settle();
    expect(popoverExists()).toBe(false);
    expect(toolPressed(harness)).toBe("true");

    pressEscape(surfaceOf(harness));
    await settle();
    expect(toolPressed(harness)).toBe("false");
  });

  it("turns the tool off when the teacher moves to another question", async () => {
    const harness = mountHarness(plainGapItem());
    await settle();

    await toolToggle(harness).trigger("click");
    await settle();
    expect(toolPressed(harness)).toBe("true");

    harness.setItem({ ...buildGapItem(), item_id: "item_002" });
    await settle();

    expect(toolPressed(harness)).toBe("false");
    expect(richEditorOf(harness).props("gapTool")).toBe(false);
    expect(bodyEditorOf(harness).props("item").item_id).toBe("item_002");
  });

  it("turns the tool off while disabled and the toggle and shortcut cannot turn it on", async () => {
    const harness = mountHarness(plainGapItem());
    await settle();

    await toolToggle(harness).trigger("click");
    await settle();
    expect(toolPressed(harness)).toBe("true");

    harness.setDisabled(true);
    await settle();

    expect(toolPressed(harness)).toBe("false");
    expect(toolToggle(harness).attributes("disabled")).toBeDefined();
    await toolToggle(harness).trigger("click");
    await settle();
    expect(toolPressed(harness)).toBe("false");
    pressGapShortcut(surfaceOf(harness));
    await settle();
    expect(toolPressed(harness)).toBe("false");
    expect(creationsOf(harness)).toHaveLength(0);
  });

  it("turns the tool off at the gap_999 cap and disables the toggle", async () => {
    const harness = mountHarness(plainGapItem());
    await settle();

    await toolToggle(harness).trigger("click");
    await settle();
    expect(toolPressed(harness)).toBe("true");

    harness.setItem(capItem());
    await settle();

    const toggle = toolToggle(harness);
    expect(toolPressed(harness)).toBe("false");
    expect(toggle.attributes("disabled")).toBeDefined();
    expect(toggle.attributes("title")).toBe(GAP_AT_CAP);
    await toggle.trigger("click");
    await settle();
    expect(toolPressed(harness)).toBe("false");
    expect(creationsOf(harness)).toHaveLength(0);
  });

  it("shows no toggle for free text and the shortcut does nothing there", async () => {
    const harness = mountHarness(
      buildGapItem({ kind: "free_text", body: plainBody("Solen lyser."), gaps: [] }),
    );
    await settle();

    expect(harness.host.find(TOOLBAR_GAP_TOOL).exists()).toBe(false);

    pressGapShortcut(surfaceOf(harness));
    await settle();

    expect(richEditorOf(harness).props("gapTool")).toBe(false);
    expect(creationsOf(harness)).toHaveLength(0);
    expect(updatesOf(harness)).toHaveLength(0);
  });

  it("renders no gap tool toggle in the Kort svar field", async () => {
    const item: NativeExamItem = {
      ...newTeacherItem("item_001", 1, "gap_fill"),
      body: [
        ...plainBody("Vad heter Sveriges huvudstad?"),
        { heading_level: null, segments: [{ kind: "gap", gap_id: "gap_001" }] },
      ],
      gaps: [buildGap("gap_001", ["Stockholm"])],
    };
    const wrapper = track(
      mount(ExamWorkspaceShortAnswerField, { props: { item }, attachTo: document.body }),
    );
    await settle();

    expect(wrapper.find(TOOLBAR_GAP_TOOL).exists()).toBe(false);
  });
});
