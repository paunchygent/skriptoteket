/**
 * Exam workspace rich-text editor make-gap spec support.
 *
 * Purpose:
 *   Shared mount and click helpers for the make-gap specs: opening the
 *   editor under test with `createGap`/`update` capture, the active target,
 *   a primary click at a document position, stubbed word coordinates, and
 *   the teleported floating "Lucka" button. jsdom has no layout, so
 *   selections are set through TipTap commands and clicks reach the view
 *   through `someProp("handleClick")`; coordinates are stubbed where the
 *   placement is asserted. The button teleports to document.body, so it is
 *   found through `document` rather than the wrapper.
 */

import { Editor } from "@tiptap/core";
import { mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import { nextTick, reactive } from "vue";
import { defineComponent, h } from "vue";
import { vi } from "vitest";

import type { NativeExamBodyParagraph } from "../../../api/examWorkspace";
import ExamWorkspaceRichTextEditor from "./ExamWorkspaceRichTextEditor.vue";
import { releaseEditor } from "./ExamWorkspaceRichTextEditor.specSupport";
import { provideExamWorkspaceHistoryKeys } from "./examWorkspaceHistoryKeys";
import type { ExamWorkspaceHistoryKeys } from "./examWorkspaceHistoryKeys";
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
  setProps: (props: Partial<EditorProps>) => Promise<void>;
};

const openedWrappers: VueWrapper[] = [];

/** Unmount every editor `openEditor` opened; each spec calls it after each test. */
export function releaseOpenedEditors(): void {
  while (openedWrappers.length > 0) {
    openedWrappers.pop()?.unmount();
  }
}

/** Release both the make-gap editors and the shared rich-text editor surface. */
export function releaseMakeGapEditors(): void {
  releaseOpenedEditors();
  releaseEditor();
}

export type EditorProps = {
  body: Body;
  gapsInteractive?: boolean;
  disabled?: boolean;
  nextGapId?: string | null;
};

export async function openEditor(initial: EditorProps): Promise<Opened> {
  const updates: Array<[Body, boolean]> = [];
  const creations: Creation[] = [];
  let registry!: RichTextTargetRegistry;
  const keys: ExamWorkspaceHistoryKeys = { undo: vi.fn(), redo: vi.fn() };
  const live = reactive<EditorProps>({ ...initial });
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
          onUpdate: (body: Body, structural: boolean) => updates.push([body, structural]),
          onCreateGap: (body: Body, gapId: string, seed: string) => creations.push([body, gapId, seed]),
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
    setProps: async (props) => {
      Object.assign(live, props);
      await nextTick();
    },
  };
}

export function targetOf(opened: Opened) {
  opened.surface.focus();
  const target = opened.registry.active.value;
  if (!target) {
    throw new Error("no active target");
  }
  return target;
}

/** A primary click at `pos` that leaves the given selection behind, as a mousedown would. */
export function clickAt(opened: Opened, pos: number): void {
  opened.editor.view.someProp("handleClick", (handler) =>
    handler(opened.editor.view, pos, new MouseEvent("click", { bubbles: true, cancelable: true })),
  );
}

export function stubGeometry(opened: Opened, coords: { left: number; top: number; right: number; bottom: number }): void {
  const rect = new DOMRect(coords.left, coords.top, coords.right - coords.left, coords.bottom - coords.top);
  vi.spyOn(opened.editor.view, "coordsAtPos").mockReturnValue(rect);
}

/** The floating button teleports to `document.body`, outside the wrapper. */
export function gapButton(): HTMLElement | null {
  const candidate = document.body.querySelector("[data-test='exam-workspace-make-gap']");
  return candidate instanceof HTMLElement ? candidate : null;
}

export function shownGapButton(): HTMLButtonElement {
  const button = gapButton();
  if (!(button instanceof HTMLButtonElement)) {
    throw new Error("the floating gap button did not open");
  }
  return button;
}
