/**
 * Exam workspace question-text editor: closing a gap popover without an answer removes the gap.
 *
 * Expected behavior (TASK-SKRIPT-40-04-13 H6):
 *   Closing the popover of a gap with no answer (Escape, a click outside,
 *   selecting another question) removes the gap from the body and from the
 *   item's gaps as one structural undo step; Ångra brings the gap back. A
 *   Lucktext gap with no accepted answer and a dropdown gap with no correct
 *   option are unanswered. A gap with an answer, and a gap whose answer was
 *   typed before the close, stays. A suspended editor forwards no gap change.
 *
 * jsdom has no layout, so a gap click reaches the view through its own click
 * handler, Escape and focusout are real DOM events, and the popover is
 * teleported to `document.body`, so specs query the document for it.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { Editor } from "@tiptap/core";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent, h, nextTick, ref } from "vue";

import type {
  NativeExamBodyParagraph,
  NativeExamChoice,
  NativeExamItem,
} from "../../../api/examWorkspace";
import ExamWorkspaceBodyEditor from "./ExamWorkspaceBodyEditor.vue";
import {
  buildGapItem,
  popoverExists,
  popoverInput,
} from "./ExamWorkspaceBodyEditor.specSupport";
import { withBody } from "./examWorkspaceItemEdits";
import { withGapOptions, withGapValues } from "./examWorkspaceGapEdits";
import { buildGap } from "./examWorkspaceKeyedItems.specSupport";
import { placedGapIds } from "./examWorkspaceRichTextDocument";
import { plainBody } from "./examWorkspaceRichText";
import {
  exam,
  openEditing,
  stopScopes,
} from "./useExamWorkspaceEditing.history.specSupport";

const api = vi.hoisted(() => ({
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  moveExamWorkspaceHistoryPosition: vi.fn(),
  saveExamWorkspaceDocument: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
}));
const toast = vi.hoisted(() => ({ failure: vi.fn(), warning: vi.fn() }));

vi.mock("../../../api/examWorkspace", async (original) => ({
  ...(await original<typeof import("../../../api/examWorkspace")>()),
  ...api,
}));
vi.mock("../../../composables/useToast", () => ({ useToast: () => toast }));

beforeEach(() => {
  for (const fn of [...Object.values(api), ...Object.values(toast)]) fn.mockReset();
});

type UpdateBodyEvent = [string, NativeExamBodyParagraph[], boolean];

/** The one host component of this file: the body editor on a teacher-owned item and disabled flag. */
type BodyEditorHost = {
  item: () => NativeExamItem;
  disabled: () => boolean;
  onUpdateBody: (itemId: string, body: NativeExamBodyParagraph[], structural: boolean) => void;
  onUpdateGapValues: (itemId: string, gapId: string, acceptedValues: string[]) => void;
  onUpdateGapOptions: (
    itemId: string,
    gapId: string,
    options: NativeExamChoice[],
    correctOptionId: string | null,
    structural: boolean,
  ) => void;
};

const Host = defineComponent({
  props: {
    state: { type: Object as () => BodyEditorHost, required: true },
  },
  setup(props) {
    return () =>
      h(ExamWorkspaceBodyEditor, {
        item: props.state.item(),
        disabled: props.state.disabled(),
        onUpdateBody: props.state.onUpdateBody,
        onUpdateGapValues: props.state.onUpdateGapValues,
        onUpdateGapOptions: props.state.onUpdateGapOptions,
      });
  },
});

/** Mount the body editor inside a small owner that applies each edit like the real store. */
function mountHarness(item: NativeExamItem) {
  const current = ref(item);
  const locked = ref(false);
  const host = mount(Host, {
    attachTo: document.body,
    props: {
      state: {
        item: () => current.value,
        disabled: () => locked.value,
        onUpdateBody: (
          itemId: string,
          body: NativeExamBodyParagraph[],
          structural: boolean,
        ) => {
          current.value = withBody(current.value, body);
          void itemId;
          void structural;
        },
        onUpdateGapValues: (itemId: string, gapId: string, acceptedValues: string[]) => {
          current.value = withGapValues(current.value, gapId, acceptedValues);
          void itemId;
        },
        onUpdateGapOptions: (
          itemId: string,
          gapId: string,
          options: NativeExamChoice[],
          correctOptionId: string | null,
          structural: boolean,
        ) => {
          current.value = withGapOptions(current.value, gapId, options, correctOptionId);
          void itemId;
          void structural;
        },
      } satisfies BodyEditorHost,
    },
  });
  mounted.push(host);
  return {
    host,
    current: (): NativeExamItem => current.value,
    setDisabled: (value: boolean): void => {
      locked.value = value;
    },
    setItem: (next: NativeExamItem): void => {
      current.value = next;
    },
  };
}

type Harness = ReturnType<typeof mountHarness>;

const mounted: Array<{ unmount: () => void }> = [];

afterEach(() => {
  while (mounted.length > 0) {
    mounted.pop()?.unmount();
  }
  stopScopes();
  document.body.innerHTML = "";
});

function bodyEditorOf(harness: Harness) {
  return harness.host.findComponent(ExamWorkspaceBodyEditor);
}

function bodyUpdates(harness: Harness): UpdateBodyEvent[] {
  return bodyEditorOf(harness).emitted<UpdateBodyEvent>("updateBody") ?? [];
}

function innerEditorOf(host: Harness["host"]): Editor {
  const surface = host.get('[data-test="exam-workspace-body-editor-surface"]').element;
  if (!(surface instanceof HTMLElement)) {
    throw new Error("the question text editor surface is not an element");
  }
  if (!("editor" in surface)) {
    throw new Error("the question text editor did not mount");
  }
  const candidate = surface.editor;
  if (!(candidate instanceof Editor)) {
    throw new Error("the question text editor did not mount");
  }
  return candidate;
}

function innerEditor(harness: Harness): Editor {
  return innerEditorOf(harness.host);
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

/** A dropdown question with one keyed and one unanswered gap. */
function dropdownItem(): NativeExamItem {
  const options: NativeExamChoice[] = [
    { body: plainBody("zebra"), choice_id: "choice_001" },
    { body: plainBody("apa"), choice_id: "choice_002" },
  ];
  return buildGapItem({
    kind: "inline_choice",
    body: [
      {
        heading_level: null,
        segments: [
          { kind: "text", marks: [], text: "Välj " },
          { gap_id: "gap_001", kind: "gap" },
          { kind: "text", marks: [], text: " eller " },
          { gap_id: "gap_002", kind: "gap" },
          { kind: "text", marks: [], text: "." },
        ],
      },
    ],
    gaps: [
      buildGap("gap_001", [], { correct_option_id: "choice_001", options }),
      buildGap("gap_002", [], { correct_option_id: null, options }),
    ],
  });
}

describe("ExamWorkspaceBodyEditor gap popover close without an answer", () => {
  it("removes an empty text gap on Escape as one structural edit", async () => {
    const harness = mountHarness(buildGapItem());
    await settle();

    clickGapChip(harness, "gap_002");
    await settle();
    expect(popoverExists()).toBe(true);

    dispatchEscape(requireInput(document.activeElement, "the popover answer"));
    await settle();

    expect(popoverExists()).toBe(false);
    const updates = bodyUpdates(harness);
    expect(updates).toHaveLength(1);
    expect(updates[0]?.[0]).toBe("item_001");
    expect(updates[0]?.[2]).toBe(true);
    expect(placedGapIds(updates[0]?.[1] ?? [])).toEqual(["gap_001"]);
    // The owner drops the record through `withBody`.
    expect(harness.current().gaps.map((gap) => gap.gap_id)).toEqual(["gap_001"]);
  });

  it("keeps a gap with an answer on Escape", async () => {
    const harness = mountHarness(buildGapItem());
    await settle();

    clickGapChip(harness, "gap_001");
    await settle();
    expect(popoverExists()).toBe(true);

    dispatchEscape(requireInput(document.activeElement, "the popover answer"));
    await settle();

    expect(popoverExists()).toBe(false);
    expect(bodyUpdates(harness)).toHaveLength(0);
    expect(harness.current().gaps.map((gap) => gap.gap_id)).toEqual(["gap_001", "gap_002"]);
  });

  it("removes an empty gap on a click outside and keeps an answered one", async () => {
    const harness = mountHarness(buildGapItem());
    await settle();

    clickGapChip(harness, "gap_002");
    await settle();
    requireInput(document.activeElement, "the popover answer").dispatchEvent(
      new FocusEvent("focusout", { bubbles: true, relatedTarget: null }),
    );
    await settle();

    expect(popoverExists()).toBe(false);
    expect(bodyUpdates(harness)).toHaveLength(1);
    expect(harness.current().gaps.map((gap) => gap.gap_id)).toEqual(["gap_001"]);

    clickGapChip(harness, "gap_001");
    await settle();
    requireInput(document.activeElement, "the popover answer").dispatchEvent(
      new FocusEvent("focusout", { bubbles: true, relatedTarget: null }),
    );
    await settle();

    expect(popoverExists()).toBe(false);
    expect(bodyUpdates(harness)).toHaveLength(1);
    expect(harness.current().gaps.map((gap) => gap.gap_id)).toEqual(["gap_001"]);
  });

  it("removes the closed question's empty gap when selecting another question", async () => {
    const harness = mountHarness(buildGapItem());
    await settle();

    clickGapChip(harness, "gap_002");
    await settle();
    expect(popoverExists()).toBe(true);

    harness.setItem({ ...buildGapItem(), item_id: "item_002" });
    await settle();

    expect(popoverExists()).toBe(false);
    const updates = bodyUpdates(harness);
    expect(updates).toHaveLength(1);
    expect(updates[0]?.[0]).toBe("item_001");
    expect(updates[0]?.[2]).toBe(true);
    expect(placedGapIds(updates[0]?.[1] ?? [])).toEqual(["gap_001"]);
  });

  it("keeps a gap whose answer was typed before Escape closes", async () => {
    const harness = mountHarness(buildGapItem());
    await settle();

    clickGapChip(harness, "gap_002");
    await settle();
    const input = popoverInput("gap_002");
    await input.setValue("noll");
    expect(harness.current().gaps.find((gap) => gap.gap_id === "gap_002")?.accepted_values).toEqual(
      ["noll"],
    );

    dispatchEscape(input.element);
    await settle();

    expect(popoverExists()).toBe(false);
    expect(bodyUpdates(harness)).toHaveLength(0);
    expect(harness.current().gaps.map((gap) => gap.gap_id)).toEqual(["gap_001", "gap_002"]);
  });

  it("removes a gap cleared by typing once Escape commits the empty rows", async () => {
    const harness = mountHarness(buildGapItem());
    await settle();

    clickGapChip(harness, "gap_001");
    await settle();
    const input = popoverInput("gap_001");
    await input.setValue("");
    // Typing an empty list commits nothing yet.
    expect(bodyUpdates(harness)).toHaveLength(0);

    dispatchEscape(input.element);
    await settle();

    expect(popoverExists()).toBe(false);
    const updates = bodyUpdates(harness);
    expect(updates).toHaveLength(1);
    expect(updates[0]?.[0]).toBe("item_001");
    expect(updates[0]?.[2]).toBe(true);
    expect(placedGapIds(updates[0]?.[1] ?? [])).toEqual(["gap_002"]);
    expect(harness.current().gaps.map((gap) => gap.gap_id)).toEqual(["gap_002"]);
  });

  it("removes a dropdown gap with no correct option and keeps a keyed one", async () => {
    const harness = mountHarness(dropdownItem());
    await settle();

    clickGapChip(harness, "gap_002");
    await settle();
    expect(popoverExists()).toBe(true);
    dispatchEscape(requireInput(document.activeElement, "the popover option"));
    await settle();

    expect(popoverExists()).toBe(false);
    expect(bodyUpdates(harness)).toHaveLength(1);
    expect(harness.current().gaps.map((gap) => gap.gap_id)).toEqual(["gap_001"]);

    clickGapChip(harness, "gap_001");
    await settle();
    dispatchEscape(requireInput(document.activeElement, "the popover option"));
    await settle();

    expect(popoverExists()).toBe(false);
    expect(bodyUpdates(harness)).toHaveLength(1);
    expect(harness.current().gaps.map((gap) => gap.gap_id)).toEqual(["gap_001"]);
  });

  it("forwards no gap change when a suspended editor closes the popover", async () => {
    const harness = mountHarness(buildGapItem());
    await settle();

    clickGapChip(harness, "gap_002");
    await settle();
    expect(popoverExists()).toBe(true);

    harness.setDisabled(true);
    await settle();

    expect(popoverExists()).toBe(false);
    expect(bodyUpdates(harness)).toHaveLength(0);
    expect(harness.current().gaps.map((gap) => gap.gap_id)).toEqual(["gap_001", "gap_002"]);
  });

  it("stores the removal as one structural step that Ångra brings back", async () => {
    const baseline = exam("Prov", 2);
    baseline.items[0] = buildGapItem();
    const { editing, server } = await openEditing(api, baseline);
    // The position move stands on a retained step, as the history specs fake it.
    api.moveExamWorkspaceHistoryPosition.mockImplementation(
      async (_lineage: string, request: { expectedCursor: string; stepId: string }) => {
        const position = request.stepId;
        server.state.position = position;
        server.state.cursor = `move-${position}`;
        return {
          document: server.documents.get(position)!,
          export_blockers: [],
          history: {
            baseline_step_id: "step-0",
            cursor: server.state.cursor,
            position_step_id: server.state.position,
            step_ids: [...server.state.steps],
          },
        };
      },
    );
    const host = mount(Host, {
      attachTo: document.body,
      props: {
        state: {
          item: () => editing.workspaceDocument.value!.items[0]!,
          disabled: () => editing.isBusy.value,
          onUpdateBody: editing.updateItemBody,
          onUpdateGapValues: editing.updateItemGapValues,
          onUpdateGapOptions: editing.updateItemGapOptions,
        } satisfies BodyEditorHost,
      },
    });
    mounted.push(host);
    await settle();
    const editor = innerEditorOf(host);
    const openChip = (gapId: string): void => {
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
    };
    openChip("gap_002");
    await settle();
    expect(popoverExists()).toBe(true);

    dispatchEscape(popoverInput("gap_002").element);
    await settle();
    await flushPromises();

    expect(popoverExists()).toBe(false);
    const removed = editing.workspaceDocument.value?.items[0];
    expect(removed?.gaps.map((gap) => gap.gap_id)).toEqual(["gap_001"]);
    expect(placedGapIds(removed?.body ?? [])).toEqual(["gap_001"]);
    expect(server.state.steps).toHaveLength(1);

    await editing.history.undo();
    await settle();
    await flushPromises();

    const restored = editing.workspaceDocument.value?.items[0];
    expect(restored?.gaps.map((gap) => gap.gap_id)).toEqual(["gap_001", "gap_002"]);
    expect(placedGapIds(restored?.body ?? [])).toEqual(["gap_001", "gap_002"]);
  });
});
