/**
 * Exam workspace rich-text editor: the gap command and the floating gap button.
 *
 * Expected behavior (TASK-SKRIPT-40-04-08 J4):
 *   `target.makeGap(gapId)` turns the selection, or the word at the caret,
 *   into a new gap, or inserts an empty gap, as one change that emits a
 *   single `createGap(body, gapId, seed)` event and never `update`. A click
 *   inside a word shows a small floating "Gör till lucka" button above that
 *   word; one click on it converts the word. The button stays while later
 *   transactions leave the document and the caret inside the word, and hides
 *   on any document change, on a caret move out of the word, on scroll or
 *   resize, on Escape, and when the editor is disabled or has no next gap id.
 *
 * jsdom has no layout, so selections are set through TipTap commands and
 * clicks reach the view through `someProp("handleClick")`; coordinates are
 * stubbed where the placement is asserted. The button teleports to
 * document.body, so it is found through `document` rather than the wrapper.
 */

import { NodeSelection, TextSelection } from "@tiptap/pm/state";
import { mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import type { Editor } from "@tiptap/core";
import { afterEach, describe, expect, it, vi } from "vitest";
import { defineComponent, h, nextTick } from "vue";

import type { NativeExamBodyParagraph } from "../../../api/examWorkspace";
import ExamWorkspaceRichTextEditor from "./ExamWorkspaceRichTextEditor.vue";
import {
  gap,
  paragraph,
  posIn,
  releaseEditor,
  text,
} from "./ExamWorkspaceRichTextEditor.specSupport";
import { provideExamWorkspaceHistoryKeys } from "./examWorkspaceHistoryKeys";
import type { ExamWorkspaceHistoryKeys } from "./examWorkspaceHistoryKeys";
import { provideRichTextTargetRegistry } from "./examWorkspaceRichTextTarget";
import type { RichTextTargetRegistry } from "./examWorkspaceRichTextTarget";
import { ATOM_STATE_KEY } from "./examWorkspaceRichTextSchema";

type Body = NativeExamBodyParagraph[];
type Creation = [Body, string, string];

type Opened = {
  wrapper: VueWrapper;
  editor: Editor;
  surface: HTMLElement;
  root: HTMLElement;
  registry: RichTextTargetRegistry;
  updates: Array<[Body, boolean]>;
  creations: Creation[];
  setProps: (props: Partial<EditorProps>) => Promise<void>;
};

const openedWrappers: VueWrapper[] = [];

/** Unmount every editor `openEditor` opened; each spec calls it after each test. */
function releaseOpenedEditors(): void {
  while (openedWrappers.length > 0) {
    openedWrappers.pop()?.unmount();
  }
}

type EditorProps = {
  body: Body;
  gapsInteractive?: boolean;
  disabled?: boolean;
  nextGapId?: string | null;
};

async function openEditor(initial: EditorProps): Promise<Opened> {
  const updates: Array<[Body, boolean]> = [];
  const creations: Creation[] = [];
  let registry!: RichTextTargetRegistry;
  const keys = { undo: vi.fn(), redo: vi.fn() };
  const Host = defineComponent({
    props: { editorProps: { type: Object, required: true } },
    setup(hostProps) {
      registry = provideRichTextTargetRegistry();
      provideExamWorkspaceHistoryKeys(keys as ExamWorkspaceHistoryKeys);
      return () =>
        h(ExamWorkspaceRichTextEditor, {
          label: "Frågetext",
          testId: "editor-under-test",
          ...(hostProps.editorProps as EditorProps),
          onUpdate: (body: Body, structural: boolean) => updates.push([body, structural]),
          onCreateGap: (body: Body, gapId: string, seed: string) => creations.push([body, gapId, seed]),
        });
    },
  });
  const wrapper = mount(Host, { attachTo: document.body, props: { editorProps: initial } });
  await nextTick();
  await nextTick();
  const surface = wrapper.get("[data-test='editor-under-test']").element as HTMLElement & { editor?: Editor };
  if (!surface.editor) {
    throw new Error("the editor did not mount");
  }
  const root = wrapper.findComponent(ExamWorkspaceRichTextEditor).element as HTMLElement;
  openedWrappers.push(wrapper);
  return {
    wrapper,
    editor: surface.editor,
    surface,
    root,
    registry,
    updates,
    creations,
    setProps: async (props) => {
      await wrapper.setProps({ editorProps: { ...initial, ...props } });
      await nextTick();
    },
  };
}

function targetOf(opened: Opened) {
  opened.surface.focus();
  const target = opened.registry.active.value;
  if (!target) {
    throw new Error("no active target");
  }
  return target;
}

/** A primary click at `pos` that leaves the given selection behind, as a mousedown would. */
function clickAt(opened: Opened, pos: number): void {
  opened.editor.view.someProp("handleClick", (handler) =>
    handler(opened.editor.view, pos, new MouseEvent("click", { bubbles: true, cancelable: true })),
  );
}

function stubGeometry(opened: Opened, coords: { left: number; top: number; right: number; bottom: number }): void {
  vi.spyOn(opened.editor.view, "coordsAtPos").mockReturnValue({ ...coords, toJSON: () => ({}) } as DOMRect);
}

/** The floating button teleports to `document.body`, outside the wrapper. */
function gapButton(): HTMLElement | null {
  return document.body.querySelector("[data-test='exam-workspace-make-gap']");
}

describe("ExamWorkspaceRichTextEditor makeGap", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    releaseOpenedEditors();
    releaseEditor();
  });

  it("turns the word at the caret into a gap in exactly one createGap event", async () => {
    const opened = await openEditor({ body: [paragraph(text("Huvudstaden är Paris."))], gapsInteractive: true });
    opened.editor.commands.setTextSelection(posIn(opened.editor, "Paris", 1));
    targetOf(opened).makeGap("gap_002");

    expect(opened.creations).toHaveLength(1);
    expect(opened.updates).toHaveLength(0);
    const [body, gapId, seed] = opened.creations[0]!;
    expect(gapId).toBe("gap_002");
    expect(seed).toBe("Paris");
    expect(body).toEqual([paragraph(text("Huvudstaden är "), gap("gap_002"), text("."))]);
    expect(opened.editor.state.selection).toBeInstanceOf(NodeSelection);
  });

  it("turns a selected range into one gap seeded with the trimmed text", async () => {
    const opened = await openEditor({ body: [paragraph(text("Huvudstaden är Paris."))], gapsInteractive: true });
    opened.editor.commands.setTextSelection({
      from: posIn(opened.editor, "är Paris", 0),
      to: posIn(opened.editor, "är Paris", 8),
    });
    targetOf(opened).makeGap("gap_002");

    expect(opened.creations).toHaveLength(1);
    expect(opened.updates).toHaveLength(0);
    const [body, gapId, seed] = opened.creations[0]!;
    expect(gapId).toBe("gap_002");
    expect(seed).toBe("är Paris");
    expect(body).toEqual([paragraph(text("Huvudstaden "), gap("gap_002"), text("."))]);
  });

  it("does nothing for a selection spanning a gap atom", async () => {
    const opened = await openEditor({
      body: [paragraph(text("a"), gap("gap_001"), text("b"))],
      gapsInteractive: true,
    });
    opened.editor.commands.setTextSelection({
      from: posIn(opened.editor, "a", 1),
      to: posIn(opened.editor, "b", 0),
    });
    targetOf(opened).makeGap("gap_002");

    expect(opened.creations).toHaveLength(0);
    expect(opened.updates).toHaveLength(0);
    expect(opened.editor.getText()).toBe("ab");
  });

  it("does nothing for a selection spanning two paragraphs", async () => {
    const opened = await openEditor({
      body: [paragraph(text("first")), paragraph(text("second"))],
      gapsInteractive: true,
    });
    opened.editor.commands.setTextSelection({
      from: posIn(opened.editor, "first", 2),
      to: posIn(opened.editor, "second", 3),
    });
    targetOf(opened).makeGap("gap_002");

    expect(opened.creations).toHaveLength(0);
    expect(opened.updates).toHaveLength(0);
    expect(opened.editor.getText()).toBe("first\n\nsecond");
  });

  it("inserts an empty gap at the caret with an empty seed when the caret is not in a word", async () => {
    const opened = await openEditor({ body: [paragraph(text("ab "))], gapsInteractive: true });
    opened.editor.commands.setTextSelection(posIn(opened.editor, "ab ", 3));
    targetOf(opened).makeGap("gap_002");

    expect(opened.creations).toHaveLength(1);
    expect(opened.updates).toHaveLength(0);
    const [body, gapId, seed] = opened.creations[0]!;
    expect(gapId).toBe("gap_002");
    expect(seed).toBe("");
    expect(body).toEqual([paragraph(text("ab "), gap("gap_002"))]);
  });

  it("does nothing while not interactive or while disabled", async () => {
    const plain = await openEditor({ body: [paragraph(text("Huvudstaden är Paris."))] });
    plain.editor.commands.setTextSelection(posIn(plain.editor, "Paris", 1));
    plain.surface.focus();
    expect(plain.registry.active.value).not.toBeNull();
    plain.registry.active.value?.makeGap("gap_002");
    expect(plain.creations).toHaveLength(0);
    expect(plain.updates).toHaveLength(0);
    expect(plain.editor.getText()).toBe("Huvudstaden är Paris.");

    const disabled = await openEditor({
      body: [paragraph(text("Huvudstaden är Paris."))],
      gapsInteractive: true,
      disabled: true,
    });
    disabled.editor.commands.setTextSelection(posIn(disabled.editor, "Paris", 1));
    disabled.surface.focus();
    disabled.registry.active.value?.makeGap("gap_002");
    expect(disabled.creations).toHaveLength(0);
    expect(disabled.updates).toHaveLength(0);
    expect(disabled.editor.getText()).toBe("Huvudstaden är Paris.");
  });

  it("keeps the gap selection when the owner echoes the emitted body", async () => {
    const opened = await openEditor({ body: [paragraph(text("Huvudstaden är Paris."))], gapsInteractive: true });
    opened.editor.commands.setTextSelection(posIn(opened.editor, "Paris", 1));
    targetOf(opened).makeGap("gap_002");
    const [emitted] = opened.creations[0]!;

    await opened.setProps({ body: emitted });

    expect(opened.editor.state.selection).toBeInstanceOf(NodeSelection);
    expect(opened.editor.getText()).toBe("Huvudstaden är .");
    expect(opened.creations).toHaveLength(1);
    expect(opened.updates).toHaveLength(0);
  });

  describe("floating button", () => {
    it("shows above the clicked word and converts it on click", async () => {
      const opened = await openEditor({
        body: [paragraph(text("Huvudstaden är Paris."))],
        gapsInteractive: true,
        nextGapId: "gap_002",
      });
      stubGeometry(opened, { left: 50, top: 60, right: 90, bottom: 74 });
      opened.editor.commands.setTextSelection(posIn(opened.editor, "Paris", 1));
      clickAt(opened, posIn(opened.editor, "Paris", 1));
      await nextTick();
      await nextTick();

      const button = gapButton();
      expect(button).not.toBeNull();
      expect(button?.textContent).toContain("Gör till lucka");
      expect(button?.getAttribute("aria-label")).toBe("Gör till lucka");
      expect(button?.style.left).toBe("50px");
      expect(button?.style.top).toBe("56px");

      (button as HTMLButtonElement).click();
      await nextTick();
      expect(opened.creations).toHaveLength(1);
      expect(opened.creations[0]![2]).toBe("Paris");
      expect(opened.updates).toHaveLength(0);
      expect(gapButton()).toBeNull();
    });

    it("places the button below the word when there is no room above it", async () => {
      const opened = await openEditor({
        body: [paragraph(text("Huvudstaden är Paris."))],
        gapsInteractive: true,
        nextGapId: "gap_002",
      });
      stubGeometry(opened, { left: 50, top: 10, right: 90, bottom: 24 });
      opened.editor.commands.setTextSelection(posIn(opened.editor, "Paris", 1));
      clickAt(opened, posIn(opened.editor, "Paris", 1));
      await nextTick();
      await nextTick();

      expect(gapButton()?.style.top).toBe("28px");
    });

    it("hides the button when the document changes", async () => {
      const opened = await openEditor({
        body: [paragraph(text("Huvudstaden är Paris."))],
        gapsInteractive: true,
        nextGapId: "gap_002",
      });
      stubGeometry(opened, { left: 50, top: 60, right: 90, bottom: 74 });
      opened.editor.commands.setTextSelection(posIn(opened.editor, "Paris", 1));
      clickAt(opened, posIn(opened.editor, "Paris", 1));
      await nextTick();
      await nextTick();
      expect(gapButton()).not.toBeNull();

      opened.editor.commands.insertContent("x");
      await nextTick();
      expect(gapButton()).toBeNull();
    });

    it("shows nothing without a next gap id or on a space", async () => {
      const opened = await openEditor({
        body: [paragraph(text("Huvudstaden är Paris."))],
        gapsInteractive: true,
      });
      stubGeometry(opened, { left: 50, top: 60, right: 90, bottom: 74 });
      opened.editor.commands.setTextSelection(posIn(opened.editor, "Paris", 1));
      clickAt(opened, posIn(opened.editor, "Paris", 1));
      await nextTick();
      await nextTick();
      expect(gapButton()).toBeNull();

      await opened.setProps({ nextGapId: "gap_002" });
      opened.editor.commands.setTextSelection(posIn(opened.editor, "Paris.", 6));
      expect(opened.editor.state.selection).toBeInstanceOf(TextSelection);
      clickAt(opened, posIn(opened.editor, "Paris.", 6));
      await nextTick();
      await nextTick();
      expect(gapButton()).toBeNull();
    });

    it("reads the clicked word from the click position, not the stale selection", async () => {
      const opened = await openEditor({
        body: [paragraph(text("Huvudstaden är Paris."))],
        gapsInteractive: true,
        nextGapId: "gap_002",
      });
      stubGeometry(opened, { left: 50, top: 60, right: 90, bottom: 74 });
      opened.editor.commands.setTextSelection(1);
      clickAt(opened, posIn(opened.editor, "Paris", 1));
      await nextTick();
      await nextTick();
      expect(gapButton()).not.toBeNull();

      opened.editor.commands.setTextSelection(posIn(opened.editor, "Paris", 3));
      await nextTick();
      expect(gapButton()).not.toBeNull();
    });

    it("stays across a meta-only transaction that redraws the atoms", async () => {
      const opened = await openEditor({
        body: [paragraph(text("Huvudstaden är Paris."))],
        gapsInteractive: true,
        nextGapId: "gap_002",
      });
      stubGeometry(opened, { left: 50, top: 60, right: 90, bottom: 74 });
      opened.editor.commands.setTextSelection(posIn(opened.editor, "Paris", 1));
      clickAt(opened, posIn(opened.editor, "Paris", 1));
      await nextTick();
      await nextTick();
      expect(gapButton()).not.toBeNull();

      opened.editor.view.dispatch(opened.editor.state.tr.setMeta(ATOM_STATE_KEY, true));
      await nextTick();
      expect(gapButton()).not.toBeNull();
    });

    it("hides when the selection moves outside the word", async () => {
      const opened = await openEditor({
        body: [paragraph(text("Huvudstaden är Paris."))],
        gapsInteractive: true,
        nextGapId: "gap_002",
      });
      stubGeometry(opened, { left: 50, top: 60, right: 90, bottom: 74 });
      opened.editor.commands.setTextSelection(posIn(opened.editor, "Paris", 1));
      clickAt(opened, posIn(opened.editor, "Paris", 1));
      await nextTick();
      await nextTick();
      expect(gapButton()).not.toBeNull();

      opened.editor.commands.setTextSelection(posIn(opened.editor, "Huvudstaden", 0));
      await nextTick();
      expect(gapButton()).toBeNull();
    });

    it("converts the whole stored word when the caret moved inside it before confirming", async () => {
      const opened = await openEditor({
        body: [paragraph(text("Huvudstaden är Paris."))],
        gapsInteractive: true,
        nextGapId: "gap_002",
      });
      stubGeometry(opened, { left: 50, top: 60, right: 90, bottom: 74 });
      opened.editor.commands.setTextSelection(1);
      clickAt(opened, posIn(opened.editor, "Paris", 1));
      await nextTick();
      await nextTick();
      expect(gapButton()).not.toBeNull();

      opened.editor.commands.setTextSelection(posIn(opened.editor, "Paris", 4));
      await nextTick();

      (gapButton() as HTMLButtonElement).click();
      await nextTick();
      expect(opened.creations).toHaveLength(1);
      const [body, gapId, seed] = opened.creations[0]!;
      expect(gapId).toBe("gap_002");
      expect(seed).toBe("Paris");
      expect(body).toEqual([paragraph(text("Huvudstaden är "), gap("gap_002"), text("."))]);
      expect(opened.updates).toHaveLength(0);
      expect(gapButton()).toBeNull();
    });

    it("teleports the button to the document body with a fixed position", async () => {
      const opened = await openEditor({
        body: [paragraph(text("Huvudstaden är Paris."))],
        gapsInteractive: true,
        nextGapId: "gap_002",
      });
      stubGeometry(opened, { left: 50, top: 60, right: 90, bottom: 74 });
      opened.editor.commands.setTextSelection(posIn(opened.editor, "Paris", 1));
      clickAt(opened, posIn(opened.editor, "Paris", 1));
      await nextTick();
      await nextTick();

      const button = gapButton();
      expect(button).not.toBeNull();
      expect(button?.parentElement).toBe(document.body);
      expect(button?.classList.contains("fixed")).toBe(true);
    });

    it("hides on window scroll and removes the scroll listener", async () => {
      const opened = await openEditor({
        body: [paragraph(text("Huvudstaden är Paris."))],
        gapsInteractive: true,
        nextGapId: "gap_002",
      });
      stubGeometry(opened, { left: 50, top: 60, right: 90, bottom: 74 });
      opened.editor.commands.setTextSelection(posIn(opened.editor, "Paris", 1));
      clickAt(opened, posIn(opened.editor, "Paris", 1));
      await nextTick();
      await nextTick();
      expect(gapButton()).not.toBeNull();

      const removeSpy = vi.spyOn(window, "removeEventListener");
      window.dispatchEvent(new Event("scroll"));
      await nextTick();
      expect(gapButton()).toBeNull();
      expect(removeSpy).toHaveBeenCalledWith("scroll", expect.any(Function), true);
    });
  });
});
