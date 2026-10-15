<script setup lang="ts">
/**
 * Phone question bar for the exam workspace.
 *
 * Domain purpose:
 *   Let the teacher move between questions on a phone without a list on
 *   screen: previous and next buttons around a "Fråga N av M" picker that
 *   opens the question sheet. A warning glyph on the picker says that some
 *   question would stop an export or a save, and an AI glyph states that the
 *   current question's key was interpreted or invented by the AI.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceView` in the phone toolbar in Redigera; the
 *     view owns the selection and the `ExamWorkspaceSheet` it opens.
 */

import { ChevronDown } from "lucide-vue-next";

import { IconAi, IconNextPage, IconPreviousPage, IconWarning } from "../../../components/icons";

defineProps<{
  aiKeyLabel: string | null;
  needsAttention: boolean;
  position: number;
  sheetOpen: boolean;
  total: number;
}>();

const emit = defineEmits<{
  next: [];
  openQuestions: [];
  previous: [];
}>();
</script>

<template>
  <div
    class="grid grid-cols-[auto_minmax(0,1fr)_auto] items-stretch"
    data-test="exam-workspace-phone-question-bar"
  >
    <button
      type="button"
      class="inline-flex h-11 w-11 items-center justify-center border border-navy/35 bg-panel disabled:opacity-40"
      aria-label="Föregående fråga"
      :disabled="position <= 1"
      data-test="exam-workspace-phone-previous"
      @click="emit('previous')"
    >
      <IconPreviousPage :size="20" />
    </button>
    <button
      type="button"
      class="-mx-px inline-flex h-11 min-w-0 items-center justify-center gap-2 border border-navy/35 bg-panel px-3 text-sm font-semibold text-navy"
      aria-haspopup="dialog"
      :aria-expanded="sheetOpen ? 'true' : 'false'"
      data-test="exam-workspace-question-picker"
      @click="emit('openQuestions')"
    >
      <span class="truncate">Fråga {{ position }} av {{ total }}</span>
      <span
        class="inline-flex h-4 w-4 shrink-0 items-center justify-center"
        data-test="exam-workspace-phone-ai-slot"
      >
        <span
          v-if="aiKeyLabel"
          role="img"
          :aria-label="aiKeyLabel"
          :title="aiKeyLabel"
          data-test="exam-workspace-phone-ai-key"
        >
          <IconAi
            :size="16"
            class="h-4 w-4 text-navy"
            aria-hidden="true"
          />
        </span>
      </span>
      <IconWarning
        v-if="needsAttention"
        :size="16"
        class="h-4 w-4 shrink-0 text-warning"
        aria-hidden="true"
      />
      <ChevronDown
        class="h-4 w-4 shrink-0"
        aria-hidden="true"
      />
    </button>
    <button
      type="button"
      class="inline-flex h-11 w-11 items-center justify-center border border-navy/35 bg-panel disabled:opacity-40"
      aria-label="Nästa fråga"
      :disabled="position >= total"
      data-test="exam-workspace-phone-next"
      @click="emit('next')"
    >
      <IconNextPage :size="20" />
    </button>
  </div>
</template>
