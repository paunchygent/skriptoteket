/**
 * Exam workspace question-text editor: Ångra suspends the gap tool instead of ending it.
 *
 * Expected behavior (TASK-SKRIPT-40-04-09 walk finding A3):
 *   Clicking the header Ångra runs under `replaceCopy`, which sets `disabled`
 *   for the length of the replacing read. A disabled editor suspends the gap
 *   tool instead of ending it: while disabled, tool clicks make no gap and an
 *   open popover closes; when the editor is enabled again, the tool is still
 *   on. The tool ends only by its switch, its shortcut, Escape after an open
 *   popover, or selecting another question. Gör om, Spara som, a structural
 *   command and a conversion lock all reach the editor through the same
 *   `disabled` prop, so none of them ends the tool either.
 *
 * jsdom has no layout, so selections are set through TipTap commands and word
 * clicks reach the view through its own click handler.
 */

import { flushPromises, mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import { Editor } from "@tiptap/core";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { computed, defineComponent, h, nextTick, ref, watch } from "vue";

import type {
  NativeExamBodyParagraph,
  NativeExamDocument,
  NativeExamItem,
} from "../../../api/examWorkspace";
import ExamWorkspaceBodyEditor from "./ExamWorkspaceBodyEditor.vue";
import ExamWorkspaceRichTextEditor from "./ExamWorkspaceRichTextEditor.vue";
import { buildGapItem, popoverExists, posIn } from "./ExamWorkspaceBodyEditor.specSupport";
import { provideExamWorkspaceHistoryKeys } from "./examWorkspaceHistoryKeys";
import {
  dispatchGapToolClick,
  gapPointerMiddle,
  stubLinearGapPointerGeometry,
} from "./examWorkspaceGapToolPointer.specSupport";
import { withBody } from "./examWorkspaceItemEdits";
import { withNewGap } from "./examWorkspaceGapEdits";
import { exam, openEditing, stopScopes } from "./useExamWorkspaceEditing.history.specSupport";

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

const TOOLBAR_GAP_TOOL = '[data-test="exam-workspace-toolbar-gap-tool"]';

type BodyEditorHost = {
  item: () => NativeExamItem;
  disabled: () => boolean;
  undo: () => void;
  redo: () => void;
  canUndo: () => boolean;
  canRedo: () => boolean;
  onCreateGap: (itemId: string, body: NativeExamBodyParagraph[], gapId: string, seed: string) => void;
  onUpdateBody: (itemId: string, body: NativeExamBodyParagraph[], structural: boolean) => void;
  onShowGapAsText: ((itemId: string, gapId: string) => void) | null;
  onDisabledChange: ((value: boolean) => void) | null;
};

/** The one host component of this file: the body editor on a teacher-owned item and disabled flag. */
const Host = defineComponent({
  props: {
    state: { type: Object as () => BodyEditorHost, required: true },
  },
  setup(props) {
    provideExamWorkspaceHistoryKeys({
      undo: () => props.state.undo(),
      redo: () => props.state.redo(),
      canUndo: computed(() => props.state.canUndo()),
      canRedo: computed(() => props.state.canRedo()),
    });
    const disabled = computed(() => props.state.disabled());
    watch(disabled, (value) => {
      props.state.onDisabledChange?.(value);
    });
    return () =>
      h(ExamWorkspaceBodyEditor, {
        item: props.state.item(),
        disabled: disabled.value,
        onCreateGap: props.state.onCreateGap,
        onUpdateBody: props.state.onUpdateBody,
        ...(props.state.onShowGapAsText === null ? {} : { onShowGapAsText: props.state.onShowGapAsText }),
      });
  },
});

/** Mount the body editor with a teacher-owned disabled flag, as the view owns it. */
function mountHarness(item: NativeExamItem) {
  const current = ref(item);
  const locked = ref(false);
  const host = mount(Host, {
    attachTo: document.body,
    props: {
      state: {
        item: () => current.value,
        disabled: () => locked.value,
        undo: () => undefined,
        redo: () => undefined,
        canUndo: () => false,
        canRedo: () => false,
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
        onShowGapAsText: null,
        onDisabledChange: null,
      } satisfies BodyEditorHost,
    },
  });
  mounted.push(host);
  return {
    host,
    setDisabled: (value: boolean): void => {
      locked.value = value;
    },
  };
}

type Harness = ReturnType<typeof mountHarness>;

const mounted: VueWrapper[] = [];

afterEach(() => {
  for (const wrapper of mounted.splice(0)) wrapper.unmount();
  stopScopes();
  document.body.innerHTML = "";
});

function toolToggle(harness: Harness) {
  return harness.host.find(TOOLBAR_GAP_TOOL);
}

function toolPressed(harness: Harness): string | undefined {
  return toolToggle(harness).attributes("aria-pressed");
}

function toolOn(harness: Harness): boolean {
  return harness.host.findComponent(ExamWorkspaceRichTextEditor).props("gapTool") === true;
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

/** Click the word, setting the caret first as a real pointer press would. */
function clickWord(harness: Harness, word: string): void {
  const editor = innerEditor(harness);
  stubLinearGapPointerGeometry(editor);
  const pos = posIn(editor, word, 1);
  editor.commands.setTextSelection(pos);
  dispatchGapToolClick(editor, pos, gapPointerMiddle(pos));
}

/** Select a gap chip as the keyboard does, so Enter opens its popover. */
function selectGap(harness: Harness, gapId: string): void {
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
  editor.commands.setNodeSelection(pos);
}

function pressEnter(target: HTMLElement): void {
  target.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true, cancelable: true }));
}

function creationsOf(harness: Harness): unknown[][] {
  return harness.host.findComponent(ExamWorkspaceBodyEditor).emitted("createGap") ?? [];
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

/** A gap-fill first item with plain text, for the editing-session integration case. */
function sessionBaseline(): NativeExamDocument {
  const document = exam("Prov", 2);
  return {
    ...document,
    items: [
      { ...plainGapItem(), item_id: "item_001", sequence: 1 },
      document.items[1]!,
    ],
  };
}

describe("ExamWorkspaceBodyEditor gap tool across undo", () => {
  it("stays on while disabled and after the editor is enabled again", async () => {
    const harness = mountHarness(plainGapItem());
    await settle();

    await toolToggle(harness).trigger("click");
    await settle();
    expect(toolPressed(harness)).toBe("true");

    harness.setDisabled(true);
    await settle();
    expect(toolPressed(harness)).toBe("true");
    expect(toolOn(harness)).toBe(true);

    harness.setDisabled(false);
    await settle();
    expect(toolPressed(harness)).toBe("true");
    expect(toolOn(harness)).toBe(true);
  });

  it("makes no gap from a word click while disabled, and makes one after re-enabling", async () => {
    const harness = mountHarness(plainGapItem());
    await settle();

    await toolToggle(harness).trigger("click");
    await settle();
    expect(toolPressed(harness)).toBe("true");

    harness.setDisabled(true);
    await settle();
    clickWord(harness, "stjärna");
    await settle();
    expect(creationsOf(harness)).toHaveLength(0);

    harness.setDisabled(false);
    await settle();
    expect(toolPressed(harness)).toBe("true");
    clickWord(harness, "stjärna");
    await settle();
    expect(creationsOf(harness)).toHaveLength(1);
    expect(popoverExists()).toBe(false);
  });

  it("closes an open popover when disabled but keeps the tool on", async () => {
    const harness = mountHarness(buildGapItem());
    await settle();

    await toolToggle(harness).trigger("click");
    await settle();
    selectGap(harness, "gap_001");
    pressEnter(surfaceOf(harness));
    await settle();
    expect(popoverExists()).toBe(true);

    harness.setDisabled(true);
    await settle();
    expect(popoverExists()).toBe(false);
    expect(toolPressed(harness)).toBe("true");

    harness.setDisabled(false);
    await settle();
    expect(toolPressed(harness)).toBe("true");
    expect(popoverExists()).toBe(false);
  });

  it("keeps the tool on through a real undo that disables the editor", async () => {
    const { editing } = await openEditing(api, sessionBaseline());
    const transitions: boolean[] = [];
    const host = mount(Host, {
      attachTo: document.body,
      props: {
        state: {
          item: () => editing.workspaceDocument.value!.items[0]!,
          disabled: () => editing.isBusy.value,
          undo: () => void editing.history.undo(),
          redo: () => void editing.history.redo(),
          canUndo: () => editing.history.canUndo.value,
          canRedo: () => editing.history.canRedo.value,
          onCreateGap: editing.createItemGap,
          onUpdateBody: editing.updateItemBody,
          onShowGapAsText: editing.showItemGapAsText,
          onDisabledChange: (value: boolean) => {
            transitions.push(value);
          },
        } satisfies BodyEditorHost,
      },
    });
    mounted.push(host);
    await settle();

    const toggle = host.find(TOOLBAR_GAP_TOOL);
    await toggle.trigger("click");
    await settle();
    expect(toggle.attributes("aria-pressed")).toBe("true");

    const bodyEditor = host.findComponent(ExamWorkspaceBodyEditor);
    const rich = host.findComponent(ExamWorkspaceRichTextEditor);
    expect(rich.props("gapTool")).toBe(true);
    const editor = ((): Editor => {
      const surface = host.get('[data-test="exam-workspace-body-editor-surface"]').element;
      if (!(surface instanceof HTMLElement) || !("editor" in surface)) {
        throw new Error("the question text editor did not mount");
      }
      const candidate = surface.editor;
      if (!(candidate instanceof Editor)) {
        throw new Error("the question text editor did not mount");
      }
      return candidate;
    })();
    stubLinearGapPointerGeometry(editor);
    const pos = posIn(editor, "Solen", 1);
    editor.commands.setTextSelection(pos);
    dispatchGapToolClick(editor, pos, gapPointerMiddle(pos));
    await settle();
    await flushPromises();
    expect(bodyEditor.emitted("createGap")).toHaveLength(1);
    expect(toggle.attributes("aria-pressed")).toBe("true");

    await editing.history.undo();
    await settle();
    await flushPromises();

    // The undo ran under the replacing lock, so the editor was disabled mid-flight.
    expect(transitions).toContain(true);
    expect(editing.isBusy.value).toBe(false);
    expect(toggle.attributes("aria-pressed")).toBe("true");
    expect(host.findComponent(ExamWorkspaceRichTextEditor).props("gapTool")).toBe(true);
    void bodyEditor;
  });
});
