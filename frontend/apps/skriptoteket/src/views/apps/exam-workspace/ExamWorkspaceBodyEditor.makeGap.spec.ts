/**
 * Exam workspace question-text editor: gap creation through the component tree.
 *
 * Expected behavior (TASK-SKRIPT-40-04-13 Behaviours 8 and 9):
 *   In a Lucktext or dropdown-Lucktext question the gap tool switch is the
 *   only gap control: with the tool on, a word click creates a gap end to
 *   end with no popover, and the editor's one `createGap` reaches
 *   `editing.createItemGap` as one undoable structural edit. No control
 *   inserts an empty gap, and with the tool off a word click only places
 *   the caret. At `gap_999` the switch is disabled with
 *   "Luckverktyg – inga fler luckor kan läggas till i frågan".
 *
 * jsdom has no layout, so selections are set through TipTap commands, word
 * clicks reach the view through its own click handler with a stubbed
 * pointer coordinate, and the popover is teleported to `document.body`, so
 * specs query the document for the toggle and the absent floating button.
 */

import { flushPromises, mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import { Editor } from "@tiptap/core";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent, h, nextTick, ref } from "vue";

import type {
  NativeExamBodyParagraph,
  NativeExamItem,
} from "../../../api/examWorkspace";
import ExamWorkspaceBodyEditor from "./ExamWorkspaceBodyEditor.vue";
import ExamWorkspaceEditorPane from "./ExamWorkspaceEditorPane.vue";
import ExamWorkspaceQuestionEditor from "./ExamWorkspaceQuestionEditor.vue";
import ExamWorkspaceRichTextEditor from "./ExamWorkspaceRichTextEditor.vue";
import {
  buildGapItem,
  popoverExists,
  posIn,
} from "./ExamWorkspaceBodyEditor.specSupport";
import { buildGap } from "./examWorkspaceKeyedItems.specSupport";
import {
  gapPointerMiddle,
  stubLinearGapPointerGeometry,
} from "./examWorkspaceGapToolPointer.specSupport";
import { examWorkspaceProvidersPlugin } from "./examWorkspaceProviders.specSupport";
import { withBody } from "./examWorkspaceItemEdits";
import { nextGapId, withNewGap } from "./examWorkspaceGapEdits";
import { plainBody } from "./examWorkspaceRichText";
import { GAP_TOOL_AT_CAP_REASON } from "./useExamWorkspaceMakeGap";
import { serverExamWorkspaceStore } from "./examWorkspaceStore";
import { useExamWorkspaceEditing } from "./useExamWorkspaceEditing";
import { nullRouteProjection } from "./examWorkspaceRouteProjection.specSupport";
import {
  exam,
  inScope,
  stopScopes,
} from "./useExamWorkspaceEditing.history.specSupport";
import type { ExamWorkspaceItemEntry } from "./examWorkspaceListEntries";

const TOOLBAR_GAP_TOOL = '[data-test="exam-workspace-toolbar-gap-tool"]';
const FLOATING_GAP = '[data-test="exam-workspace-make-gap"]';
const TOOL_AT_CAP = GAP_TOOL_AT_CAP_REASON;

const toast = vi.hoisted(() => ({ failure: vi.fn(), warning: vi.fn() }));

vi.mock("../../../composables/useToast", () => ({ useToast: () => toast }));

/** Mount the body editor inside a small owner that applies each edit like the real store. */
function mountHarness(item: NativeExamItem, disabled = false): VueWrapper {
  const Host = defineComponent({
    setup() {
      const current = ref(item);
      return () =>
        h(ExamWorkspaceBodyEditor, {
          item: current.value,
          disabled,
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
  return mount(Host, { attachTo: document.body });
}

function bodyEditorOf(host: VueWrapper) {
  return host.findComponent(ExamWorkspaceBodyEditor);
}

function creationsOf(host: VueWrapper): unknown[][] {
  return bodyEditorOf(host).emitted("createGap") ?? [];
}

function updatesOf(host: VueWrapper): unknown[][] {
  return bodyEditorOf(host).emitted("updateBody") ?? [];
}

function itemOf(host: VueWrapper): NativeExamItem {
  return bodyEditorOf(host).props("item");
}

function innerEditor(host: VueWrapper): Editor {
  const surface = host.get('[data-test="exam-workspace-body-editor-surface"]').element;
  if (!(surface instanceof HTMLElement) || !("editor" in surface)) {
    throw new Error("the question text editor did not mount");
  }
  const candidate = surface.editor;
  if (!(candidate instanceof Editor)) {
    throw new Error("the question text editor did not mount");
  }
  return candidate;
}

function surfaceOf(host: VueWrapper): HTMLElement {
  const surface = host.get('[data-test="exam-workspace-body-editor-surface"]').element;
  if (!(surface instanceof HTMLElement)) {
    throw new Error("the question text editor surface is not an element");
  }
  return surface;
}

/** A primary click at `pos` with the pointer inside the clicked word. */
function clickAt(editor: Editor, pos: number, clientX: number): void {
  editor.view.someProp("handleClick", (handler) =>
    handler(editor.view, pos, new MouseEvent("click", { bubbles: true, cancelable: true, clientX })),
  );
}

/** Click `word` with the tool's pointer geometry, as a real pointer press would. */
function clickWord(host: VueWrapper, editor: Editor, word: string): void {
  stubLinearGapPointerGeometry(editor);
  const pos = posIn(editor, word, 1);
  editor.commands.setTextSelection(pos);
  clickAt(editor, pos, gapPointerMiddle(pos));
}

async function settle(): Promise<void> {
  await nextTick();
  await nextTick();
  await flushPromises();
}

/** Turn the tool on through its toggle, as the teacher does. */
async function switchToolOn(host: VueWrapper): Promise<void> {
  await host.get(TOOLBAR_GAP_TOOL).trigger("click");
  await settle();
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

afterEach(() => {
  stopScopes();
  document.body.innerHTML = "";
});

beforeEach(() => {
  for (const fn of Object.values(toast)) fn.mockReset();
});

describe("ExamWorkspaceBodyEditor gap creation", () => {
  it("creates three gaps through the tool with no popover and no floating button", async () => {
    const host = mountHarness(plainGapItem());
    await settle();
    await switchToolOn(host);

    for (const [index, word] of ["Solen", "stjärna", "satellit"].entries()) {
      clickWord(host, innerEditor(host), word);
      await settle();

      const creations = creationsOf(host);
      expect(creations).toHaveLength(index + 1);
      expect(updatesOf(host)).toHaveLength(0);
      const [itemId, , gapId, seed] = creations[index]!;
      expect(itemId).toBe("item_001");
      expect(gapId).toBe(`gap_00${index + 1}`);
      expect(seed).toBe(word);
      expect(popoverExists()).toBe(false);
      expect(document.querySelector(FLOATING_GAP)).toBeNull();
    }

    const item = itemOf(host);
    expect(item.gaps.map((gap) => gap.gap_id)).toEqual(["gap_001", "gap_002", "gap_003"]);
    expect(item.gaps.map((gap) => gap.accepted_values)).toEqual([
      ["Solen"],
      ["stjärna"],
      ["satellit"],
    ]);
    host.unmount();
  });

  it("creates no gap and shows no button on a word click with the tool off", async () => {
    const host = mountHarness(plainGapItem());
    await settle();

    const editor = innerEditor(host);
    editor.commands.setTextSelection(posIn(editor, "stjärna", 1));
    clickAt(editor, posIn(editor, "stjärna", 1), 0);
    await settle();

    expect(creationsOf(host)).toHaveLength(0);
    expect(updatesOf(host)).toHaveLength(0);
    expect(document.querySelector(FLOATING_GAP)).toBeNull();
    expect(popoverExists()).toBe(false);
    host.unmount();
  });

  it("disables the gap tool toggle at gap_999 with its reason and emits nothing", async () => {
    const host = mountHarness(
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

    const button = host.get(TOOLBAR_GAP_TOOL);
    expect(button.attributes("disabled")).toBeDefined();
    expect(button.attributes("title")).toBe(TOOL_AT_CAP);
    await button.trigger("click");
    await settle();
    expect(creationsOf(host)).toHaveLength(0);
    expect(updatesOf(host)).toHaveLength(0);

    clickWord(host, innerEditor(host), "Svar");
    await settle();
    expect(document.querySelector(FLOATING_GAP)).toBeNull();
    host.unmount();
  });

  it("shows no gap toggle and no floating button for free text", async () => {
    const host = mountHarness(
      buildGapItem({ kind: "free_text", body: plainBody("Solen lyser."), gaps: [] }),
    );
    await settle();

    expect(host.find(TOOLBAR_GAP_TOOL).exists()).toBe(false);

    const editor = innerEditor(host);
    editor.commands.setTextSelection(posIn(editor, "Solen", 1));
    clickAt(editor, posIn(editor, "Solen", 1), 0);
    await settle();
    expect(document.querySelector(FLOATING_GAP)).toBeNull();
    expect(creationsOf(host)).toHaveLength(0);
    expect(updatesOf(host)).toHaveLength(0);
    host.unmount();
  });

  it("emits nothing while disabled", async () => {
    const host = mountHarness(plainGapItem(), true);
    await settle();

    expect(host.get(TOOLBAR_GAP_TOOL).attributes("disabled")).toBeDefined();
    await host.get(TOOLBAR_GAP_TOOL).trigger("click");
    await settle();

    const editor = innerEditor(host);
    editor.commands.setTextSelection(posIn(editor, "stjärna", 1));
    clickAt(editor, posIn(editor, "stjärna", 1), 0);
    await settle();
    expect(document.querySelector(FLOATING_GAP)).toBeNull();

    const richText = host.findComponent(ExamWorkspaceRichTextEditor);
    richText.vm.$emit("createGap", plainGapItem().body, "gap_001", "Solen");
    await settle();

    expect(creationsOf(host)).toHaveLength(0);
    expect(updatesOf(host)).toHaveLength(0);
    expect(popoverExists()).toBe(false);
    host.unmount();
  });

  it("seeds one correct option with the word for a dropdown question", async () => {    const host = mountHarness(
      buildGapItem({
        kind: "inline_choice",
        body: [
          {
            heading_level: null,
            segments: [{ kind: "text", marks: [], text: "Huvudstaden är Paris." }],
          },
        ],
        gaps: [],
      }),
    );
    await settle();
    await switchToolOn(host);

    clickWord(host, innerEditor(host), "Paris");
    await settle();

    expect(creationsOf(host)).toHaveLength(1);
    const record = itemOf(host).gaps[0]!;
    expect(record.gap_id).toBe("gap_001");
    expect(record.correct_option_id).toBe("choice_001");
    expect(record.options).toEqual([
      { body: plainBody("Paris"), choice_id: "choice_001" },
    ]);
    expect(nextGapId(itemOf(host))).toBe("gap_002");
    host.unmount();
  });

  it("re-emits createGap through the question editor to the pane's createItemGap", async () => {
    const item = plainGapItem();
    const question = mount(ExamWorkspaceQuestionEditor, {
      attachTo: document.body,
      global: { plugins: [examWorkspaceProvidersPlugin()] },
      props: {
        item,
        label: "1",
        origin: "digiexam_import",
        parent: null,
        child: null,
        converting: false,
        disabled: false,
        notice: null,
        importOpen: false,
      },
    });
    await settle();

    const body = question.findComponent(ExamWorkspaceBodyEditor);
    body.vm.$emit("createGap", "item_001", item.body, "gap_001", "Solen");
    expect(question.emitted("createGap")).toEqual([
      ["item_001", item.body, "gap_001", "Solen"],
    ]);
    question.unmount();

    const editing = inScope(() => useExamWorkspaceEditing(serverExamWorkspaceStore, nullRouteProjection()));
    const created = vi.spyOn(editing, "createItemGap");
    const entry: ExamWorkspaceItemEntry = {
      kind: "item",
      id: "item_001",
      label: "1",
      parentId: null,
      text: "Solen",
      typeLabel: "Lucktext",
      itemKind: "gap_fill",
      points: 1,
      problem: null,
      aiKey: null,
      status: "ok",
    };
    const pane = mount(ExamWorkspaceEditorPane, {
      attachTo: document.body,
      global: { plugins: [examWorkspaceProvidersPlugin()] },
      props: {
        editing,
        workspaceDocument: exam(),
        examInstructionsSelected: false,
        selectedParent: null,
        selectedParentEntry: null,
        parentChildren: [],
        entries: [],
        selectedItem: item,
        itemEntry: entry,
        itemParent: null,
        itemChild: null,
        itemNotice: null,
        converting: false,
        disabled: false,
        importOpen: false,
        openDrawerShown: false,
      },
    });
    await settle();

    pane.findComponent(ExamWorkspaceQuestionEditor).vm.$emit("createGap", "item_001", item.body, "gap_001", "Solen");
    expect(created).toHaveBeenCalledWith("item_001", item.body, "gap_001", "Solen");
    expect(surfaceOf(pane)).toBeDefined();
    pane.unmount();
  });
});
