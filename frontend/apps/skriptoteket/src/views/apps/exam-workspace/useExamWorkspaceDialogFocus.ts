/**
 * Exam workspace dialog keyboard and focus handling.
 *
 * Domain purpose:
 *   Give the workspace's overlays one keyboard contract. When `takesFocus`
 *   holds at mount, focus moves into the panel and returns to the element
 *   that had it when the panel unmounts. Escape closes the panel: anywhere
 *   on the page for a modal panel, only from inside the panel otherwise.
 *   A modal panel keeps Tab and Shift+Tab cycling through its own controls.
 *
 * Relationships:
 *   - Used by `ExamWorkspaceSheet` (modal) and `ExamWorkspaceItemDrawer`
 *     (modal on phone, focus and Escape on tablet, inert on desktop).
 */

import { nextTick, onBeforeUnmount, onMounted } from "vue";
import type { Ref } from "vue";

const FOCUSABLE_SELECTOR = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  '[contenteditable="true"]',
  '[tabindex]:not([tabindex="-1"])',
].join(",");

export type ExamWorkspaceDialogFocusOptions = {
  modal: () => boolean;
  onClose: () => void;
  takesFocus: () => boolean;
};

function containFocus(panel: HTMLElement, event: KeyboardEvent): void {
  const focusables = Array.from(panel.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR));
  const first = focusables[0];
  const last = focusables[focusables.length - 1];
  if (!first || !last) {
    event.preventDefault();
    panel.focus();
    return;
  }
  const active = document.activeElement;
  const outside = !(active instanceof Node) || !panel.contains(active);
  if (event.shiftKey && (outside || active === first || active === panel)) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && (outside || active === last)) {
    event.preventDefault();
    first.focus();
  }
}

export function useExamWorkspaceDialogFocus(
  panel: Ref<HTMLElement | null>,
  options: ExamWorkspaceDialogFocusOptions,
): void {
  let opener: HTMLElement | null = null;
  let movedFocus = false;

  function handleKeydown(element: HTMLElement, event: KeyboardEvent): void {
    if (event.key === "Escape") {
      options.onClose();
    } else if (event.key === "Tab" && options.modal()) {
      containFocus(element, event);
    }
  }

  // Keys pressed inside the panel reach it directly; a modal panel also
  // answers keys pressed while focus is somewhere else on the page.
  function handlePanelKeydown(event: KeyboardEvent): void {
    if (panel.value) {
      handleKeydown(panel.value, event);
    }
  }

  function handleDocumentKeydown(event: KeyboardEvent): void {
    const element = panel.value;
    const fromInside = event.target instanceof Node && element?.contains(event.target);
    if (element && !fromInside && options.modal()) {
      handleKeydown(element, event);
    }
  }

  onMounted(() => {
    panel.value?.addEventListener("keydown", handlePanelKeydown);
    document.addEventListener("keydown", handleDocumentKeydown);
    if (options.takesFocus()) {
      opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
      movedFocus = true;
      void nextTick(() => panel.value?.focus());
    }
  });

  onBeforeUnmount(() => {
    panel.value?.removeEventListener("keydown", handlePanelKeydown);
    document.removeEventListener("keydown", handleDocumentKeydown);
    if (movedFocus) {
      opener?.focus();
    }
  });
}
