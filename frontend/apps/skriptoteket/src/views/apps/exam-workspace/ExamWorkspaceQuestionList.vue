<script setup lang="ts">
/**
 * Exam workspace question list column.
 *
 * Domain purpose:
 *   Frame the Redigera question list on desktop and tablet: a "Frågor (N)"
 *   heading, the "Ny fråga" action, and a scrolling body that holds the
 *   question table passed in the default slot.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceView` beside the item editor outside the
 *     phone layout, with `ExamWorkspaceItemTable` in its slot.
 */

import { IconPlus } from "../../../components/icons";

defineProps<{
  count: number;
  disabled: boolean;
}>();

const emit = defineEmits<{
  add: [];
}>();
</script>

<template>
  <section
    class="flex min-h-0 flex-col border-r border-navy/20"
    aria-labelledby="exam-workspace-questions-title"
    data-test="exam-workspace-question-list"
  >
    <header class="flex items-center justify-between gap-2 border-b border-navy/20 px-3 py-2">
      <h2
        id="exam-workspace-questions-title"
        class="text-sm font-semibold leading-tight text-navy"
      >
        Frågor <span class="font-normal text-navy/65">({{ count }})</span>
      </h2>
      <button
        type="button"
        class="inline-flex h-8 items-center gap-1 border border-navy/35 bg-panel px-2 text-xs font-semibold text-navy hover:bg-canvas disabled:opacity-50"
        :disabled="disabled"
        data-test="exam-workspace-add-item"
        @click="emit('add')"
      >
        <IconPlus
          :size="14"
          class="h-3.5 w-3.5"
        />
        Ny fråga
      </button>
    </header>
    <div class="min-h-0 flex-1 overflow-y-auto">
      <slot />
    </div>
  </section>
</template>
