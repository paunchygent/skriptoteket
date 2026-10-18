/**
 * Shared mounting, event, selection and text builders for the
 * `ExamWorkspaceRichTextEditor*.spec.ts` files.
 *
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
import { vi } from "vitest";
import { defineComponent, h, nextTick } from "vue";

import type { NativeExamBodyParagraph, NativeExamBodySegment } from "../../../api/examWorkspace";
import type { BodyMark } from "./examWorkspaceBodyMarks";
import { provideExamWorkspaceHistoryKeys } from "./examWorkspaceHistoryKeys";
import type { ExamWorkspaceHistoryKeys } from "./examWorkspaceHistoryKeys";
import ExamWorkspaceRichTextEditor from "./ExamWorkspaceRichTextEditor.vue";
import type { ExamGapState } from "./examWorkspaceRichTextSchema";
import { provideRichTextTargetRegistry } from "./examWorkspaceRichTextTarget";
import type { RichTextTargetRegistry } from "./examWorkspaceRichTextTarget";

export type Body = NativeExamBodyParagraph[];
export type EditorProps = {
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

export function text(value: string, marks: BodyMark[] = []): NativeExamBodySegment {
  return { kind: "text", text: value, marks };
}
export function gap(id: string): NativeExamBodySegment {
  return { kind: "gap", gap_id: id };
}
export function picture(id: string): NativeExamBodySegment {
  return { kind: "asset", asset_id: id };
}
export function paragraph(...segments: NativeExamBodySegment[]): NativeExamBodyParagraph {
  return { heading_level: null, segments };
}

export type Opened = {
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

/** The position of the first atom of a node type. */
export function atomPos(editor: Editor, type: string): number {
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

export function press(
  surface: HTMLElement,
  key: string,
  modifiers: { altKey?: boolean; shiftKey?: boolean; ctrlKey?: boolean; metaKey?: boolean } = {},
): KeyboardEvent {
  // ProseMirror's own delete handling reads `keyCode`, as every browser sets it.
  const keyCode = { Backspace: 8, Enter: 13, Delete: 46 }[key];
  const event = new KeyboardEvent("keydown", { key, keyCode, bubbles: true, cancelable: true, ...modifiers });
  surface.dispatchEvent(event);
  return event;
}

export function paste(surface: HTMLElement, html: string, plain = ""): void {
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

export const TWO_PARAGRAPHS: Body = [paragraph(text("first")), paragraph(text("second"))];

let current: Opened | null = null;
export async function mountEditor(initial: EditorProps, options?: { provideKeys?: boolean }): Promise<Opened> {
  current = await open(initial, options);
  return current;
}

/** Unmount the editor `mountEditor` opened; every spec calls it after each test. */
export function releaseEditor(): void {
  current?.wrapper.unmount();
  current = null;
  document.body.innerHTML = "";
}
