/**
 * Help-panel state and contextual topic resolution.
 *
 * This module owns the global help drawer refs that are shared across the SPA.
 * Route-level help is resolved here, while nested shells like Klassrumskartan
 * can temporarily override the route via `helpContext` without introducing a
 * second help surface.
 */
import { ref } from "vue";
import type { HelpTopicId } from "./helpTopicCatalog";

export { resolveHelpTopic, type HelpTopicId } from "./helpTopicCatalog";

const isOpen = ref(false);
const activeTopic = ref<HelpTopicId | null>(null);
const helpContext = ref<string | null>(null);

export function useHelp() {
  function open(): void {
    isOpen.value = true;
  }

  function close(): void {
    isOpen.value = false;
  }

  function toggle(): void {
    isOpen.value = !isOpen.value;
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
