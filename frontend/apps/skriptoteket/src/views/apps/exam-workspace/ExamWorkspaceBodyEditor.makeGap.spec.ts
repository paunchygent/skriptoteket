/**
 * Exam workspace question-text editor: gap creation through the component tree.
 *
 * Expected behavior (TASK-SKRIPT-40-04-08 J6, ledger L4-L6):
 *   In a Lucktext or dropdown-Lucktext question the toolbar "Lucka" button
 *   and the floating "Gör till lucka" button create a gap end to end: the
 *   editor's one `createGap` reaches `editing.createItemGap` as one undoable
 *   structural edit, and the new gap's popover opens at once. At `gap_999`
 *   the Lucka button is disabled with "Kan inte lägga till fler luckor".
 *
 * jsdom has no layout, so selections are set through TipTap commands, the
 * click that shows the floating button reaches the view through its own
 * click handler, and the popover is teleported to `document.body`, so specs
 * query the document for both buttons.
 */

import { flushPromises, mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import type { Editor } from "@tiptap/core";
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
import { nextGapId, withBody, withNewGap } from "./examWorkspaceItemEdits";
import { plainBody } from "./examWorkspaceRichText";
import { useExamWorkspaceEditing } from "./useExamWorkspaceEditing";
import {
  exam,
  inScope,
  stopScopes,
} from "./useExamWorkspaceEditing.history.specSupport";
import type { ExamWorkspaceItemEntry } from "./examWorkspaceListEntries";

const TOOLBAR_GAP = '[data-test="exam-workspace-toolbar-make-gap"]';
const FLOATING_GAP = '[data-test="exam-workspace-make-gap"]';
const GAP_AT_CAP = "Kan inte lägga till fler luckor";

const toast = vi.hoisted(() => ({ failure: vi.fn(), warning: vi.fn() }));

vi.mock("../../../composables/useToast", () => ({ useToast: () => toast }));

type Creation = [string, NativeExamBodyParagraph[], string, string];

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

function creationsOf(host: VueWrapper): Creation[] {
  return ((bodyEditorOf(host).emitted("createGap") ?? []) as Creation[]).map(
    ([itemId, body, gapId, seed]) => [itemId, body, gapId, seed],
  );
}

function updatesOf(host: VueWrapper): unknown[][] {
  return bodyEditorOf(host).emitted("updateBody") ?? [];
}

function itemOf(host: VueWrapper): NativeExamItem {
  return bodyEditorOf(host).props("item");
}

function innerEditor(host: VueWrapper): Editor {
  const surface = host.get('[data-test="exam-workspace-body-editor-surface"]')
    .element as HTMLElement & { editor?: Editor };
  if (!surface.editor) {
    throw new Error("the question text editor did not mount");
  }
  return surface.editor;
}

function surfaceOf(host: VueWrapper): HTMLElement {
  return host.get('[data-test="exam-workspace-body-editor-surface"]')
    .element as HTMLElement;
}

/** A primary click at `pos` that leaves the caret behind, as a mousedown would. */
function clickAt(editor: Editor, pos: number): void {
  editor.view.someProp("handleClick", (handler) =>
    handler(editor.view, pos, new MouseEvent("click", { bubbles: true, cancelable: true })),
  );
}

async function settle(): Promise<void> {
  await nextTick();
  await nextTick();
  await flushPromises();
}

/** Place the caret inside `word`, show the floating button and click it. */
async function convertWord(host: VueWrapper, word: string): Promise<void> {
  const editor = innerEditor(host);
  editor.commands.setTextSelection(posIn(editor, word, 1));
  clickAt(editor, posIn(editor, word, 1));
  await settle();
  const button = document.querySelector<HTMLButtonElement>(FLOATING_GAP);
  if (!button) {
    throw new Error(`no floating gap button for "${word}"`);
  }
  button.click();
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
  it("creates three gaps by clicking words, opening each new gap's popover", async () => {
    const host = mountHarness(plainGapItem());
    await settle();

    for (const [index, word] of ["Solen", "stjärna", "satellit"].entries()) {
      await convertWord(host, word);

      const creations = creationsOf(host);
      expect(creations).toHaveLength(index + 1);
      expect(updatesOf(host)).toHaveLength(0);
      const [itemId, , gapId, seed] = creations[index]!;
      expect(itemId).toBe("item_001");
      expect(gapId).toBe(`gap_00${index + 1}`);
      expect(seed).toBe(word);
      expect(popoverExists()).toBe(true);
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

  it("creates an empty gap at the end from the toolbar when no rich target is active yet", async () => {
    const host = mountHarness(plainGapItem());
    await settle();

    // The caret sits inside a word but no surface has focus, so nothing is active yet.
    const editor = innerEditor(host);
    editor.commands.setTextSelection(posIn(editor, "stjärna", 1));

    await host.get(TOOLBAR_GAP).trigger("click");
    // The focus — and the registration as the active target — lands on the
    // next animation frame, so the gap command runs one frame after the click.
    await new Promise<void>((resolve) => {
      requestAnimationFrame(() => resolve());
    });
    await settle();

    const creations = creationsOf(host);
    expect(creations).toHaveLength(1);
    expect(updatesOf(host)).toHaveLength(0);
    const [itemId, body, gapId, seed] = creations[0]!;
    expect(itemId).toBe("item_001");
    expect(gapId).toBe("gap_001");
    expect(seed).toBe("");
    expect(body).toEqual([
      {
        heading_level: null,
        segments: [
          { kind: "text", marks: [], text: "Solen är en stjärna och månen en satellit." },
          { gap_id: "gap_001", kind: "gap" },
        ],
      },
    ]);
    expect(popoverExists()).toBe(true);
    host.unmount();
  });

  it("disables the Lucka button at gap_999 with its reason and emits nothing", async () => {
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

    const button = host.get(TOOLBAR_GAP);
    expect(button.attributes("disabled")).toBeDefined();
    expect(button.attributes("title")).toBe(GAP_AT_CAP);
    await button.trigger("click");
    await settle();
    expect(creationsOf(host)).toHaveLength(0);
    expect(updatesOf(host)).toHaveLength(0);

    const editor = innerEditor(host);
    editor.commands.setTextSelection(posIn(editor, "Svar", 1));
    clickAt(editor, posIn(editor, "Svar", 1));
    await settle();
    expect(document.querySelector(FLOATING_GAP)).toBeNull();
    host.unmount();
  });

  it("shows no Lucka button and no floating button for free text", async () => {
    const host = mountHarness(
      buildGapItem({ kind: "free_text", body: plainBody("Solen lyser."), gaps: [] }),
    );
    await settle();

    expect(host.find(TOOLBAR_GAP).exists()).toBe(false);

    const editor = innerEditor(host);
    editor.commands.setTextSelection(posIn(editor, "Solen", 1));
    clickAt(editor, posIn(editor, "Solen", 1));
    await settle();
    expect(document.querySelector(FLOATING_GAP)).toBeNull();
    expect(creationsOf(host)).toHaveLength(0);
    expect(updatesOf(host)).toHaveLength(0);
    host.unmount();
  });

  it("emits nothing while disabled", async () => {
    const host = mountHarness(plainGapItem(), true);
    await settle();

    expect(host.get(TOOLBAR_GAP).attributes("disabled")).toBeDefined();
    await host.get(TOOLBAR_GAP).trigger("click");
    await settle();

    const editor = innerEditor(host);
    editor.commands.setTextSelection(posIn(editor, "stjärna", 1));
    clickAt(editor, posIn(editor, "stjärna", 1));
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

  it("seeds one correct option with the word for a dropdown question", async () => {
    const host = mountHarness(
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

    await convertWord(host, "Paris");

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

    const editing = inScope(() => useExamWorkspaceEditing());
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
