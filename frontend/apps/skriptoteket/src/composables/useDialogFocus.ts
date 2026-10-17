/**
 * Shared dialog keyboard and focus handling.
 *
 * Domain purpose:
 *   Give overlays one keyboard contract. When `takesFocus`
 *   holds, at mount or later when the layout changes, focus moves into the
 *   panel. When the panel unmounts, focus returns to the element that had it
 *   before, or to `fallbackFocus` when nothing in the page had focus (a
 *   click that does not focus its button, or a focused element that is
 *   gone). Escape closes the panel: anywhere
 *   on the page for a modal panel, only from inside the panel otherwise.
 *   A modal panel keeps Tab and Shift+Tab cycling through its own controls.
 *
 *   A panel may mount with its component or appear later through v-if.
 *   Each open panel captures its own opener and returns focus when removed.
 *   `initialFocus` can select a control instead of the panel on entry.
 */

import { onBeforeUnmount, watch } from "vue";
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

export type DialogFocusOptions = {
  fallbackFocus?: () => HTMLElement | null;
  initialFocus?: () => HTMLElement | null;
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

export function useDialogFocus(
  panel: Ref<HTMLElement | null>,
  options: DialogFocusOptions,
): void {
  let opener: HTMLElement | null = null;
  let movedFocus = false;
  let boundPanel: HTMLElement | null = null;

  function handleKeydown(element: HTMLElement, event: KeyboardEvent): void {
    if (event.key === "Escape") {
      if (options.modal()) {
        // Cancelling a modal must not also cancel its underlying workspace.
        event.preventDefault();
        event.stopPropagation();
      }
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
    // This runs after rendering, so both the panel and its controls exist.
    (options.initialFocus?.() ?? panel.value)?.focus();
  }

  function releasePanel(): void {
    boundPanel?.removeEventListener("keydown", handlePanelKeydown);
    document.removeEventListener("keydown", handleDocumentKeydown);
    boundPanel = null;
    if (movedFocus) {
      const target = opener?.isConnected ? opener : (options.fallbackFocus?.() ?? null);
      target?.focus();
    }
    opener = null;
    movedFocus = false;
  }

  // Observe the actual panel, not just component mount: dialogs can stay
  // mounted while v-if removes and recreates their teleported content.
  // A layout change can also start the focus contract for an existing panel.
  watch(
    [panel, () => options.takesFocus()],
    ([element, takes]) => {
      if (element !== boundPanel) {
        releasePanel();
        boundPanel = element;
        element?.addEventListener("keydown", handlePanelKeydown);
        if (element) {
          document.addEventListener("keydown", handleDocumentKeydown);
        }
      }
      if (element && takes && !movedFocus) {
        takeFocus();
      }
    },
    { flush: "post" },
  );

  onBeforeUnmount(releasePanel);
}
