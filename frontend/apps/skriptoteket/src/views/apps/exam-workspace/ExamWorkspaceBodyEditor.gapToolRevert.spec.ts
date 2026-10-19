/**
 * Exam workspace question-text editor: the gap tool revert and restore clicks.
 *
 * Expected behavior (TASK-SKRIPT-40-04-13 items 1, 3 and 6, unit H4):
 *   With the tool on, a gap click reverts it through `revertGap` (the owner
 *   applies `withGapReverted` as one structural edit) instead of opening its
 *   popover; with the tool off the chip opens its popover as today. With the
 *   tool on, a kept-word click restores the gap through `restoreKeptGap` with
 *   the clicked block's index. While disabled, neither click forwards.
 *
 * jsdom has no layout, so selections are set through TipTap commands, word
 * clicks reach the view through its own click handler, a gap click calls the
 * view's click handler, and the popover is teleported to `document.body`.
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
import {
  buildGapItem,
  popoverExists,
  posIn,
} from "./ExamWorkspaceBodyEditor.specSupport";
import {
  dispatchGapToolClick,
  gapPointerMiddle,
  stubLinearGapPointerGeometry,
} from "./examWorkspaceGapToolPointer.specSupport";
import { withBody } from "./examWorkspaceItemEdits";
import { withNewGap } from "./examWorkspaceGapEdits";
import { withGapReverted, withKeptGapRestored } from "./examWorkspaceKeptGapEdits";
import { buildGap } from "./examWorkspaceKeyedItems.specSupport";

const TOOLBAR_GAP_TOOL = '[data-test="exam-workspace-toolbar-gap-tool"]';

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
          onRevertGap: (itemId: string, gapId: string) => {
            current.value = withGapReverted(current.value, gapId);
            void itemId;
          },
          onRestoreKeptGap: (itemId: string, keptGapId: string, blockIndex: number) => {
            current.value = withKeptGapRestored(current.value, keptGapId, blockIndex);
            void itemId;
          },
        });
    },
  });
  const host = mount(Host, { attachTo: document.body });
  mounted.push(host);
  return {
    host,
    item: (): NativeExamItem => current.value,
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

function richEditorOf(harness: Harness) {
  return harness.host.findComponent(ExamWorkspaceRichTextEditor);
}

function innerEditor(harness: Harness): Editor {
  const surface = harness.host.get('[data-test="exam-workspace-body-editor-surface"]').element;
  if (!(surface instanceof HTMLElement) || !("editor" in surface)) {
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

/** A gap click as the view's own click handler sees it, carrying the given click count. */
function clickGapChip(harness: Harness, gapId: string, detail: number): unknown {
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
  let result: unknown;
  editor.view.someProp("handleClickOn", (handler) => {
    result = handler(
      editor.view,
      pos,
      node,
      pos,
      new MouseEvent("click", { bubbles: true, cancelable: true, detail }),
      true,
    );
    return result;
  });
  return result;
}

async function settle(): Promise<void> {
  await nextTick();
  await nextTick();
  await flushPromises();
}

function revertedItem(): NativeExamItem {
  return withGapReverted(
    buildGapItem({
      body: [
        {
          heading_level: null,
          segments: [
            { kind: "text", marks: [], text: "Vatten kokar vid ", kept_gap_id: null },
            { gap_id: "gap_001", kind: "gap" },
            { kind: "text", marks: [], text: " grader.", kept_gap_id: null },
          ],
        },
      ],
      gaps: [buildGap("gap_001", ["100"])],
    }),
    "gap_001",
  );
}

describe("ExamWorkspaceBodyEditor gap tool revert and restore", () => {
  it("with the tool on, a gap click reverts it and opens no popover", async () => {
    const harness = mountHarness(buildGapItem());
    await settle();

    await harness.host.find(TOOLBAR_GAP_TOOL).trigger("click");
    await settle();
    expect(richEditorOf(harness).props("gapTool")).toBe(true);

    clickGapChip(harness, "gap_001", 1);
    await settle();

    expect(popoverExists()).toBe(false);
    const item = harness.item();
    expect(item.gaps.map((gap) => gap.gap_id)).toEqual(["gap_002"]);
    expect(item.kept_gaps).toHaveLength(1);
    expect(
      harness.host.findComponent(ExamWorkspaceBodyEditor).emitted("revertGap"),
    ).toEqual([["item_001", "gap_001"]]);
  });

  it("with the tool off, a gap click opens its popover and reverts nothing", async () => {
    const harness = mountHarness(buildGapItem());
    await settle();
    expect(richEditorOf(harness).props("gapTool")).toBe(false);

    clickGapChip(harness, "gap_001", 1);
    await settle();

    expect(popoverExists()).toBe(true);
    expect(harness.item().gaps.map((gap) => gap.gap_id)).toEqual(["gap_001", "gap_002"]);
    expect(harness.item().kept_gaps).toEqual([]);
    expect(
      harness.host.findComponent(ExamWorkspaceBodyEditor).emitted("revertGap"),
    ).toBeUndefined();
  });

  it("with the tool on, a kept-word click restores the gap", async () => {
    const harness = mountHarness(revertedItem());
    await settle();

    await harness.host.find(TOOLBAR_GAP_TOOL).trigger("click");
    await settle();

    clickWord(harness, "100");
    await settle();

    const item = harness.item();
    expect(item.gaps).toHaveLength(1);
    expect(item.kept_gaps).toEqual([]);
    expect(item.gaps[0]?.accepted_values).toEqual(["100"]);
    expect(
      harness.host.findComponent(ExamWorkspaceBodyEditor).emitted("restoreKeptGap"),
    ).toEqual([["item_001", item.gaps[0]?.gap_id ?? "", 0]]);
  });

  it("while disabled, a gap click and a kept-word click forward nothing", async () => {
    const harness = mountHarness(buildGapItem());
    await settle();

    await harness.host.find(TOOLBAR_GAP_TOOL).trigger("click");
    await settle();
    harness.setDisabled(true);
    await settle();

    clickGapChip(harness, "gap_001", 1);
    await settle();

    expect(popoverExists()).toBe(false);
    expect(harness.item().gaps.map((gap) => gap.gap_id)).toEqual(["gap_001", "gap_002"]);
    expect(
      harness.host.findComponent(ExamWorkspaceBodyEditor).emitted("revertGap"),
    ).toBeUndefined();
  });
});
