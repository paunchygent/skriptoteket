<script setup lang="ts">
/**
 * Exam workspace question tools: Import and the review check.
 *
 * Domain purpose:
 *   Import shows the question as the exam file had it (shown only when the
 *   question was imported); the check marks the question reviewed or takes
 *   that back. An instruction has Import only. The same tools sit in the
 *   question header on desktop and tablet and in the question strip on a
 *   phone.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceQuestionEditor` and `ExamWorkspacePhoneStrip`.
 */

import { UiGlyph } from "../../../components/ui";

defineProps<{
  hasImport: boolean;
  importOpen: boolean;
  /** Null for an instruction, which has no review state. */
  reviewed: boolean | null;
  disabled: boolean;
}>();

const emit = defineEmits<{ toggleImport: []; toggleReviewed: [] }>();
</script>

<template>
  <button
    v-if="hasImport"
    type="button"
    class="xw-btn tools__import"
    :class="{ 'xw-btn--pressed': importOpen }"
    :aria-expanded="importOpen"
    aria-label="Import"
    title="Visa frågan som den står i provfilen"
    data-test="exam-workspace-import-toggle"
    @click="emit('toggleImport')"
  >
    <UiGlyph
      meaning="document"
      :size="20"
    /><span class="tools__word">Import</span>
  </button>
  <button
    v-if="reviewed !== null"
    type="button"
    class="xw-btn xw-btn--icon"
    :class="{ 'xw-btn--checked': reviewed }"
    :disabled="disabled"
    :aria-pressed="reviewed"
    :aria-label="reviewed ? 'Ångra granskad' : 'Markera som granskad'"
    :title="reviewed ? 'Ångra granskad' : 'Markera som granskad'"
    data-test="exam-workspace-review"
    @click="emit('toggleReviewed')"
  >
    <UiGlyph
      meaning="confirm"
      :size="20"
    />
  </button>
</template>

<style scoped>
@media (max-width: 1279px) {
  .tools__word { display: none; }
  .tools__import { width: var(--xw-ctl-fine, 36px); padding: 0; }
}
@media (max-width: 1279px) and (pointer: coarse) {
  .tools__import { width: var(--xw-ctl, 44px); }
}
@media (max-width: 767px) {
  .tools__import { width: var(--xw-ctl, 44px); }
}
</style>
