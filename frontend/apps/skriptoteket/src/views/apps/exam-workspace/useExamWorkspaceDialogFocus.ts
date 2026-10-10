/**
 * Exam workspace dialog keyboard and focus handling.
 *
 * Domain purpose:
 *   Give the workspace's overlays one keyboard contract. When `takesFocus`
 *   holds, at mount or later when the layout changes, focus moves into the
 *   panel. When the panel unmounts, focus returns to the element that had it
 *   before, or to `fallbackFocus` when nothing in the page had focus (a
 *   click that does not focus its button, or a focused element that is
 *   gone). Escape closes the panel: anywhere
 *   on the page for a modal panel, only from inside the panel otherwise.
 *   A modal panel keeps Tab and Shift+Tab cycling through its own controls.
 *
 * Relationships:
 *   - Used by `ExamWorkspaceSheet` (modal) and `ExamWorkspaceItemDrawer`
 *     (modal on phone, focus and Escape on tablet, inert on desktop).
 */

import { nextTick, onBeforeUnmount, onMounted, watch } from "vue";
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
  fallbackFocus?: () => HTMLElement | null;
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

  function takeFocus(): void {
    const active = document.activeElement;
    const usable =
      active instanceof HTMLElement && active !== document.body && !panel.value?.contains(active);
    opener = usable ? active : null;
    movedFocus = true;
    void nextTick(() => panel.value?.focus());
  }

  onMounted(() => {
    panel.value?.addEventListener("keydown", handlePanelKeydown);
    document.addEventListener("keydown", handleDocumentKeydown);
    if (options.takesFocus()) {
      takeFocus();
    }
  });

  // A layout change while the panel is open can start the focus contract.
  watch(
    () => options.takesFocus(),
    (takes) => {
      if (takes && !movedFocus) {
        takeFocus();
      }
    },
    { flush: "post" },
  );

  onBeforeUnmount(() => {
    panel.value?.removeEventListener("keydown", handlePanelKeydown);
    document.removeEventListener("keydown", handleDocumentKeydown);
    if (movedFocus) {
      const target = opener?.isConnected ? opener : (options.fallbackFocus?.() ?? null);
      target?.focus();
    }
  });
}
