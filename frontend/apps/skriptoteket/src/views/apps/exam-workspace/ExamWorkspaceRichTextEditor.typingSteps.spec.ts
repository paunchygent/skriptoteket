/**
 * Exam workspace rich-text editor: typing-step probe (TASK-SKRIPT-40-04-09 walk finding A2).
 *
 * Domain purpose:
 *   Diagnose why Ångra undid one typed character per press on the staging
 *   walk, when typing must store one step per 900 ms pause
 *   (`EXAM_WORKSPACE_TYPING_PAUSE_MS`). The static trace (discovery scope
 *   `typing-steps`) found no per-keystroke store: `onUpdate` computes
 *   `structural = toolbarEdit || atoms !== knownAtoms || isDiscreteEdit(transaction)`
 *   and only `structural === true` stores at once (`noteEdit`). This probe
 *   records the `structural` flag the real editor emits for each typed
 *   character, typed through ProseMirror the way a browser does
 *   (`handleTextInput`, else an `insertText` transaction; Backspace is the
 *   single-character delete transaction the browser's input handling
 *   produces), then drives the real history with fake timers to show bursts
 *   100 ms apart store once and characters 1000 ms apart store five times.
 *   Each case asserts the correct behaviour, so a per-keystroke
 *   `structural === true` fails here as the found defect.
 *
 * Relationships:
 *   - Reuses `ExamWorkspaceRichTextEditor.specSupport` (`mountEditor` and
 *     positions) and `ExamWorkspaceRichTextEditor.gapTool.specSupport`
 *     (`openEditor`) for mounts; no production code.
 *   - Drives the production editing session through
 *     `useExamWorkspaceEditing.history.specSupport` (`openEditing`) on the
 *     named double of the server's step store.
 */

import { flushPromises, mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import { Editor } from "@tiptap/core";
import { TextSelection } from "@tiptap/pm/state";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { computed, defineComponent, h, nextTick } from "vue";

import type { NativeExamBodyParagraph, NativeExamDocument } from "../../../api/examWorkspace";
import ExamWorkspaceRichTextEditor from "./ExamWorkspaceRichTextEditor.vue";
import { closeGapToolEditors, openEditor } from "./ExamWorkspaceRichTextEditor.gapTool.specSupport";
import type { Body } from "./ExamWorkspaceRichTextEditor.specSupport";
import {
  atomPos,
  gap,
  mountEditor,
  paragraph,
  posIn,
  releaseEditor,
  text,
} from "./ExamWorkspaceRichTextEditor.specSupport";
import { exam, openEditing, stopScopes } from "./useExamWorkspaceEditing.history.specSupport";

const api = vi.hoisted(() => ({
  changeExamWorkspaceItemType: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  saveExamWorkspaceDocument: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
}));
const toast = vi.hoisted(() => ({ failure: vi.fn(), warning: vi.fn() }));

vi.mock("../../../api/examWorkspace", async (original) => ({
  ...(await original<typeof import("../../../api/examWorkspace")>()),
  ...api,
}));
vi.mock("../../../api/examWorkspaceStructureCommands", async (original) => ({
  ...(await original<typeof import("../../../api/examWorkspaceStructureCommands")>()),
  changeExamWorkspaceItemType: api.changeExamWorkspaceItemType,
}));
vi.mock("../../../composables/useToast", () => ({ useToast: () => toast }));

beforeEach(() => {
  for (const fn of [...Object.values(api), ...Object.values(toast)]) fn.mockReset();
});

/** The `structural` flags the editor emitted, one per document change. */
function flagsOf(opened: { updates: Array<[Body, boolean]> }): boolean[] {
  return opened.updates.map(([, structural]) => structural);
}

/**
 * Type one character the way a browser does: ProseMirror's `handleTextInput`
 * props run first at the current selection, and when none handles it an
 * `insertText` transaction carries the character, with the caret placed after
 * it as the browser leaves it. Returns whether a `handleTextInput` prop
 * consumed the character.
 */
function typeChar(editor: Editor, char: string): boolean {
  const { from, to } = editor.state.selection;
  const consumed = editor.view.someProp("handleTextInput", (handler) =>
    handler(editor.view, from, to, char, () => editor.state.tr.insertText(char, from, to)),
  );
  if (consumed === undefined) {
    editor.view.dispatch(editor.state.tr.insertText(char, from, to));
    const caret = editor.state.doc.resolve(from + char.length);
    editor.view.dispatch(editor.state.tr.setSelection(new TextSelection(caret)));
    return false;
  }
  return true;
}

/** Type one character per selection step and return the flags each one emitted. */
function typeText(editor: Editor, chars: string[], opened: { updates: Array<[Body, boolean]> }): boolean[] {
  for (const char of chars) {
    typeChar(editor, char);
  }
  return flagsOf(opened);
}

describe("typing-step probe: the structural flag per typed character", () => {
  afterEach(() => {
    releaseEditor();
    closeGapToolEditors();
    stopScopes();
  });

  it("marks a Backspace that deletes one character as not structural", async () => {
    const opened = await mountEditor({ body: [paragraph(text("hello"))] });
    opened.editor.commands.setTextSelection(posIn(opened.editor, "hello", 3));

    // A bare keydown performs no deletion in jsdom: mid-word Backspace is
    // applied by the browser's input handling, not by ProseMirror's keymap
    // (which only joins at a block start). Dispatch the transaction shape the
    // browser produces: one character gone inside one textblock.
    const { from } = opened.editor.state.selection;
    opened.editor.view.dispatch(opened.editor.state.tr.delete(from - 1, from));
    expect(flagsOf(opened)).toEqual([false]);
    expect(opened.last()).toEqual([paragraph(text("helo"))]);
  });

  it("marks plain typing in the middle of a word as not structural", async () => {
    const opened = await mountEditor({ body: [paragraph(text("hello"))] });
    opened.editor.commands.setTextSelection(posIn(opened.editor, "hello", 2));

    expect(typeText(opened.editor, ["x", "y"], opened)).toEqual([false, false]);
    expect(opened.last()).toEqual([paragraph(text("hexyllo"))]);
  });

  it("marks typing right after a gap chip as not structural", async () => {
    const opened = await mountEditor({ body: [paragraph(text("a"), gap("gap_001"), text("b"))] });
    opened.editor.commands.setTextSelection(atomPos(opened.editor, "examGap") + 1);

    expect(typeText(opened.editor, ["x", "y"], opened)).toEqual([false, false]);
    expect(opened.last()).toEqual([paragraph(text("a"), gap("gap_001"), text("xyb"))]);
  });

  it("marks typing right before a gap chip as not structural", async () => {
    const opened = await mountEditor({ body: [paragraph(text("a"), gap("gap_001"), text("b"))] });
    opened.editor.commands.setTextSelection(atomPos(opened.editor, "examGap"));

    expect(typeText(opened.editor, ["x"], opened)).toEqual([false]);
    expect(opened.last()).toEqual([paragraph(text("ax"), gap("gap_001"), text("b"))]);
  });

  it("marks typing with a bold mark active as not structural", async () => {
    const opened = await mountEditor({ body: [paragraph(text("ab", ["bold"]))] });
    opened.editor.commands.setTextSelection(posIn(opened.editor, "ab", 2));

    expect(typeText(opened.editor, ["c", "d"], opened)).toEqual([false, false]);
    expect(opened.last()).toEqual([paragraph(text("abcd", ["bold"]))]);
  });

  it("marks typing over a selected gap chip structural once, then not structural", async () => {
    const opened = await mountEditor({ body: [paragraph(text("a"), gap("gap_001"), text("b"))] });
    opened.editor.commands.setNodeSelection(atomPos(opened.editor, "examGap"));

    // Replacing the chip removes a gap, which is one structural edit; the
    // characters typed after it are plain typing again.
    expect(typeText(opened.editor, ["x", "y", "z"], opened)).toEqual([true, false, false]);
    expect(opened.last()).toEqual([paragraph(text("axyzb"))]);
  });

  it("marks typing over a selected gap chip the same with the gap tool on", async () => {
    const opened = await openEditor({
      body: [paragraph(text("a"), gap("gap_001"), text("b"))],
      gapsInteractive: true,
      gapTool: true,
      nextGapId: "gap_002",
    });
    opened.editor.commands.setNodeSelection(atomPos(opened.editor, "examGap"));

    expect(typeText(opened.editor, ["x", "y"], opened)).toEqual([true, false]);
    expect(opened.updates.at(-1)?.[0]).toEqual([paragraph(text("axyb"))]);
  });

  it("marks typing after an installed step as not structural", async () => {
    const opened = await mountEditor({ body: [paragraph(text("hello"))] });
    opened.editor.commands.setTextSelection(posIn(opened.editor, "hello", 5));
    typeChar(opened.editor, "!");

    // Ångra installs a stored step through `props.body`: the watcher redraws
    // without emitting and resets the known atoms.
    await opened.setProps({ body: [paragraph(text("hello"))] });
    expect(opened.updates).toHaveLength(1);

    opened.editor.commands.setTextSelection(posIn(opened.editor, "hello", 5));
    typeChar(opened.editor, "?");
    expect(flagsOf(opened)).toEqual([false, false]);
  });
});

describe("typing-step probe: bursts through the real history", () => {
  const mounted: VueWrapper[] = [];

  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    for (const wrapper of mounted.splice(0)) wrapper.unmount();
    releaseEditor();
    stopScopes();
    vi.useRealTimers();
  });

  async function elapse(ms: number): Promise<void> {
    await vi.advanceTimersByTimeAsync(ms);
    await flushPromises();
  }

  function baselineWith(body: NativeExamBodyParagraph[]): NativeExamDocument {
    const document = exam("Prov", 1);
    return { ...document, items: [{ ...document.items[0]!, body }] };
  }

  /** The editor on the session's first item, wired as the body editor wires it. */
  async function mountOnSession(editing: Awaited<ReturnType<typeof openEditing>>["editing"]) {
    const Host = defineComponent({
      setup() {
        const item = computed(() => editing.workspaceDocument.value!.items[0]!);
        return () =>
          h(ExamWorkspaceRichTextEditor, {
            body: item.value.body,
            label: "Frågetext",
            testId: "session-editor",
            onUpdate: (body: NativeExamBodyParagraph[], structural: boolean) =>
              editing.updateItemBody(item.value.item_id, body, structural),
          });
      },
    });
    const wrapper = mount(Host, { attachTo: document.body });
    mounted.push(wrapper);
    await nextTick();
    await nextTick();
    const candidate = wrapper.get("[data-test='session-editor']").element;
    if (!(candidate instanceof HTMLElement) || !("editor" in candidate)) {
      throw new Error("the editor did not mount");
    }
    const attached = candidate.editor;
    if (!(attached instanceof Editor)) {
      throw new Error("the editor did not mount");
    }
    return { wrapper, surface: candidate, editor: attached };
  }

  it("stores five characters 100 ms apart as exactly one step", async () => {
    const { editing, server } = await openEditing(api, baselineWith([paragraph(text("Fråga"))]));
    const session = await mountOnSession(editing);
    session.editor.commands.setTextSelection(posIn(session.editor, "Fråga", 5));

    for (const char of ["a", "b", "c", "d", "e"]) {
      typeChar(session.editor, char);
      await elapse(100);
    }
    // The 900 ms pause has not fired since the last character.
    expect(api.storeExamWorkspaceUndoStep).not.toHaveBeenCalled();

    await elapse(1000);
    expect(server.state.steps).toHaveLength(1);
    expect(editing.history.pending.value).toBe(false);
  });

  it("stores five characters 1000 ms apart as five steps", async () => {
    const { editing, server } = await openEditing(api, baselineWith([paragraph(text("Fråga"))]));
    const session = await mountOnSession(editing);
    session.editor.commands.setTextSelection(posIn(session.editor, "Fråga", 5));

    for (const char of ["a", "b", "c", "d", "e"]) {
      typeChar(session.editor, char);
      // Each pause fires before the next character, so each one stores.
      await elapse(1000);
    }
    expect(server.state.steps).toHaveLength(5);
    expect(editing.history.pending.value).toBe(false);
  });
});
