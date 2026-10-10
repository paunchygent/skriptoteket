<script setup lang="ts">
/**
 * Phone bottom sheet for the exam workspace question list.
 *
 * Domain purpose:
 *   Show every question over the phone editor without leaving it (ST-29
 *   sheet pattern). The sheet is a modal dialog: focus moves into it on
 *   open, Tab stays inside it, the backdrop, the close button, and Escape
 *   close it, and focus returns to the element that opened it.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceView` only in the phone layout, holding the
 *     question list behind the "Fråga N av M" picker.
 *   - Keyboard and focus handling comes from `useExamWorkspaceDialogFocus`.
 */

import { ref } from "vue";

import { IconX } from "../../../components/icons";
import { useExamWorkspaceDialogFocus } from "./useExamWorkspaceDialogFocus";

defineProps<{
  title: string;
}>();

const emit = defineEmits<{
  close: [];
}>();

const panel = ref<HTMLElement | null>(null);

useExamWorkspaceDialogFocus(panel, {
  modal: () => true,
  onClose: () => emit("close"),
  takesFocus: () => true,
});
</script>

<template>
  <div
    class="fixed inset-0 z-50 flex flex-col justify-end"
    data-test="exam-workspace-sheet"
  >
    <button
      type="button"
      class="absolute inset-0 bg-navy/40"
      aria-label="Stäng"
      tabindex="-1"
      @click="emit('close')"
    />
    <section
      ref="panel"
      class="relative grid max-h-[85dvh] grid-rows-[auto_minmax(0,1fr)] border-t border-navy bg-panel text-navy outline-none"
      role="dialog"
      aria-modal="true"
      :aria-label="title"
      tabindex="-1"
    >
      <header class="flex items-center justify-between gap-3 border-b border-navy/20 px-4 py-3">
        <h2 class="text-sm font-semibold leading-tight">
          {{ title }}
        </h2>
        <button
          type="button"
          class="inline-flex h-10 w-10 items-center justify-center border border-navy/35 bg-panel"
          aria-label="Stäng"
          data-test="exam-workspace-sheet-close"
          @click="emit('close')"
        >
          <IconX
            :size="18"
            class="h-[1.125rem] w-[1.125rem]"
          />
        </button>
      </header>
      <div class="min-h-0 overflow-y-auto">
        <slot />
      </div>
    </section>
  </div>
</template>
