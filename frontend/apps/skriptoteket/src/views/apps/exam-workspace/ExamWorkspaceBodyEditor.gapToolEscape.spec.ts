/**
 * Exam workspace question-text editor: one Escape with a gap popover open closes only the popover.
 *
 * Expected behavior (TASK-SKRIPT-40-04-09 L4):
 *   With the gap tool on and a gap popover open, one Escape closes the
 *   popover, keeps the tool on and returns focus to the question text. With
 *   no popover open, Escape turns the tool off. A repeated Escape keydown in
 *   the same press must not turn the tool off.
 *
 * jsdom has no layout, so word clicks reach the view through its own click
 * handler, Escape is a real `keydown` (ProseMirror's `handleKeyDown` reads it
 * off the surface element, the popover's `@keydown` off its teleported
 * root), and the popover is teleported to `document.body`, so specs query
 * the document for it.
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
import {
  buildGapItem,
  documentControl,
  popoverExists,
  popoverInput,
  posIn,
} from "./ExamWorkspaceBodyEditor.specSupport";
import {
  dispatchGapToolClick,
  gapPointerMiddle,
  stubLinearGapPointerGeometry,
} from "./examWorkspaceGapToolPointer.specSupport";
import { withBody } from "./examWorkspaceItemEdits";
import { withNewGap } from "./examWorkspaceGapEdits";
import { buildGap } from "./examWorkspaceKeyedItems.specSupport";
import { plainBody } from "./examWorkspaceRichText";

const TOOLBAR_GAP_TOOL = '[data-test="exam-workspace-toolbar-gap-tool"]';
const BODY_EDITOR_ROOT = '[data-test="exam-workspace-body-editor"]';
const BODY_EDITOR_SURFACE = '[data-test="exam-workspace-body-editor-surface"]';

/** Mount the body editor inside a small owner that applies each edit like the real store. */
function mountHarness(item: NativeExamItem) {
  const current = ref(item);
  const Host = defineComponent({
    setup() {
      return () =>
        h(ExamWorkspaceBodyEditor, {
          item: current.value,
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
  return { host };
}

type Harness = ReturnType<typeof mountHarness>;

const mounted: Array<{ unmount: () => void }> = [];

afterEach(() => {
  while (mounted.length > 0) {
    mounted.pop()?.unmount();
  }
  document.body.innerHTML = "";
});

function toolToggle(harness: Harness) {
  return harness.host.find(TOOLBAR_GAP_TOOL);
}

function toolPressed(harness: Harness): string | undefined {
  return toolToggle(harness).attributes("aria-pressed");
}

function bodyRoot(harness: Harness): HTMLElement {
  const root = harness.host.get(BODY_EDITOR_ROOT).element;
  if (!(root instanceof HTMLElement)) {
    throw new Error("the body editor root is not an element");
  }
  return root;
}

function surfaceOf(harness: Harness): HTMLElement {
  const surface = harness.host.get(BODY_EDITOR_SURFACE).element;
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

/** Click the word, setting the caret first as a real pointer press would. */
function clickWord(harness: Harness, word: string): void {
  const editor = innerEditor(harness);
  stubLinearGapPointerGeometry(editor);
  const pos = posIn(editor, word, 1);
  editor.commands.setTextSelection(pos);
  dispatchGapToolClick(editor, pos, gapPointerMiddle(pos));
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

function dispatchEscape(target: HTMLElement, init: KeyboardEventInit = {}): void {
  target.dispatchEvent(
    new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true, ...init }),
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

/** A dropdown question with one optioned gap, for the inline-choice popover. */
function dropdownGapItem(): NativeExamItem {
  return buildGapItem({
    kind: "inline_choice",
    gaps: [
      buildGap("gap_001", [], {
        correct_option_id: "choice_001",
        options: [
          { body: plainBody("zebra"), choice_id: "choice_001" },
          { body: plainBody("apa"), choice_id: "choice_002" },
        ],
      }),
      buildGap("gap_002", []),
    ],
  });
}

function requireInput(element: Element | null, what: string): HTMLInputElement {
  if (!(element instanceof HTMLInputElement)) {
    throw new Error(`${what} is not focused in an input`);
  }
  return element;
}

/**
 * Switch the tool on, make one gap with a tool click, and open its popover
 * with a chip click. Returns the made gap's id.
 */
async function openToolMadePopover(harness: Harness): Promise<string> {
  await toolToggle(harness).trigger("click");
  await settle();
  expect(toolPressed(harness)).toBe("true");

  clickWord(harness, "Solen");
  await settle();
  const creations = harness.host.findComponent(ExamWorkspaceBodyEditor).emitted("createGap") ?? [];
  expect(creations).toHaveLength(1);
  const gapId = creations[0]![2];
  expect(gapId).toBe("gap_001");
  expect(popoverExists()).toBe(false);

  clickGapChip(harness, "gap_001");
  await settle();
  expect(popoverExists()).toBe(true);
  return "gap_001";
}

describe("ExamWorkspaceBodyEditor gap tool Escape", () => {
  it("closes the popover on Escape in its first input and keeps the tool on, then the tool ends", async () => {
    const harness = mountHarness(plainGapItem());
    await settle();
    const gapId = await openToolMadePopover(harness);

    const firstInput = popoverInput(gapId).element;
    expect(document.activeElement).toBe(firstInput);

    dispatchEscape(requireInput(document.activeElement, "the popover answer"));
    await settle();

    expect(popoverExists()).toBe(false);
    expect(toolPressed(harness)).toBe("true");
    expect(document.activeElement).toBe(surfaceOf(harness));

    dispatchEscape(surfaceOf(harness));
    await settle();
    expect(popoverExists()).toBe(false);
    expect(toolPressed(harness)).toBe("false");
  });

  it("closes the popover on Escape in the surface and keeps the tool on, then the tool ends", async () => {
    const harness = mountHarness(plainGapItem());
    await settle();
    await openToolMadePopover(harness);

    dispatchEscape(surfaceOf(harness));
    await settle();

    expect(popoverExists()).toBe(false);
    expect(toolPressed(harness)).toBe("true");
    expect(document.activeElement).toBe(surfaceOf(harness));

    dispatchEscape(surfaceOf(harness));
    await settle();
    expect(toolPressed(harness)).toBe("false");
  });

  it("closes the popover on Escape with typed, uncommitted text and keeps the tool on", async () => {
    const harness = mountHarness(plainGapItem());
    await settle();
    const gapId = await openToolMadePopover(harness);

    const input = popoverInput(gapId);
    input.setValue("solen skin");
    expect(input.element.value).toBe("solen skin");

    dispatchEscape(input.element);
    await settle();

    expect(popoverExists()).toBe(false);
    expect(toolPressed(harness)).toBe("true");
  });

  it("ignores a repeated Escape in a text-gap popover and keeps the typed draft", async () => {
    const harness = mountHarness(plainGapItem());
    await settle();
    const gapId = await openToolMadePopover(harness);

    const input = popoverInput(gapId);
    await input.setValue("solen skin");
    expect(input.element.value).toBe("solen skin");

    dispatchEscape(input.element, { repeat: true });
    await settle();

    expect(popoverExists()).toBe(true);
    expect(popoverInput(gapId).element.value).toBe("solen skin");
    expect(toolPressed(harness)).toBe("true");

    dispatchEscape(popoverInput(gapId).element);
    await settle();

    expect(popoverExists()).toBe(false);
    expect(toolPressed(harness)).toBe("true");
  });

  it("ignores a repeated Escape in a dropdown popover and keeps the typed option draft", async () => {
    const harness = mountHarness(dropdownGapItem());
    await settle();
    await toolToggle(harness).trigger("click");
    await settle();
    expect(toolPressed(harness)).toBe("true");

    clickGapChip(harness, "gap_001");
    await settle();
    expect(popoverExists()).toBe(true);

    const option = documentControl<HTMLInputElement>(
      '[data-test="exam-workspace-gap-option-text-choice_001"]',
    );
    option.element.value = "zebra randig";
    await option.trigger("input");
    expect(option.element.value).toBe("zebra randig");

    dispatchEscape(option.element, { repeat: true });
    await settle();

    expect(popoverExists()).toBe(true);
    expect(
      documentControl<HTMLInputElement>(
        '[data-test="exam-workspace-gap-option-text-choice_001"]',
      ).element.value,
    ).toBe("zebra randig");
    expect(toolPressed(harness)).toBe("true");

    dispatchEscape(
      documentControl<HTMLInputElement>(
        '[data-test="exam-workspace-gap-option-text-choice_001"]',
      ).element,
    );
    await settle();

    expect(popoverExists()).toBe(false);
    expect(toolPressed(harness)).toBe("true");
  });

  it("returns focus inside the body editor root when the popover closes, through a chip re-render", async () => {
    const harness = mountHarness(plainGapItem());
    await settle();
    await openToolMadePopover(harness);

    const root = bodyRoot(harness);
    const outside: EventTarget[] = [];
    const onFocusIn = (event: FocusEvent): void => {
      const target = event.target;
      if (target instanceof Node && !root.contains(target)) {
        outside.push(target);
      }
    };
    document.addEventListener("focusin", onFocusIn);
    try {
      // Opening moves focus into the teleported popover by design; only the
      // close and what follows must stay inside the root.
      outside.length = 0;

      dispatchEscape(requireInput(document.activeElement, "the popover answer"));
      await settle();
      expect(popoverExists()).toBe(false);
      expect(toolPressed(harness)).toBe("true");

      // Re-render the closed gap's chip with a body edit, as the owner's
      // write-back does; focus must not leave the root through it either.
      const editor = innerEditor(harness);
      editor.commands.insertContentAt(posIn(editor, "satellit", 1), "x");
      await settle();

      expect(popoverExists()).toBe(false);
      expect(toolPressed(harness)).toBe("true");
      expect(outside).toHaveLength(0);
      expect(root.contains(document.activeElement)).toBe(true);
    } finally {
      document.removeEventListener("focusin", onFocusIn);
    }
  });

  it("does not turn the tool off on a repeated Escape keydown in the same press", async () => {
    const harness = mountHarness(plainGapItem());
    await settle();
    await openToolMadePopover(harness);

    // The held key's first keydown closes the popover from its input.
    dispatchEscape(requireInput(document.activeElement, "the popover answer"));
    await settle();
    expect(popoverExists()).toBe(false);
    expect(toolPressed(harness)).toBe("true");

    const surface = surfaceOf(harness);
    expect(document.activeElement).toBe(surface);
    surface.dispatchEvent(new KeyboardEvent("keyup", { key: "Escape", bubbles: true }));

    const repeated = new KeyboardEvent("keydown", {
      key: "Escape",
      bubbles: true,
      cancelable: true,
      repeat: true,
    });
    expect(repeated.repeat).toBe(true);
    document.activeElement?.dispatchEvent(repeated);
    await settle();

    expect(popoverExists()).toBe(false);
    expect(toolPressed(harness)).toBe("true");
  });
});
