/**
 * Exam workspace question-text editor spec support.
 *
 * Purpose:
 *   Shared fixture and mount helpers for the `ExamWorkspaceBodyEditor` specs:
 *   a gap-fill item with two gaps (one keyed, one empty) and an image marker,
 *   a mounted editor attached to the document, and TipTap helpers. jsdom has
 *   no layout, so selections are set through TipTap commands and a gap click
 *   calls the view's click handler; every key is a real `keydown`.
 */

import { mount } from "@vue/test-utils";
import type { Editor } from "@tiptap/core";
import { nextTick } from "vue";

import type { NativeExamItem } from "../../../api/examWorkspace";
import ExamWorkspaceBodyEditor from "./ExamWorkspaceBodyEditor.vue";
import { buildGap } from "./examWorkspaceKeyedItems.specSupport";

export function buildGapItem(overrides: Partial<NativeExamItem> = {}): NativeExamItem {
  return {
    ai_suggestion: null,
    facit_text: null,
    import_record: null,
    criteria: [],
    printed_label: null,
    print_order: [],
    retry_source: null,
    answer_key: { correct_choice_ids: [], match_pairs: [], origin: "teacher_authored" },
    body: [
      { heading_level: null, segments: [
          { kind: "text", marks: [], text: "Vatten kokar vid " },
          { gap_id: "gap_001", kind: "gap" },
          { kind: "text", marks: [], text: " grader och fryser vid " },
          { gap_id: "gap_002", kind: "gap" },
          { kind: "text", marks: [], text: " grader." },
        ],
      },
      { heading_level: null, segments: [{ kind: "text", marks: [], text: "Se " }, { asset_id: "asset_001", kind: "asset" }] },
    ],
    choices: [],
    gaps: [
      buildGap("gap_001", ["100"]),
      buildGap("gap_002"),
    ],
    item_id: "item_001",
    kind: "gap_fill",
    match_left: [],
    match_right: [],
    points: 1,
    points_estimated: false,
    review: {
      confidence: 0.95,
      parse_origin: "deterministic",
      reasons: [],
      state: "review_complete",
    },
    sequence: 1,
    source_anchor: null,
    suggested_kind: null,
    tick_points: null,
    ...overrides,
  };
}

/**
 * A gap-fill item whose first paragraph ends with a gap and whose second
 * starts with a picture: "A [gap_001] B [gap_002] C" and "[asset_001] D".
 */
export function buildMergeItem(): NativeExamItem {
  return buildGapItem({
    body: [
      {
        heading_level: null,
        segments: [
          { kind: "text", marks: [], text: "A " },
          { gap_id: "gap_001", kind: "gap" },
          { kind: "text", marks: [], text: " B " },
          { gap_id: "gap_002", kind: "gap" },
          { kind: "text", marks: [], text: " C" },
        ],
      },
      {
        heading_level: null,
        segments: [{ asset_id: "asset_001", kind: "asset" }, { kind: "text", marks: [], text: " D" }],
      },
    ],
  });
}

/**
 * Mount the editor with its props, wait for TipTap to build the surface, and
 * hand back the wrapper. `props` can carry `assetUrls` and `disabled`.
 */
export async function mountEditor(
  item: NativeExamItem = buildGapItem(),
  props: { assetUrls?: Record<string, string>; disabled?: boolean } = {},
) {
  const wrapper = mount(ExamWorkspaceBodyEditor, { props: { item, ...props }, attachTo: document.body });
  await nextTick();
  await nextTick();
  return wrapper;
}

export type MountedBodyEditor = Awaited<ReturnType<typeof mountEditor>>;

/** The question text's editing surface (the ProseMirror DOM). */
export function surface(wrapper: MountedBodyEditor): HTMLElement {
  return wrapper.get('[data-test="exam-workspace-body-editor-surface"]').element as HTMLElement;
}

/** The TipTap editor behind the surface, to set selections jsdom cannot place by pointer. */
export function tiptap(wrapper: MountedBodyEditor): Editor {
  const { editor } = surface(wrapper) as HTMLElement & { editor?: Editor };
  if (!editor) {
    throw new Error("the question text editor did not mount");
  }
  return editor;
}

/** Position `offset` characters into the first text node that contains `needle`. */
export function posIn(editor: Editor, needle: string, offset: number): number {
  let found = -1;
  editor.state.doc.descendants((node, pos) => {
    if (found < 0 && node.isText && node.text?.includes(needle)) {
      found = pos + (node.text.indexOf(needle) + offset);
    }
    return found < 0;
  });
  if (found < 0) {
    throw new Error(`no text "${needle}"`);
  }
  return found;
}

/** Position of the first atom of a node type (`examGap` or `examPicture`) whose attribute matches. */
export function atomPos(editor: Editor, type: string, id: string): number {
  let found = -1;
  editor.state.doc.descendants((node, pos) => {
    if (found < 0 && node.type.name === type && Object.values(node.attrs).includes(id)) {
      found = pos;
    }
    return found < 0;
  });
  if (found < 0) {
    throw new Error(`no ${type} ${id}`);
  }
  return found;
}

/** A real `keydown` on the surface; ProseMirror's own delete handling reads `keyCode`, as browsers set it. */
export function press(
  target: HTMLElement,
  key: string,
  modifiers: { shiftKey?: boolean; ctrlKey?: boolean; metaKey?: boolean } = {},
): KeyboardEvent {
  const keyCode = { Backspace: 8, Enter: 13, Delete: 46 }[key];
  const event = new KeyboardEvent("keydown", { key, keyCode, bubbles: true, cancelable: true, ...modifiers });
  target.dispatchEvent(event);
  return event;
}

/**
 * Activate a gap as a click on it does. jsdom has no layout, so the view's own
 * click handler (`handleClickOn`) is called with the gap as the clicked node.
 */
export function clickGap(wrapper: MountedBodyEditor, gapId: string): void {
  const editor = tiptap(wrapper);
  const pos = atomPos(editor, "examGap", gapId);
  const node = editor.state.doc.nodeAt(pos)!;
  editor.view.someProp("handleClickOn", (handler) =>
    handler(editor.view, pos, node, pos, new MouseEvent("click"), true),
  );
}

/** The drawn element of one gap. */
export function gapElement(wrapper: MountedBodyEditor, gapId: string): HTMLElement {
  return wrapper.get(`[data-gap-id="${gapId}"]`).element as HTMLElement;
}
