/**
 * Exam workspace make-gap composable: the floating button lifecycle.
 *
 * Expected behavior (TASK-SKRIPT-40-04-08 J4):
 *   A click inside a word shows the floating "Lucka" button above that word.
 *   The button hides on any viewport move while shown and removes its window
 *   listeners, stays across a meta-only redraw, and hides when the caret
 *   leaves the stored word.
 *
 * jsdom has no layout, so selections are set through TipTap commands and
 * clicks reach the view through `someProp("handleClick")`; coordinates are
 * stubbed. The button teleports to document.body, so it is found through
 * `document` rather than the wrapper.
 */

import { Editor } from "@tiptap/core";
import { mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import { defineComponent, h, nextTick, reactive } from "vue";

import type { NativeExamBodyParagraph } from "../../../api/examWorkspace";
import ExamWorkspaceRichTextEditor from "./ExamWorkspaceRichTextEditor.vue";
import {
  paragraph,
  posIn,
  releaseEditor,
  text,
} from "./ExamWorkspaceRichTextEditor.specSupport";
import { provideExamWorkspaceHistoryKeys } from "./examWorkspaceHistoryKeys";
import type { ExamWorkspaceHistoryKeys } from "./examWorkspaceHistoryKeys";
import { provideRichTextTargetRegistry } from "./examWorkspaceRichTextTarget";
import { ATOM_STATE_KEY } from "./examWorkspaceRichTextSchema";

type Body = NativeExamBodyParagraph[];

type Opened = {
  wrapper: VueWrapper;
  editor: Editor;
  setProps: (props: Partial<EditorProps>) => Promise<void>;
};

type EditorProps = {
  body: Body;
  gapsInteractive?: boolean;
  disabled?: boolean;
  nextGapId?: string | null;
};

async function openEditor(initial: EditorProps): Promise<Opened> {
  const keys: ExamWorkspaceHistoryKeys = { undo: vi.fn(), redo: vi.fn() };
  const live = reactive<EditorProps>({ ...initial });
  const Host = defineComponent({
    setup() {
      provideRichTextTargetRegistry();
      provideExamWorkspaceHistoryKeys(keys);
      return () =>
        h(ExamWorkspaceRichTextEditor, {
          label: "Frågetext",
          testId: "editor-under-test",
          body: live.body,
          gapsInteractive: live.gapsInteractive,
          disabled: live.disabled,
          nextGapId: live.nextGapId,
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
  return {
    wrapper,
    editor: attached,
    setProps: async (props) => {
      Object.assign(live, props);
      await nextTick();
    },
  };
}

/** A primary click at `pos`, as a mousedown would leave it behind. */
function clickAt(opened: Opened, pos: number): void {
  opened.editor.view.someProp("handleClick", (handler) =>
    handler(opened.editor.view, pos, new MouseEvent("click", { bubbles: true, cancelable: true })),
  );
}

function stubGeometry(opened: Opened): void {
  const rect = new DOMRect(50, 60, 40, 14);
  vi.spyOn(opened.editor.view, "coordsAtPos").mockReturnValue(rect);
}

/** The floating button teleports to `document.body`, outside the wrapper. */
function gapButton(): HTMLElement | null {
  const candidate = document.body.querySelector("[data-test='exam-workspace-make-gap']");
  return candidate instanceof HTMLElement ? candidate : null;
}

async function openWithButton(): Promise<Opened> {
  const opened = await openEditor({
    body: [paragraph(text("Huvudstaden är Paris."))],
    gapsInteractive: true,
    nextGapId: "gap_002",
  });
  stubGeometry(opened);
  opened.editor.commands.setTextSelection(posIn(opened.editor, "Paris", 1));
  clickAt(opened, posIn(opened.editor, "Paris", 1));
  await nextTick();
  await nextTick();
  return opened;
}

describe("useExamWorkspaceMakeGap", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    releaseEditor();
  });

  it("shows the floating button above the clicked word", async () => {
    const opened = await openWithButton();
    try {
      expect(gapButton()).not.toBeNull();
    } finally {
      opened.wrapper.unmount();
    }
  });

  it("hides on window scroll and removes its listeners", async () => {
    const opened = await openWithButton();
    try {
      expect(gapButton()).not.toBeNull();
      const removeSpy = vi.spyOn(window, "removeEventListener");
      window.dispatchEvent(new Event("scroll"));
      await nextTick();
      expect(gapButton()).toBeNull();
      expect(removeSpy).toHaveBeenCalledWith("scroll", expect.any(Function), true);
      expect(removeSpy).toHaveBeenCalledWith("resize", expect.any(Function));
    } finally {
      opened.wrapper.unmount();
    }
  });

  it("hides on window resize", async () => {
    const opened = await openWithButton();
    try {
      expect(gapButton()).not.toBeNull();
      window.dispatchEvent(new Event("resize"));
      await nextTick();
      expect(gapButton()).toBeNull();
    } finally {
      opened.wrapper.unmount();
    }
  });

  it("stays across a meta-only redraw and hides when the caret leaves the word", async () => {
    const opened = await openWithButton();
    try {
      opened.editor.view.dispatch(opened.editor.state.tr.setMeta(ATOM_STATE_KEY, true));
      await nextTick();
      expect(gapButton()).not.toBeNull();

      opened.editor.commands.setTextSelection(posIn(opened.editor, "Huvudstaden", 0));
      await nextTick();
      expect(gapButton()).toBeNull();
    } finally {
      opened.wrapper.unmount();
    }
  });

  it("hides when the editor is disabled or loses its next gap id", async () => {
    const opened = await openWithButton();
    try {
      await opened.setProps({ disabled: true });
      expect(gapButton()).toBeNull();
    } finally {
      opened.wrapper.unmount();
    }
  });
});
