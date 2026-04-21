/**
 * Help-panel state and contextual topic resolution.
 *
 * This module owns the global help drawer refs that are shared across the SPA.
 * Route-level help is resolved here, while nested shells like Klassrumskartan
 * can temporarily override the route via `helpContext` without introducing a
 * second help surface.
 */
import { nextTick, ref } from "vue";
import type { HelpTopicId } from "./helpTopicCatalog";

export { resolveHelpTopic, type HelpTopicId } from "./helpTopicCatalog";

const isOpen = ref(false);
const activeTopic = ref<HelpTopicId | null>(null);
const helpContext = ref<string | null>(null);
const openerElement = ref<HTMLElement | null>(null);
let focusRestoreGeneration = 0;

type CloseHelpOptions = {
  restoreFocus?: boolean;
};

function rememberOpener(opener?: HTMLElement | null): void {
  focusRestoreGeneration += 1;

  if (opener) {
    openerElement.value = opener;
    return;
  }

  if (typeof document !== "undefined" && document.activeElement instanceof HTMLElement) {
    openerElement.value = document.activeElement;
  }
}

async function restoreOpenerFocus(generation: number): Promise<void> {
  const opener = openerElement.value;
  openerElement.value = null;

  await nextTick();

  if (
    generation === focusRestoreGeneration &&
    opener &&
    typeof document !== "undefined" &&
    document.contains(opener)
  ) {
    opener.focus({ preventScroll: true });
  }
}

export function useHelp() {
  function open(opener?: HTMLElement | null): void {
    rememberOpener(opener);
    isOpen.value = true;
  }

  function close(options: CloseHelpOptions = {}): void {
    const restoreGeneration = focusRestoreGeneration + 1;
    focusRestoreGeneration = restoreGeneration;
    isOpen.value = false;
    if (options.restoreFocus ?? true) {
      void restoreOpenerFocus(restoreGeneration);
    } else {
      openerElement.value = null;
    }
  }

  function toggle(opener?: HTMLElement | null): void {
    if (isOpen.value) {
      close();
      return;
    }
    open(opener);
  }

  function showIndex(): void {
    activeTopic.value = null;
  }

  function showTopic(topic: HelpTopicId): void {
    activeTopic.value = topic;
  }

  function setHelpContext(ctx: string | null): void {
    helpContext.value = ctx;
  }

  function clearHelpContext(expectedContext?: string | null): void {
    if (expectedContext && helpContext.value !== expectedContext) {
      return;
    }
    helpContext.value = null;
  }

  return {
    isOpen,
    activeTopic,
    helpContext,
    open,
    close,
    toggle,
    showIndex,
    showTopic,
    setHelpContext,
    clearHelpContext,
  };
}
