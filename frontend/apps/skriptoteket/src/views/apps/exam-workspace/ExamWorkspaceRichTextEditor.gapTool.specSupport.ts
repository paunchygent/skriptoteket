/**
 * Exam workspace rich-text editor gap tool spec support: shared mount helpers.
 *
 * Domain purpose:
 *   Mount the editor under test with gap tool event capture (`update`,
 *   `createGap`, `activateGap`, `toggleGapTool`, `escape`) so the gap tool
 *   specs can drive clicks, drag releases and geometry through the same
 *   host. jsdom has no layout, so pointer hits still resolve through the
 *   stubbed linear character grid in
 *   `examWorkspaceGapToolPointer.specSupport`.
 *
 * Relationships:
 *   - Used by `ExamWorkspaceRichTextEditor.gapTool.spec.ts` (pointer and
 *     selection conversion) and
 *     `ExamWorkspaceRichTextEditor.gapToolWiring.spec.ts` (shortcut and
 *     Escape wiring).
 *   - Reuses `ExamWorkspaceRichTextEditor.specSupport` and
 *     `examWorkspaceGapToolPointer.specSupport`; no production code.
 */

import { mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import { Editor } from "@tiptap/core";
import { defineComponent, h, nextTick, reactive, ref } from "vue";
import { vi } from "vitest";

import type { NativeExamBodyParagraph } from "../../../api/examWorkspace";
import ExamWorkspaceRichTextEditor from "./ExamWorkspaceRichTextEditor.vue";
import { releaseEditor } from "./ExamWorkspaceRichTextEditor.specSupport";
import { provideExamWorkspaceHistoryKeys } from "./examWorkspaceHistoryKeys";
import type { ExamWorkspaceHistoryKeys } from "./examWorkspaceHistoryKeys";
import { dispatchGapToolClick } from "./examWorkspaceGapToolPointer.specSupport";
import { provideRichTextTargetRegistry } from "./examWorkspaceRichTextTarget";
import type { RichTextTargetRegistry } from "./examWorkspaceRichTextTarget";

export type Body = NativeExamBodyParagraph[];
export type Creation = [Body, string, string];

export type Opened = {
  wrapper: VueWrapper;
  editor: Editor;
  surface: HTMLElement;
  registry: RichTextTargetRegistry;
  updates: Array<[Body, boolean]>;
  creations: Creation[];
  activations: Array<[string, HTMLElement]>;
  toggles: string[];
  escapes: string[];
  setProps: (props: Partial<EditorProps>) => Promise<void>;
};

export type EditorProps = {
  body: Body;
  gapsInteractive?: boolean;
  disabled?: boolean;
  nextGapId?: string | null;
  gapTool?: boolean;
};

const openedWrappers: VueWrapper[] = [];

export async function openEditor(initial: EditorProps): Promise<Opened> {
  const updates: Array<[Body, boolean]> = [];
  const creations: Creation[] = [];
  const activations: Array<[string, HTMLElement]> = [];
  const toggles: string[] = [];
  const escapes: string[] = [];
  const keys: ExamWorkspaceHistoryKeys = { undo: vi.fn(), redo: vi.fn(), canUndo: ref(false), canRedo: ref(false) };
  const live = reactive<EditorProps>({ ...initial });
  let registry!: RichTextTargetRegistry;
  const Host = defineComponent({
    setup() {
      registry = provideRichTextTargetRegistry();
      provideExamWorkspaceHistoryKeys(keys);
      return () =>
        h(ExamWorkspaceRichTextEditor, {
          label: "Frågetext",
          testId: "editor-under-test",
          body: live.body,
          gapsInteractive: live.gapsInteractive,
          disabled: live.disabled,
          nextGapId: live.nextGapId,
          gapTool: live.gapTool,
          onUpdate: (body: Body, structural: boolean) => updates.push([body, structural]),
          onCreateGap: (body: Body, gapId: string, seed: string) => creations.push([body, gapId, seed]),
          onActivateGap: (gapId: string, element: HTMLElement) => activations.push([gapId, element]),
          onToggleGapTool: () => toggles.push("toggle"),
          onEscape: () => escapes.push("escape"),
        });
    },
  });
  const wrapper = mount(Host, { attachTo: document.body });
  await nextTick();
  await nextTick();
  const candidate = wrapper.get("[data-test='editor-under-test']").element;
  if (!(candidate instanceof HTMLElement) || !("editor" in candidate)) {
    throw new Error("the editor did not mount");
  }
  const attached = candidate.editor;
  if (!(attached instanceof Editor)) {
    throw new Error("the editor did not mount");
  }
  openedWrappers.push(wrapper);
  return {
    wrapper,
    editor: attached,
    surface: candidate,
    registry,
    updates,
    creations,
    activations,
    toggles,
    escapes,
    setProps: async (props) => {
      Object.assign(live, props);
      await nextTick();
    },
  };
}

/** Unmount every editor opened through this support and release its editor. */
export function closeGapToolEditors(): void {
  while (openedWrappers.length > 0) {
    openedWrappers.pop()?.unmount();
  }
  releaseEditor();
}

/** A primary click at `pos` with the pointer at `clientX`; returns whether a handler consumed it. */
export function clickAt(opened: Opened, pos: number, clientX = 0): unknown {
  return dispatchGapToolClick(opened.editor, pos, clientX);
}

/** A real DOM press on the surface, as ProseMirror's `handleDOMEvents` sees it. */
export function pressMouse(opened: Opened, type: "mousedown" | "mouseup", button: number): void {
  opened.surface.dispatchEvent(new MouseEvent(type, { bubbles: true, cancelable: true, button }));
}

/** A primary drag release: mousedown button 0, then a real mouseup, then the tool's next tick. */
export async function releaseMouse(opened: Opened): Promise<void> {
  pressMouse(opened, "mousedown", 0);
  pressMouse(opened, "mouseup", 0);
  await new Promise((resolve) => setTimeout(resolve, 0));
  await nextTick();
}

/** The floating button is removed: this query always finds nothing. */
export function gapButton(): HTMLElement | null {
  const candidate = document.body.querySelector("[data-test='exam-workspace-make-gap']");
  return candidate instanceof HTMLElement ? candidate : null;
}

/** The active rich-text target, after focusing the surface as a toolbar would. */
export function targetOf(opened: Opened) {
  opened.surface.focus();
  const target = opened.registry.active.value;
  if (!target) {
    throw new Error("no active target");
  }
  return target;
}
