/**
 * Exam workspace question-text editor: the Tom lucka emit and the empty gap's lifetime.
 *
 * Expected behavior (TASK-SKRIPT-40-04-13 Behaviour 9 and 10, L3):
 *   The toolbar's `insertEmptyGap` emit inserts an empty gap at the caret
 *   through `insertEmptyGapAtCursor`, with the gap tool on or off, and the new
 *   gap's popover opens at once. The command is refused for a question that is
 *   not a gap question and at the gap cap. An empty gap stays while its
 *   question is edited: closing its popover (Escape, a click outside) removes
 *   nothing. Removing empty gaps on leaving the question belongs to the
 *   selection layer, so this editor emits no body change for it.
 *
 * jsdom has no layout, so the caret is set through TipTap commands and the
 * popover is teleported to `document.body`, so specs query the document.
 */

import { flushPromises, mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import { Editor } from "@tiptap/core";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent, h, nextTick, ref } from "vue";

import type {
  NativeExamBodyParagraph,
  NativeExamChoice,
  NativeExamItem,
} from "../../../api/examWorkspace";
import ExamWorkspaceBodyEditor from "./ExamWorkspaceBodyEditor.vue";
import ExamWorkspaceMarkToolbar from "./ExamWorkspaceMarkToolbar.vue";
import {
  buildGapItem,
  popoverExists,
  posIn,
} from "./ExamWorkspaceBodyEditor.specSupport";
import { buildGap } from "./examWorkspaceKeyedItems.specSupport";
import { withBody } from "./examWorkspaceItemEdits";
import { withGapOptions, withGapValues, withNewGap } from "./examWorkspaceGapEdits";
import { placedGapIds } from "./examWorkspaceRichTextDocument";

const toast = vi.hoisted(() => ({ failure: vi.fn(), warning: vi.fn() }));

vi.mock("../../../composables/useToast", () => ({ useToast: () => toast }));

beforeEach(() => {
  for (const fn of Object.values(toast)) fn.mockReset();
});

afterEach(() => {
  document.body.innerHTML = "";
});

type UpdateBodyEvent = [string, NativeExamBodyParagraph[], boolean];
type CreateGapEvent = [string, NativeExamBodyParagraph[], string, string];

const harnessItem = ref<NativeExamItem>(buildGapItem());
const harnessDisabled = ref(false);

/** The one host component of this file: the body editor on a teacher-owned item and disabled flag. */
const Host = defineComponent({
  setup() {
    return () =>
      h(ExamWorkspaceBodyEditor, {
        item: harnessItem.value,
        disabled: harnessDisabled.value,
        onCreateGap: (
          itemId: string,
          body: NativeExamBodyParagraph[],
          gapId: string,
          seed: string,
        ) => {
          harnessItem.value = withNewGap(harnessItem.value, body, gapId, seed);
          void itemId;
        },
        onUpdateBody: (
          itemId: string,
          body: NativeExamBodyParagraph[],
          structural: boolean,
        ) => {
          harnessItem.value = withBody(harnessItem.value, body);
          void itemId;
          void structural;
        },
        onUpdateGapValues: (itemId: string, gapId: string, acceptedValues: string[]) => {
          harnessItem.value = withGapValues(harnessItem.value, gapId, acceptedValues);
          void itemId;
        },
        onUpdateGapOptions: (
          itemId: string,
          gapId: string,
          options: NativeExamChoice[],
          correctOptionId: string | null,
          structural: boolean,
        ) => {
          harnessItem.value = withGapOptions(harnessItem.value, gapId, options, correctOptionId);
          void itemId;
          void structural;
        },
      });
  },
});

type Harness = {
  host: VueWrapper;
  setItem: (next: NativeExamItem) => void;
  setDisabled: (value: boolean) => void;
};

/** Mount the body editor inside a small owner that applies each edit like the real store. */
function mountHarness(item: NativeExamItem): Harness {
  harnessItem.value = item;
  harnessDisabled.value = false;
  return {
    host: mount(Host, { attachTo: document.body }),
    setItem: (next: NativeExamItem): void => {
      harnessItem.value = next;
    },
    setDisabled: (value: boolean): void => {
      harnessDisabled.value = value;
    },
  };
}

function bodyEditorOf(harness: Harness) {
  return harness.host.findComponent(ExamWorkspaceBodyEditor);
}

function creationsOf(harness: Harness): CreateGapEvent[] {
  return (bodyEditorOf(harness).emitted<CreateGapEvent>("createGap") ?? []) as CreateGapEvent[];
}

function updatesOf(harness: Harness): UpdateBodyEvent[] {
  return (bodyEditorOf(harness).emitted<UpdateBodyEvent>("updateBody") ?? []) as UpdateBodyEvent[];
}

function itemOf(harness: Harness): NativeExamItem {
  return bodyEditorOf(harness).props("item");
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

function dispatchEscape(target: HTMLElement): void {
  target.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
}

function requireInput(element: Element | null, what: string): HTMLInputElement {
  if (!(element instanceof HTMLInputElement)) {
    throw new Error(`${what} is not focused in an input`);
  }
  return element;
}

async function settle(): Promise<void> {
  await nextTick();
  await nextTick();
  await flushPromises();
}

/** A keyed Lucktext question with plain text and no gaps yet. */
function plainGapItem(): NativeExamItem {
  return buildGapItem({
    body: [
      {
        heading_level: null,
        segments: [{ kind: "text", marks: [], text: "Solen är en stjärna." }],
      },
    ],
    gaps: [],
  });
}

describe("ExamWorkspaceBodyEditor Tom lucka emit", () => {
  it("inserts an empty gap at the caret and opens its popover with the tool off", async () => {
    const host = mountHarness(plainGapItem());
    await settle();

    const editor = innerEditor(host);
    editor.commands.setTextSelection(posIn(editor, "stjärna", 1));
    bodyEditorOf(host).findComponent(ExamWorkspaceMarkToolbar).vm.$emit("insertEmptyGap");
    await settle();

    const creations = creationsOf(host);
    expect(creations).toHaveLength(1);
    expect(creations[0]?.[0]).toBe("item_001");
    expect(creations[0]?.[2]).toBe("gap_001");
    expect(creations[0]?.[3]).toBe("");
    expect(popoverExists()).toBe(true);
    const item = itemOf(host);
    expect(item.gaps.map((gap) => gap.gap_id)).toEqual(["gap_001"]);
    expect(item.gaps[0]?.accepted_values).toEqual([]);
    host.host.unmount();
  });

  it("inserts an empty gap when the Tom lucka toolbar button is clicked", async () => {
    const host = mountHarness(plainGapItem());
    await settle();

    const editor = innerEditor(host);
    editor.commands.setTextSelection(posIn(editor, "stjärna", 1));
    await host.host.get('[data-test="exam-workspace-toolbar-empty-gap"]').trigger("click");
    await settle();

    const creations = creationsOf(host);
    expect(creations).toHaveLength(1);
    expect(creations[0]?.[2]).toBe("gap_001");
    expect(creations[0]?.[3]).toBe("");
    expect(popoverExists()).toBe(true);
    host.host.unmount();
  });

  it("opens the new gap's popover with the gap tool on", async () => {
    const host = mountHarness(plainGapItem());
    await settle();
    await host.host.get('[data-test="exam-workspace-toolbar-gap-tool"]').trigger("click");
    await settle();

    const editor = innerEditor(host);
    editor.commands.setTextSelection(posIn(editor, "stjärna", 1));
    bodyEditorOf(host).findComponent(ExamWorkspaceMarkToolbar).vm.$emit("insertEmptyGap");
    await settle();

    expect(creationsOf(host)).toHaveLength(1);
    expect(creationsOf(host)[0]?.[3]).toBe("");
    expect(popoverExists()).toBe(true);
    host.host.unmount();
  });

  it("inserts at a selection's end and deletes no text", async () => {
    const host = mountHarness(plainGapItem());
    await settle();

    const editor = innerEditor(host);
    editor.commands.setTextSelection({
      from: posIn(editor, "Solen är en stjärna.", 0),
      to: posIn(editor, "Solen är en stjärna.", 5),
    });
    bodyEditorOf(host).findComponent(ExamWorkspaceMarkToolbar).vm.$emit("insertEmptyGap");
    await settle();

    expect(creationsOf(host)).toHaveLength(1);
    expect(editor.getText()).toBe("Solen är en stjärna.");
    host.host.unmount();
  });

  it("refuses the command for free text and at the gap cap", async () => {
    const freeText = mountHarness(
      buildGapItem({ kind: "free_text", body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "Solen lyser." }] }], gaps: [] }),
    );
    await settle();
    bodyEditorOf(freeText).findComponent(ExamWorkspaceMarkToolbar).vm.$emit("insertEmptyGap");
    await settle();
    expect(creationsOf(freeText)).toHaveLength(0);
    expect(popoverExists()).toBe(false);
    freeText.host.unmount();

    const capped = mountHarness(
      buildGapItem({
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
      }),
    );
    await settle();
    bodyEditorOf(capped).findComponent(ExamWorkspaceMarkToolbar).vm.$emit("insertEmptyGap");
    await settle();
    expect(creationsOf(capped)).toHaveLength(0);
    expect(popoverExists()).toBe(false);
    capped.host.unmount();
  });

  it("emits nothing while disabled", async () => {
    const host = mountHarness(plainGapItem());
    host.setDisabled(true);
    await settle();
    bodyEditorOf(host).findComponent(ExamWorkspaceMarkToolbar).vm.$emit("insertEmptyGap");
    await settle();
    expect(creationsOf(host)).toHaveLength(0);
    expect(popoverExists()).toBe(false);
    host.host.unmount();
  });
});

describe("ExamWorkspaceBodyEditor empty gap lifetime", () => {
  it("keeps an empty gap when its popover closes on Escape", async () => {
    const host = mountHarness(buildGapItem());
    await settle();

    clickGapChip(host, "gap_002");
    await settle();
    expect(popoverExists()).toBe(true);

    dispatchEscape(requireInput(document.activeElement, "the popover answer"));
    await settle();

    expect(popoverExists()).toBe(false);
    expect(updatesOf(host)).toHaveLength(0);
    expect(itemOf(host).gaps.map((gap) => gap.gap_id)).toEqual(["gap_001", "gap_002"]);
    expect(placedGapIds(itemOf(host).body)).toEqual(["gap_001", "gap_002"]);
    host.host.unmount();
  });

  it("keeps an empty gap when its popover closes on a click outside", async () => {
    const host = mountHarness(buildGapItem());
    await settle();

    clickGapChip(host, "gap_002");
    await settle();
    requireInput(document.activeElement, "the popover answer").dispatchEvent(
      new FocusEvent("focusout", { bubbles: true, relatedTarget: null }),
    );
    await settle();

    expect(popoverExists()).toBe(false);
    expect(updatesOf(host)).toHaveLength(0);
    expect(itemOf(host).gaps.map((gap) => gap.gap_id)).toEqual(["gap_001", "gap_002"]);
    host.host.unmount();
  });

  it("emits no body change of its own when the question is switched", async () => {
    const host = mountHarness(buildGapItem());
    await settle();

    clickGapChip(host, "gap_002");
    await settle();
    expect(popoverExists()).toBe(true);

    // The selection layer owns empty-gap cleanup; this editor only closes the popover.
    host.setItem({ ...buildGapItem(), item_id: "item_002" });
    await settle();

    expect(popoverExists()).toBe(false);
    expect(updatesOf(host)).toHaveLength(0);
    host.host.unmount();
  });

  it("shows no toast for the Tom lucka insert and the popover close", async () => {
    const host = mountHarness(plainGapItem());
    await settle();

    const editor = innerEditor(host);
    editor.commands.setTextSelection(posIn(editor, "stjärna", 1));
    bodyEditorOf(host).findComponent(ExamWorkspaceMarkToolbar).vm.$emit("insertEmptyGap");
    await settle();
    expect(popoverExists()).toBe(true);

    dispatchEscape(requireInput(document.activeElement, "the popover answer"));
    await settle();

    expect(toast.failure).not.toHaveBeenCalled();
    expect(toast.warning).not.toHaveBeenCalled();
    host.host.unmount();
  });
});
