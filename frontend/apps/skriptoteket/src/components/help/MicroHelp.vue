<script setup lang="ts">
/**
 * Accessible field-level micro-help disclosure.
 *
 * This component owns the small contextual help pattern used next to form
 * labels. Route-level help remains in `HelpPanel`, while field explanations can
 * reuse this non-modal disclosure without each view wiring document listeners.
 */
import { nextTick, onMounted, onUnmounted, ref } from "vue";

import { IconHelp, IconX } from "../icons";

const props = withDefaults(
  defineProps<{
    id: string;
    label?: string;
    title?: string;
  }>(),
  {
    label: "Visa hjälp",
    title: undefined,
  },
);

const isOpen = ref(false);
const rootRef = ref<HTMLElement | null>(null);
const triggerRef = ref<HTMLButtonElement | null>(null);

const panelId = `${props.id}-panel`;
const titleId = `${props.id}-title`;

async function close(restoreFocus = true): Promise<void> {
  if (!isOpen.value) {
    return;
  }
  isOpen.value = false;

  if (restoreFocus) {
    await nextTick();
    triggerRef.value?.focus({ preventScroll: true });
  }
}

function toggle(): void {
  isOpen.value = !isOpen.value;
}

function handleDocumentClick(event: MouseEvent): void {
  if (!isOpen.value) {
    return;
  }

  const target = event.target;
  if (target instanceof Node && rootRef.value?.contains(target)) {
    return;
  }

  void close(false);
}

function handleDocumentKeydown(event: KeyboardEvent): void {
  if (event.key === "Escape" && isOpen.value) {
    event.stopPropagation();
    void close();
  }
}

onMounted(() => {
  document.addEventListener("click", handleDocumentClick);
  document.addEventListener("keydown", handleDocumentKeydown);
});

onUnmounted(() => {
  document.removeEventListener("click", handleDocumentClick);
  document.removeEventListener("keydown", handleDocumentKeydown);
});
</script>

<template>
  <span
    ref="rootRef"
    class="micro-help"
  >
    <button
      ref="triggerRef"
      type="button"
      class="micro-help-trigger"
      :aria-label="props.label"
      :aria-expanded="isOpen"
      :aria-controls="panelId"
      @click.stop="toggle"
    >
      <IconHelp :size="16" />
    </button>

    <Transition name="micro-help-popover">
      <span
        v-if="isOpen"
        :id="panelId"
        class="micro-help-panel"
        role="dialog"
        aria-modal="false"
        :aria-labelledby="props.title ? titleId : undefined"
      >
        <button
          type="button"
          class="micro-help-close"
          aria-label="Stäng hjälp"
          @click="close()"
        >
          <IconX :size="14" />
        </button>

        <span
          v-if="props.title"
          :id="titleId"
          class="micro-help-title"
        >
          {{ props.title }}
        </span>
        <span class="micro-help-content">
          <slot />
        </span>
      </span>
    </Transition>
  </span>
</template>

<style scoped>
.micro-help {
  position: relative;
  display: inline-flex;
  align-items: center;
}

.micro-help-trigger {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: var(--huleedu-space-1);
  color: var(--huleedu-navy-60);
  border-radius: var(--huleedu-radius-sm);
  transition:
    color var(--huleedu-duration-default) var(--huleedu-ease-default),
    background-color var(--huleedu-duration-default) var(--huleedu-ease-default);
}

.micro-help-trigger:hover {
  color: var(--huleedu-action);
  background-color: var(--huleedu-action-10);
}

.micro-help-trigger:focus-visible,
.micro-help-close:focus-visible {
  outline: 2px solid var(--huleedu-action-40);
  outline-offset: 2px;
}

.micro-help-panel {
  position: absolute;
  top: calc(100% + var(--huleedu-space-2));
  left: 0;
  z-index: var(--huleedu-z-tooltip);
  display: block;
  width: max-content;
  max-width: min(20rem, calc(100vw - var(--huleedu-space-8)));
  padding: var(--huleedu-space-4);
  padding-right: var(--huleedu-space-10);
  background-color: var(--surface-modal);
  border: var(--huleedu-border-width) solid var(--huleedu-navy);
  box-shadow: var(--huleedu-shadow-brutal-sm);
  font-size: 0.875rem;
  line-height: 1.5;
  color: var(--huleedu-navy-80);
}

.micro-help-close {
  position: absolute;
  top: var(--huleedu-space-2);
  right: var(--huleedu-space-2);
  display: grid;
  place-items: center;
  width: var(--huleedu-space-6);
  height: var(--huleedu-space-6);
  padding: 0;
  border: var(--huleedu-border-width) solid transparent;
  border-radius: var(--huleedu-radius-sm);
  background: transparent;
  color: var(--huleedu-navy-60);
  cursor: pointer;
  transition:
    color var(--huleedu-duration-default) var(--huleedu-ease-default),
    border-color var(--huleedu-duration-default) var(--huleedu-ease-default);
}

.micro-help-close:hover {
  color: var(--huleedu-action);
  border-color: var(--huleedu-navy);
}

.micro-help-title {
  display: block;
  margin-bottom: var(--huleedu-space-2);
  font-weight: 600;
  color: var(--huleedu-navy);
}

.micro-help-content {
  display: block;
}

.micro-help-popover-enter-active,
.micro-help-popover-leave-active {
  transition:
    opacity 150ms var(--huleedu-ease-default),
    transform 150ms var(--huleedu-ease-default);
}

.micro-help-popover-enter-from,
.micro-help-popover-leave-to {
  opacity: 0;
  transform: translateY(calc(-1 * var(--huleedu-space-1)));
}
</style>
