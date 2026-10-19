/**
 * Exam workspace rich-text editor: the structural flag, the formatting
 * toolbar and the workspace history keys.
 *
 * Expected behavior (TASK-SKRIPT-40-04-06 D1, D2):
 *   - `update(body, structural)` is structural for a toolbar click, for a
 *     keyboard mark (Ctrl/Cmd+B, I, U), for a heading change and for
 *     deleting text across paragraphs, because the editor reads those from
 *     the transaction itself. Typing, Enter, Shift+Enter, a Backspace that
 *     only merges two paragraphs and paste coalesce.
 *   - Wired to the production editing session, each structural edit is its
 *     own Ångra step: Ctrl+B then Ctrl+I take two Ångra to undo, and a
 *     cross-paragraph delete undoes without the typing before it.
 *   - Ctrl/Cmd+Z, Ctrl/Cmd+Shift+Z and Ctrl+Y call the workspace history and
 *     the editor holds no history of its own.
 *
 * Keys are real `keydown` events handled by the editor's keymaps; marks and
 * headings from the toolbar go through the registered `RichTextTarget`.
 * Typed characters are `insertContent` (the browser inserts them). The
 * editing session is the production composable on a named double of the
 * server's step store.
 */

import { flushPromises, mount } from "@vue/test-utils";
import type { Editor } from "@tiptap/core";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { computed, defineComponent, h, nextTick } from "vue";

import type { NativeExamBodyParagraph, NativeExamDocument } from "../../../api/examWorkspace";
import ExamWorkspaceRichTextEditor from "./ExamWorkspaceRichTextEditor.vue";
import {
  mountEditor,
  paragraph,
  paste,
  posIn,
  press,
  releaseEditor,
  text,
  TWO_PARAGRAPHS,
} from "./ExamWorkspaceRichTextEditor.specSupport";
import { exam, openEditing, stopScopes } from "./useExamWorkspaceEditing.history.specSupport";

const api = vi.hoisted(() => ({
  changeExamWorkspaceItemType: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
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
vi.mock("../../../api/examWorkspaceStructureCommands", async (original) => ({
  ...(await original<typeof import("../../../api/examWorkspaceStructureCommands")>()),
  changeExamWorkspaceItemType: api.changeExamWorkspaceItemType,
}));
vi.mock("../../../composables/useToast", () => ({ useToast: () => toast }));

beforeEach(() => {
  for (const fn of [...Object.values(api), ...Object.values(toast)]) fn.mockReset();
});

describe("ExamWorkspaceRichTextEditor", () => {
  afterEach(() => {
    releaseEditor();
    stopScopes();
  });

  describe("structural flag and the formatting toolbar", () => {
    it("reports typed text as not structural", async () => {
      const opened = await mountEditor({ body: [paragraph(text("ab"))] });
      opened.editor.commands.setTextSelection(posIn(opened.editor, "ab", 2));
      opened.editor.commands.insertContent("c");
      expect(opened.last()).toEqual([paragraph(text("abc"))]);
      expect(opened.lastStructural()).toBe(false);
    });

    it("applies a mark through the active target in one structural step", async () => {
      const opened = await mountEditor({ body: [paragraph(text("hello"))] });
      opened.surface.focus();
      const target = opened.registry.active.value;
      expect(target).not.toBeNull();
      opened.editor.commands.setTextSelection({ from: posIn(opened.editor, "hello", 0), to: posIn(opened.editor, "hello", 5) });
      target?.toggleMark("bold");
      expect(opened.last()).toEqual([paragraph(text("hello", ["bold"]))]);
      expect(opened.lastStructural()).toBe(true);
      expect(target?.marks.value).toEqual(["bold"]);

      target?.toggleMark("bold");
      expect(opened.last()).toEqual([paragraph(text("hello"))]);
      expect(target?.marks.value).toEqual([]);

      opened.editor.commands.insertContent("!");
      expect(opened.lastStructural()).toBe(false);
    });

    it("leaves only subscript after superscript and then subscript", async () => {
      const opened = await mountEditor({ body: [paragraph(text("x2"))] });
      opened.surface.focus();
      const target = opened.registry.active.value;
      opened.editor.commands.setTextSelection({ from: posIn(opened.editor, "x2", 1), to: posIn(opened.editor, "x2", 2) });
      target?.toggleMark("superscript");
      expect(opened.last()).toEqual([paragraph(text("x"), text("2", ["superscript"]))]);
      target?.toggleMark("subscript");
      expect(opened.last()).toEqual([paragraph(text("x"), text("2", ["subscript"]))]);
      expect(target?.marks.value).toEqual(["subscript"]);
    });

    it("toggles a heading level and back to a plain paragraph", async () => {
      const opened = await mountEditor({ body: [paragraph(text("title"))] });
      opened.surface.focus();
      const target = opened.registry.active.value;
      opened.editor.commands.setTextSelection(posIn(opened.editor, "title", 2));
      expect(target?.headingLevel()).toBeNull();
      target?.toggleHeading(2);
      expect(opened.last()).toEqual([{ heading_level: 2, segments: [text("title")] }]);
      expect(opened.lastStructural()).toBe(true);
      expect(target?.headingLevel()).toBe(2);
      target?.toggleHeading(3);
      expect(opened.last()[0].heading_level).toBe(3);
      target?.toggleHeading(3);
      expect(opened.last()).toEqual([paragraph(text("title"))]);
      expect(target?.headingLevel()).toBeNull();
    });

    it("becomes the toolbar's active target on focus, emits focus, and leaves the registry on unmount", async () => {
      const opened = await mountEditor({ body: [paragraph(text("a"))] });
      expect(opened.registry.active.value).toBeNull();
      opened.surface.focus();
      expect(opened.registry.active.value).not.toBeNull();
      expect(opened.wrapper.findComponent(ExamWorkspaceRichTextEditor).emitted("focus")).toHaveLength(1);
      opened.wrapper.unmount();
      expect(opened.registry.active.value).toBeNull();
    });
  });

  describe("workspace history keys", () => {
    it.each([
      ["Ctrl+Z", "z", { ctrlKey: true }, "undo"],
      ["Ctrl+Shift+Z", "Z", { ctrlKey: true, shiftKey: true }, "redo"],
      ["Ctrl+Y", "y", { ctrlKey: true }, "redo"],
    ] as const)("%s calls the workspace, swallows the event and leaves the text alone", async (_name, key, modifiers, call) => {
      const opened = await mountEditor({ body: [paragraph(text("keep"))] });
      opened.editor.commands.setTextSelection(posIn(opened.editor, "keep", 2));
      const event = press(opened.surface, key, modifiers);
      expect(event.defaultPrevented).toBe(true);
      const other = call === "undo" ? "redo" : "undo";
      expect(opened.keys[call]).toHaveBeenCalledTimes(1);
      expect(opened.keys[other]).not.toHaveBeenCalled();
      expect(opened.updates).toHaveLength(0);
      expect(opened.editor.getText()).toBe("keep");
    });

    it("still swallows the keys without a provider, and the document is unchanged", async () => {
      const opened = await mountEditor({ body: [paragraph(text("keep"))] }, { provideKeys: false });
      for (const [key, modifiers] of [
        ["z", { ctrlKey: true }],
        ["Z", { ctrlKey: true, shiftKey: true }],
        ["y", { ctrlKey: true }],
      ] as const) {
        expect(press(opened.surface, key, modifiers).defaultPrevented).toBe(true);
      }
      expect(opened.keys.undo).not.toHaveBeenCalled();
      expect(opened.updates).toHaveLength(0);
      expect(opened.editor.getText()).toBe("keep");
    });

    it("does not undo typed text locally: the editor holds no history", async () => {
      const opened = await mountEditor({ body: [paragraph(text("ab"))] });
      opened.editor.commands.setTextSelection(posIn(opened.editor, "ab", 2));
      opened.editor.commands.insertContent("c");
      press(opened.surface, "z", { ctrlKey: true });
      expect(opened.editor.getText()).toBe("abc");
      expect(opened.keys.undo).toHaveBeenCalledTimes(1);
    });
  });

  describe("keyboard and range edits are classified from the transaction", () => {
    // Every case below is a real keydown, except typing and paste, which are
    // an inserted character and a real paste event.
    async function openWithSelection(body: NativeExamBodyParagraph[], needle: string, from: number, to: number) {
      const opened = await mountEditor({ body });
      opened.editor.commands.setTextSelection({ from: posIn(opened.editor, needle, from), to: posIn(opened.editor, needle, to) });
      return opened;
    }

    it("reports Ctrl+B, then Ctrl+I, then Ctrl+B again as three structural edits", async () => {
      const opened = await openWithSelection([paragraph(text("hello world"))], "hello world", 6, 11);
      press(opened.surface, "b", { ctrlKey: true });
      expect(opened.updates.map(([, structural]) => structural)).toEqual([true]);
      expect(opened.last()).toEqual([paragraph(text("hello "), text("world", ["bold"]))]);

      press(opened.surface, "i", { ctrlKey: true });
      expect(opened.updates.map(([, structural]) => structural)).toEqual([true, true]);
      expect(opened.last()[0]!.segments[1]).toEqual(text("world", ["bold", "italic"]));

      press(opened.surface, "b", { ctrlKey: true });
      expect(opened.updates.map(([, structural]) => structural)).toEqual([true, true, true]);
      expect(opened.last()[0]!.segments[1]).toEqual(text("world", ["italic"]));
    });

    it("reports Ctrl+U as structural", async () => {
      const opened = await openWithSelection([paragraph(text("hello"))], "hello", 0, 5);
      press(opened.surface, "u", { ctrlKey: true });
      expect(opened.last()).toEqual([paragraph(text("hello", ["underline"]))]);
      expect(opened.lastStructural()).toBe(true);
    });

    it("reports the heading key and its reverse as structural", async () => {
      const opened = await openWithSelection([paragraph(text("title"))], "title", 2, 2);
      press(opened.surface, "1", { ctrlKey: true, altKey: true });
      expect(opened.last()).toEqual([{ heading_level: 1, segments: [text("title")] }]);
      expect(opened.lastStructural()).toBe(true);

      press(opened.surface, "0", { ctrlKey: true, altKey: true });
      expect(opened.last()).toEqual([paragraph(text("title"))]);
      expect(opened.updates).toHaveLength(2);
      expect(opened.lastStructural()).toBe(true);
    });

    it("reports typed characters as not structural, also inside bold text", async () => {
      const opened = await openWithSelection([paragraph(text("ab", ["bold"]))], "ab", 2, 2);
      opened.editor.commands.insertContent("c");
      opened.editor.commands.insertContent("d");
      expect(opened.last()).toEqual([paragraph(text("abcd", ["bold"]))]);
      expect(opened.updates.map(([, structural]) => structural)).toEqual([false, false]);
    });

    it("reports Enter and Shift+Enter as not structural", async () => {
      const opened = await openWithSelection([paragraph(text("abcd"))], "abcd", 2, 2);
      press(opened.surface, "Enter");
      expect(opened.last()).toEqual([paragraph(text("ab")), paragraph(text("cd"))]);
      expect(opened.lastStructural()).toBe(false);

      press(opened.surface, "Enter", { shiftKey: true });
      expect(opened.last()).toEqual([paragraph(text("ab")), paragraph(text("\ncd"))]);
      expect(opened.updates).toHaveLength(2);
      expect(opened.lastStructural()).toBe(false);
    });

    it("reports a Backspace that only merges two paragraphs as not structural", async () => {
      const opened = await openWithSelection(TWO_PARAGRAPHS, "second", 0, 0);
      press(opened.surface, "Backspace");
      expect(opened.last()).toEqual([paragraph(text("firstsecond"))]);
      expect(opened.updates).toHaveLength(1);
      expect(opened.lastStructural()).toBe(false);
    });

    it("reports a Backspace that removes an empty paragraph as not structural", async () => {
      const opened = await openWithSelection(
        [paragraph(text("a")), { heading_level: null, segments: [] }, paragraph(text("c"))],
        "c",
        0,
        0,
      );
      press(opened.surface, "Backspace");
      expect(opened.last()).toEqual([paragraph(text("a")), paragraph(text("c"))]);
      expect(opened.lastStructural()).toBe(false);
    });

    it("reports a Backspace over a word inside one paragraph as not structural", async () => {
      const opened = await openWithSelection([paragraph(text("hello world")), paragraph(text("next"))], "hello world", 5, 11);
      press(opened.surface, "Backspace");
      expect(opened.last()).toEqual([paragraph(text("hello")), paragraph(text("next"))]);
      expect(opened.lastStructural()).toBe(false);
    });

    it("reports a Backspace over text across two paragraphs as structural", async () => {
      const opened = await mountEditor({ body: TWO_PARAGRAPHS });
      opened.editor.commands.setTextSelection({
        from: posIn(opened.editor, "first", 2),
        to: posIn(opened.editor, "second", 3),
      });
      press(opened.surface, "Backspace");
      expect(opened.last()).toEqual([paragraph(text("fiond"))]);
      expect(opened.lastStructural()).toBe(true);
    });

    it("reports a Backspace over everything in several paragraphs as structural", async () => {
      const opened = await mountEditor({ body: TWO_PARAGRAPHS });
      opened.editor.commands.selectAll();
      press(opened.surface, "Backspace");
      expect(opened.last()).toEqual([]);
      expect(opened.lastStructural()).toBe(true);
    });

    it("reports typing over a selection that spans paragraphs as structural, because it deletes that range", async () => {
      const opened = await mountEditor({ body: TWO_PARAGRAPHS });
      opened.editor.commands.setTextSelection({
        from: posIn(opened.editor, "first", 2),
        to: posIn(opened.editor, "second", 3),
      });
      opened.editor.commands.insertContent("X");
      expect(opened.last()).toEqual([paragraph(text("fiXond"))]);
      expect(opened.lastStructural()).toBe(true);
    });

    it("reports a paste at the caret as not structural", async () => {
      const opened = await openWithSelection([paragraph(text("ab"))], "ab", 1, 1);
      paste(opened.surface, "<p>x</p><p>y</p>", "x\ny");
      expect(opened.updates.length).toBeGreaterThan(0);
      expect(opened.editor.getText({ blockSeparator: "|" })).toBe("ax|yb");
      expect(opened.updates.every(([, structural]) => !structural)).toBe(true);
    });
  });

  describe("each structural edit is its own Ångra step in the editing session", () => {
    const BODY: NativeExamBodyParagraph[] = [paragraph(text("hello world")), paragraph(text("second")), paragraph(text("third"))];

    function baselineWith(body: NativeExamBodyParagraph[]): NativeExamDocument {
      const document = exam("Prov", 1);
      return { ...document, items: [{ ...document.items[0]!, body }] };
    }

    /** The editor on the session's first item, wired as the body editor wires it: edits go to `updateItemBody`. */
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
      await nextTick();
      await nextTick();
      const surface = wrapper.get("[data-test='session-editor']").element as HTMLElement & { editor?: Editor };
      if (!surface.editor) {
        throw new Error("the editor did not mount");
      }
      return { wrapper, surface, editor: surface.editor };
    }

    function bodyOf(editing: Awaited<ReturnType<typeof openEditing>>["editing"]): NativeExamBodyParagraph[] {
      return editing.workspaceDocument.value!.items[0]!.body;
    }

    function marksOfWord(body: NativeExamBodyParagraph[], word: string): string[] {
      const segment = body.flatMap((entry) => entry.segments).find((entry) => entry.kind === "text" && entry.text === word);
      return segment?.kind === "text" ? [...segment.marks].sort() : [];
    }

    it("undoes Ctrl+I, then Ctrl+B, one Ångra each", async () => {
      const { editing } = await openEditing(api, baselineWith(BODY));
      const { wrapper, surface, editor } = await mountOnSession(editing);
      editor.commands.setTextSelection({ from: posIn(editor, "hello world", 6), to: posIn(editor, "hello world", 11) });
      press(surface, "b", { ctrlKey: true });
      press(surface, "i", { ctrlKey: true });
      expect(marksOfWord(bodyOf(editing), "world")).toEqual(["bold", "italic"]);

      await editing.history.undo();
      await flushPromises();
      expect(marksOfWord(bodyOf(editing), "world")).toEqual(["bold"]);

      await editing.history.undo();
      await flushPromises();
      expect(marksOfWord(bodyOf(editing), "hello world")).toEqual([]);
      expect(bodyOf(editing)).toEqual(BODY);
      wrapper.unmount();
    });

    it("undoes a cross-paragraph delete without the text typed before it", async () => {
      const { editing } = await openEditing(api, baselineWith(BODY));
      const { wrapper, surface, editor } = await mountOnSession(editing);
      editor.commands.setTextSelection(posIn(editor, "third", 5));
      editor.commands.insertContent("abc");
      expect(bodyOf(editing)[2]).toEqual(paragraph(text("thirdabc")));

      editor.commands.setTextSelection({ from: posIn(editor, "hello world", 2), to: posIn(editor, "second", 3) });
      press(surface, "Backspace");
      expect(bodyOf(editing)).toEqual([paragraph(text("heond")), paragraph(text("thirdabc"))]);

      await editing.history.undo();
      await flushPromises();
      expect(bodyOf(editing)).toEqual([paragraph(text("hello world")), paragraph(text("second")), paragraph(text("thirdabc"))]);

      await editing.history.undo();
      await flushPromises();
      expect(bodyOf(editing)).toEqual(BODY);
      wrapper.unmount();
    });
  });
});
