/**
 * Exam workspace keyboard shortcuts.
 *
 * Domain purpose:
 *   Ctrl/Cmd+S saves (and never the browser's save page), Ctrl/Cmd+Z and
 *   Ctrl/Cmd+Shift+Z step through the autosave history outside text fields,
 *   ↑ and ↓ move between questions outside text fields, menus and dialogs,
 *   and Escape closes the phone list.
 *
 * Relationships:
 *   - Registers one window `keydown` listener for the lifetime of the
 *     component that calls it.
 *   - Acts through the callbacks `ExamWorkspaceView` passes from the save
 *     flow, the autosave history and the selection.
 */

import { onBeforeUnmount, onMounted } from "vue";
import type { Ref } from "vue";

export interface ExamWorkspaceKeyboardDeps {
  save: () => Promise<void>;
  undo: () => Promise<unknown> | unknown;
  redo: () => Promise<unknown> | unknown;
  step: (delta: -1 | 1) => void;
  listOpen: Ref<boolean>;
}

function isEditable(target: EventTarget | null): boolean {
  return (
    target instanceof HTMLElement &&
    (target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName))
  );
}

export function useExamWorkspaceKeyboard({ save, undo, redo, step, listOpen }: ExamWorkspaceKeyboardDeps): void {
  function handleKeydown(event: KeyboardEvent): void {
    const modifier = event.metaKey || event.ctrlKey;
    const key = event.key.toLowerCase();
    if (modifier && key === "s") {
      // The browser's save page never opens over the workspace.
      event.preventDefault();
      void save();
      return;
    }
    if (modifier && key === "z" && !isEditable(event.target)) {
      event.preventDefault();
      void (event.shiftKey ? redo() : undo());
      return;
    }
    if (event.key === "Escape" && listOpen.value) {
      listOpen.value = false;
      return;
    }
    if (
      (event.key === "ArrowDown" || event.key === "ArrowUp") &&
      !modifier &&
      !event.defaultPrevented &&
      !isEditable(event.target) &&
      !(event.target instanceof HTMLElement && event.target.closest('[role="menu"], [role="dialog"], select'))
    ) {
      event.preventDefault();
      step(event.key === "ArrowDown" ? 1 : -1);
    }
  }

  onMounted(() => {
    window.addEventListener("keydown", handleKeydown);
  });

  onBeforeUnmount(() => {
    window.removeEventListener("keydown", handleKeydown);
  });
}
