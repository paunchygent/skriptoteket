/**
 * jsdom has no layout, so a real pointer cannot place a selection. Selections
 * are set through TipTap commands (`setTextSelection`, `setNodeSelection`,
 * `selectAll`); every key is a real `keydown` event dispatched on the editor
 * DOM and handled by the keymaps, and a paste is a real `paste` event. Typed
 * characters are inserted with `insertContent`, because the browser — not
 * ProseMirror — inserts a typed character from a keydown.
 */
import { mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import type { Editor } from "@tiptap/core";
import { afterEach, describe, expect, it, vi } from "vitest";
import { defineComponent, h, nextTick } from "vue";

import type { NativeExamBodyParagraph, NativeExamBodySegment } from "../../../api/examWorkspace";
import type { BodyMark } from "./examWorkspaceBodyMarks";
import { provideExamWorkspaceHistoryKeys } from "./examWorkspaceHistoryKeys";
import type { ExamWorkspaceHistoryKeys } from "./examWorkspaceHistoryKeys";
import ExamWorkspaceRichTextEditor from "./ExamWorkspaceRichTextEditor.vue";
import type { ExamGapState } from "./examWorkspaceRichTextSchema";
import { provideRichTextTargetRegistry } from "./examWorkspaceRichTextTarget";
import type { RichTextTargetRegistry } from "./examWorkspaceRichTextTarget";

type Body = NativeExamBodyParagraph[];
type EditorProps = {
  body: Body;
  label?: string;
  testId?: string;
  disabled?: boolean;
  invalid?: boolean;
  describedBy?: string;
  gapsInteractive?: boolean;
  gapStates?: Record<string, ExamGapState>;
  assetUrls?: Record<string, string>;
};

function text(value: string, marks: BodyMark[] = []): NativeExamBodySegment {
  return { kind: "text", text: value, marks };
}
function gap(id: string): NativeExamBodySegment {
  return { kind: "gap", gap_id: id };
}
function picture(id: string): NativeExamBodySegment {
  return { kind: "asset", asset_id: id };
}
function paragraph(...segments: NativeExamBodySegment[]): NativeExamBodyParagraph {
  return { heading_level: null, segments };
}

type Opened = {
  wrapper: VueWrapper;
  editor: Editor;
  surface: HTMLElement;
  registry: RichTextTargetRegistry;
  updates: Array<[Body, boolean]>;
  activations: Array<[string, HTMLElement]>;
  keys: { undo: ReturnType<typeof vi.fn>; redo: ReturnType<typeof vi.fn> };
  setProps: (props: Partial<EditorProps>) => Promise<void>;
  last: () => Body;
  lastStructural: () => boolean;
};

async function open(
  initial: EditorProps,
  options: { provideKeys?: boolean } = {},
): Promise<Opened> {
  const updates: Array<[Body, boolean]> = [];
  const activations: Array<[string, HTMLElement]> = [];
  const keys = { undo: vi.fn(), redo: vi.fn() };
  let registry!: RichTextTargetRegistry;
  const Host = defineComponent({
    props: { editorProps: { type: Object, required: true } },
    setup(hostProps) {
      registry = provideRichTextTargetRegistry();
      if (options.provideKeys !== false) {
        provideExamWorkspaceHistoryKeys(keys as ExamWorkspaceHistoryKeys);
      }
      return () =>
        h(ExamWorkspaceRichTextEditor, {
          label: "Frågetext",
          testId: "editor-under-test",
          ...(hostProps.editorProps as EditorProps),
          onUpdate: (body: Body, structural: boolean) => updates.push([body, structural]),
          onActivateGap: (gapId: string, element: HTMLElement) => activations.push([gapId, element]),
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
  return {
    wrapper,
    editor: surface.editor,
    surface,
    registry,
    updates,
    activations,
    keys,
    setProps: async (props) => {
      await wrapper.setProps({ editorProps: { ...initial, ...props } });
      await nextTick();
    },
    last: () => {
      const latest = updates.at(-1);
      if (!latest) {
        throw new Error("the editor emitted no update");
      }
      return latest[0];
    },
    lastStructural: () => updates.at(-1)?.[1] ?? false,
  };
}

/** Position `offset` characters into the first text node that contains `needle`. */
function posIn(editor: Editor, needle: string, offset: number): number {
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

/** The position of the first atom of a node type. */
function atomPos(editor: Editor, type: string): number {
  let found = -1;
  editor.state.doc.descendants((node, pos) => {
    if (found < 0 && node.type.name === type) {
      found = pos;
    }
    return found < 0;
  });
  if (found < 0) {
    throw new Error(`no ${type}`);
  }
  return found;
}

function press(
  surface: HTMLElement,
  key: string,
  modifiers: { shiftKey?: boolean; ctrlKey?: boolean; metaKey?: boolean } = {},
): KeyboardEvent {
  // ProseMirror's own delete handling reads `keyCode`, as every browser sets it.
  const keyCode = { Backspace: 8, Enter: 13, Delete: 46 }[key];
  const event = new KeyboardEvent("keydown", { key, keyCode, bubbles: true, cancelable: true, ...modifiers });
  surface.dispatchEvent(event);
  return event;
}

function paste(surface: HTMLElement, html: string, plain = ""): void {
  const event = new Event("paste", { bubbles: true, cancelable: true });
  Object.defineProperty(event, "clipboardData", {
    value: {
      getData: (format: string) => (format === "text/html" ? html : plain),
      types: html ? ["text/html", "text/plain"] : ["text/plain"],
      files: [],
    },
  });
  surface.dispatchEvent(event);
}

const TWO_PARAGRAPHS: Body = [paragraph(text("first")), paragraph(text("second"))];

let current: Opened | null = null;
async function mountEditor(initial: EditorProps, options?: { provideKeys?: boolean }): Promise<Opened> {
  current = await open(initial, options);
  return current;
}

describe("ExamWorkspaceRichTextEditor", () => {
  afterEach(() => {
    current?.wrapper.unmount();
    current = null;
    document.body.innerHTML = "";
  });

  describe("word-processor editing", () => {
    it("deletes a selection across two paragraphs with one Backspace and merges them", async () => {
      const opened = await mountEditor({ body: TWO_PARAGRAPHS });
      opened.editor.commands.setTextSelection({
        from: posIn(opened.editor, "first", 2),
        to: posIn(opened.editor, "second", 3),
      });
      press(opened.surface, "Backspace");
      expect(opened.updates).toHaveLength(1);
      expect(opened.last()).toEqual([paragraph(text("fiond"))]);
    });

    it("deletes a range holding a gap and a picture in one keystroke and reports it as structural", async () => {
      const opened = await mountEditor({
        body: [
          paragraph(text("a"), gap("gap_001"), text("b")),
          paragraph(text("c"), picture("asset_1"), text("d")),
        ],
      });
      opened.editor.commands.setTextSelection({
        from: posIn(opened.editor, "a", 1),
        to: posIn(opened.editor, "d", 0),
      });
      press(opened.surface, "Backspace");
      expect(opened.updates).toHaveLength(1);
      expect(opened.last()).toEqual([paragraph(text("ad"))]);
      expect(opened.lastStructural()).toBe(true);
    });

    it("deletes an atom right after the caret with the first Backspace", async () => {
      // ProseMirror stops the browser's own delete next to a non-text inline
      // node and removes the node itself, so one Backspace deletes it; it does
      // not first select it.
      const opened = await mountEditor({ body: [paragraph(text("a"), gap("gap_001"), text("b"))] });
      const gapPos = atomPos(opened.editor, "examGap");
      opened.editor.commands.setTextSelection(gapPos + 1);
      press(opened.surface, "Backspace");
      expect(opened.updates).toHaveLength(1);
      expect(opened.last()).toEqual([paragraph(text("ab"))]);
      expect(opened.lastStructural()).toBe(true);
    });

    it("deletes a node-selected atom with Backspace and keeps its neighbours", async () => {
      const opened = await mountEditor({ body: [paragraph(text("a"), picture("asset_1"), text("b"))] });
      opened.editor.commands.setNodeSelection(atomPos(opened.editor, "examPicture"));
      press(opened.surface, "Backspace");
      expect(opened.updates).toHaveLength(1);
      expect(opened.last()).toEqual([paragraph(text("ab"))]);
      expect(opened.lastStructural()).toBe(true);
    });

    it("deletes an atom right after the caret with Delete from the other side", async () => {
      const opened = await mountEditor({ body: [paragraph(text("a"), gap("gap_001"), text("b"))] });
      opened.editor.commands.setTextSelection(atomPos(opened.editor, "examGap"));
      press(opened.surface, "Delete");
      expect(opened.last()).toEqual([paragraph(text("ab"))]);
      expect(opened.lastStructural()).toBe(true);
    });

    it("merges a paragraph into the one before it with Backspace at its start", async () => {
      const opened = await mountEditor({ body: TWO_PARAGRAPHS });
      opened.editor.commands.setTextSelection(posIn(opened.editor, "second", 0));
      press(opened.surface, "Backspace");
      expect(opened.last()).toEqual([paragraph(text("firstsecond"))]);
    });

    it("removes an emptied paragraph with Backspace", async () => {
      const opened = await mountEditor({
        body: [paragraph(text("a")), paragraph(text("b")), paragraph(text("c"))],
      });
      opened.editor.commands.setTextSelection({
        from: posIn(opened.editor, "b", 0),
        to: posIn(opened.editor, "b", 1),
      });
      press(opened.surface, "Backspace");
      expect(opened.last()).toEqual([paragraph(text("a")), { heading_level: null, segments: [] }, paragraph(text("c"))]);
      press(opened.surface, "Backspace");
      expect(opened.last()).toEqual([paragraph(text("a")), paragraph(text("c"))]);
    });

    it("emits the empty body when everything is deleted", async () => {
      const opened = await mountEditor({ body: TWO_PARAGRAPHS });
      opened.editor.commands.selectAll();
      press(opened.surface, "Backspace");
      expect(opened.last()).toEqual([]);
    });

    it("splits a paragraph on Enter", async () => {
      const opened = await mountEditor({ body: [paragraph(text("abcd"))] });
      opened.editor.commands.setTextSelection(posIn(opened.editor, "abcd", 2));
      press(opened.surface, "Enter");
      expect(opened.last()).toEqual([paragraph(text("ab")), paragraph(text("cd"))]);
    });

    it("inserts a hard break in the same paragraph on Shift+Enter", async () => {
      const opened = await mountEditor({ body: [paragraph(text("abcd"))] });
      opened.editor.commands.setTextSelection(posIn(opened.editor, "abcd", 2));
      press(opened.surface, "Enter", { shiftKey: true });
      expect(opened.last()).toEqual([paragraph(text("ab\ncd"))]);
    });
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

  describe("paste", () => {
    it("inserts no gap from a pasted fragment that carries a gap element, and keeps the surrounding text", async () => {
      const opened = await mountEditor({ body: [paragraph(text("ab"))] });
      opened.editor.commands.setTextSelection(posIn(opened.editor, "ab", 1));
      paste(
        opened.surface,
        '<p>x<span data-atom="gap" data-gap-id="gap_009"></span>y<span data-atom="asset" data-asset-id="asset_9"></span>z</p>',
      );
      expect(opened.updates.length).toBeGreaterThan(0);
      const [pasted] = opened.last();
      expect(pasted.segments.every((segment) => segment.kind === "text")).toBe(true);
      expect(opened.surface.querySelector("[data-atom]")).toBeNull();
      expect(opened.editor.getText()).toBe("axyzb");
    });

    it("drops the formatting the vocabulary does not keep", async () => {
      const opened = await mountEditor({ body: [paragraph(text("ab"))] });
      opened.editor.commands.setTextSelection(posIn(opened.editor, "ab", 1));
      paste(opened.surface, '<p><a href="https://example.test">link</a> <code>code</code> <b>bold</b></p>');
      const all = opened.last().flatMap((entry) => entry.segments);
      expect(all.some((segment) => segment.kind === "text" && segment.text.includes("bold") && segment.marks.includes("bold"))).toBe(true);
      expect(opened.surface.querySelector("a, code")).toBeNull();
    });
  });

  describe("gaps", () => {
    const GAP_BODY: Body = [paragraph(text("a"), gap("gap_001"), text("b"), picture("asset_1"))];

    it("opens a gap that is clicked when gaps are interactive", async () => {
      const opened = await mountEditor({ body: GAP_BODY, gapsInteractive: true });
      const gapPos = atomPos(opened.editor, "examGap");
      const node = opened.editor.state.doc.nodeAt(gapPos);
      // jsdom has no hit testing, so the pointer cannot choose the target: the
      // view's own click handlers run with the gap as the clicked node.
      const handled = opened.editor.view.someProp("handleClickOn", (handler) =>
        handler(opened.editor.view, gapPos, node!, gapPos, new MouseEvent("click"), true),
      );
      expect(handled).toBe(true);
      expect(opened.activations).toHaveLength(1);
      expect(opened.activations[0][0]).toBe("gap_001");
      expect(opened.activations[0][1]).toBe(opened.surface.querySelector("[data-atom='gap']"));
    });

    it("never opens a picture", async () => {
      const opened = await mountEditor({ body: GAP_BODY, gapsInteractive: true });
      const picturePos = atomPos(opened.editor, "examPicture");
      const node = opened.editor.state.doc.nodeAt(picturePos);
      const handled = opened.editor.view.someProp("handleClickOn", (handler) =>
        handler(opened.editor.view, picturePos, node!, picturePos, new MouseEvent("click"), true),
      );
      expect(handled).toBeFalsy();
      opened.editor.commands.setNodeSelection(picturePos);
      press(opened.surface, "Enter");
      press(opened.surface, " ");
      expect(opened.activations).toHaveLength(0);
    });

    it("opens a node-selected gap on Enter and on Space and does not type into the document", async () => {
      const opened = await mountEditor({ body: GAP_BODY, gapsInteractive: true });
      opened.editor.commands.setNodeSelection(atomPos(opened.editor, "examGap"));
      expect(press(opened.surface, "Enter").defaultPrevented).toBe(true);
      expect(press(opened.surface, " ").defaultPrevented).toBe(true);
      expect(opened.activations.map(([id]) => id)).toEqual(["gap_001", "gap_001"]);
      expect(opened.updates).toHaveLength(0);
    });

    it("does not split the paragraph when Enter is pressed on a gap that is not interactive", async () => {
      const opened = await mountEditor({ body: GAP_BODY });
      const gapPos = atomPos(opened.editor, "examGap");
      const node = opened.editor.state.doc.nodeAt(gapPos);
      const handled = opened.editor.view.someProp("handleClickOn", (handler) =>
        handler(opened.editor.view, gapPos, node!, gapPos, new MouseEvent("click"), true),
      );
      expect(handled).toBeFalsy();
      opened.editor.commands.setNodeSelection(gapPos);
      press(opened.surface, "Enter");
      expect(opened.activations).toHaveLength(0);
    });

    it("opens nothing while disabled", async () => {
      const opened = await mountEditor({ body: GAP_BODY, gapsInteractive: true, disabled: true });
      const gapPos = atomPos(opened.editor, "examGap");
      const node = opened.editor.state.doc.nodeAt(gapPos);
      expect(
        opened.editor.view.someProp("handleClickOn", (handler) =>
          handler(opened.editor.view, gapPos, node!, gapPos, new MouseEvent("click"), true),
        ),
      ).toBeFalsy();
      opened.editor.commands.setNodeSelection(gapPos);
      press(opened.surface, "Enter");
      expect(opened.activations).toHaveLength(0);
    });

    it("draws a changed label and an arriving picture URL in place without an update", async () => {
      const opened = await mountEditor({ body: GAP_BODY, gapsInteractive: true });
      const gapElement = opened.surface.querySelector("[data-atom='gap']") as HTMLElement;
      const pictureElement = opened.surface.querySelector("[data-atom='asset']") as HTMLElement;
      expect(gapElement.dataset.label).toBe("Lucka");
      expect(gapElement.dataset.empty).toBe("true");
      expect(pictureElement.querySelector("img")).toBeNull();

      await opened.setProps({
        gapStates: { gap_001: { label: "Lucka 1", accessibleLabel: "Lucka 1, svar saknas", empty: false } },
      });
      expect(gapElement.dataset.label).toBe("Lucka 1");
      expect(gapElement.getAttribute("aria-label")).toBe("Lucka 1, svar saknas");
      expect(gapElement.dataset.empty).toBeUndefined();

      await opened.setProps({
        gapStates: { gap_001: { label: "Lucka 1", accessibleLabel: "Lucka 1", empty: false } },
        assetUrls: { asset_1: "blob:picture-1" },
      });
      const image = opened.surface.querySelector("[data-atom='asset'] img") as HTMLImageElement | null;
      expect(image?.getAttribute("src")).toBe("blob:picture-1");
      expect(opened.updates).toHaveLength(0);
    });
  });

  describe("body prop and disabled state", () => {
    it("replaces the content when a new body arrives, without emitting an update", async () => {
      const opened = await mountEditor({ body: [paragraph(text("old"))] });
      await opened.setProps({ body: [paragraph(text("new"), gap("gap_001"))] });
      expect(opened.editor.getText()).toContain("new");
      expect(opened.surface.querySelector("[data-atom='gap']")).not.toBeNull();
      expect(opened.updates).toHaveLength(0);
    });

    it("keeps the content and the caret when the owner echoes the last emitted body", async () => {
      const opened = await mountEditor({ body: [paragraph(text("ab"))] });
      opened.editor.commands.setTextSelection(posIn(opened.editor, "ab", 1));
      opened.editor.commands.insertContent("X");
      const echoed = opened.last();
      const caret = opened.editor.state.selection.from;
      await opened.setProps({ body: echoed });
      expect(opened.editor.state.selection.from).toBe(caret);
      expect(opened.editor.getText()).toBe("aXb");
      expect(opened.updates).toHaveLength(1);
    });

    it("treats a body the owner changed back to an earlier value as new content", async () => {
      const opened = await mountEditor({ body: [paragraph(text("ab"))] });
      opened.editor.commands.insertContent("X");
      expect(opened.updates).toHaveLength(1);
      await opened.setProps({ body: [paragraph(text("ab"))] });
      expect(opened.editor.getText()).toBe("ab");
      expect(opened.updates).toHaveLength(1);
    });

    it("counts a later change as structural when it differs from the replaced body's atoms", async () => {
      const opened = await mountEditor({ body: [paragraph(text("a"))] });
      await opened.setProps({ body: [paragraph(text("a"), gap("gap_001"), text("b"))] });
      opened.editor.commands.setTextSelection(posIn(opened.editor, "b", 1));
      opened.editor.commands.insertContent("c");
      expect(opened.lastStructural()).toBe(false);
    });

    it("changes nothing and emits nothing while disabled", async () => {
      const opened = await mountEditor({ body: [paragraph(text("keep"))], disabled: true });
      expect(opened.surface.getAttribute("contenteditable")).toBe("false");
      opened.editor.commands.setTextSelection({ from: posIn(opened.editor, "keep", 0), to: posIn(opened.editor, "keep", 4) });
      press(opened.surface, "Backspace");
      paste(opened.surface, "<p>pasted</p>", "pasted");
      expect(opened.editor.getText()).toBe("keep");
      expect(opened.updates).toHaveLength(0);
    });

    it("becomes editable again when enabled", async () => {
      const opened = await mountEditor({ body: [paragraph(text("abc"))], disabled: true });
      await opened.setProps({ disabled: false });
      expect(opened.surface.getAttribute("contenteditable")).toBe("true");
      opened.editor.commands.setTextSelection({ from: posIn(opened.editor, "abc", 0), to: posIn(opened.editor, "abc", 3) });
      press(opened.surface, "Backspace");
      expect(opened.last()).toEqual([]);
    });

    it("names the surface and follows invalid and describedBy", async () => {
      const opened = await mountEditor({ body: [], label: "Frågetext" });
      expect(opened.surface.getAttribute("aria-label")).toBe("Frågetext");
      expect(opened.surface.getAttribute("aria-invalid")).toBeNull();
      await opened.wrapper.setProps({ editorProps: { body: [], label: "Alternativ 2", invalid: true, describedBy: "err-1" } });
      expect(opened.surface.getAttribute("aria-label")).toBe("Alternativ 2");
      expect(opened.surface.getAttribute("aria-invalid")).toBe("true");
      expect(opened.surface.getAttribute("aria-describedby")).toBe("err-1");
    });
  });
});
