/**
 * The keymap reads the platform once, when ProseMirror's keymap module loads,
 * so the Cmd shortcuts need a spec file of their own that reports a Mac before
 * any import runs. `ExamWorkspaceRichTextEditor.spec.ts` covers the Ctrl keys.
 */
import { mount } from "@vue/test-utils";
import type { Editor } from "@tiptap/core";
import { afterEach, describe, expect, it, vi } from "vitest";
import { defineComponent, h, nextTick } from "vue";

import { provideExamWorkspaceHistoryKeys } from "./examWorkspaceHistoryKeys";
import ExamWorkspaceRichTextEditor from "./ExamWorkspaceRichTextEditor.vue";

vi.hoisted(() => {
  Object.defineProperty(window.navigator, "platform", { value: "MacIntel", configurable: true });
});

describe("ExamWorkspaceRichTextEditor on a Mac", () => {
  afterEach(() => {
    document.body.innerHTML = "";
  });

  it.each([
    ["Cmd+Z", "z", { metaKey: true }, "undo"],
    ["Cmd+Shift+Z", "Z", { metaKey: true, shiftKey: true }, "redo"],
    ["Ctrl+Z", "z", { ctrlKey: true }, null],
  ] as const)("%s calls the workspace history only for the Cmd shortcuts", async (_name, key, modifiers, call) => {
    const keys = { undo: vi.fn(), redo: vi.fn() };
    const Host = defineComponent({
      setup() {
        provideExamWorkspaceHistoryKeys(keys);
        return () =>
          h(ExamWorkspaceRichTextEditor, {
            body: [{ heading_level: null, segments: [{ kind: "text", text: "keep", marks: [] }] }],
            label: "Frågetext",
            testId: "mac-editor",
          });
      },
    });
    const wrapper = mount(Host, { attachTo: document.body });
    await nextTick();
    await nextTick();
    const surface = wrapper.get("[data-test='mac-editor']").element as HTMLElement & { editor?: Editor };
    const event = new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true, ...modifiers });
    surface.dispatchEvent(event);
    if (call === null) {
      expect(keys.undo).not.toHaveBeenCalled();
      expect(keys.redo).not.toHaveBeenCalled();
    } else {
      expect(event.defaultPrevented).toBe(true);
      expect(keys[call]).toHaveBeenCalledTimes(1);
    }
    expect(surface.editor?.getText()).toBe("keep");
    wrapper.unmount();
  });
});
