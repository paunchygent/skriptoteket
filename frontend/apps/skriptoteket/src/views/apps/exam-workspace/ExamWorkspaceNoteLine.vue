<script setup lang="ts">
/**
 * Exam workspace footer note line.
 *
 * Domain purpose:
 *   One neutral footer line: the line's text, then one glyph-only icon
 *   button per action. Each action names itself only in tooltip and
 *   aria-label; a button carries no visible text. The line knows nothing
 *   about totals: the parent maps its line kinds to actions.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceQuestionList`; the per-kind `data-test`
 *     arrives as a fallthrough attribute on the line.
 */

import { UiGlyph } from "../../../components/ui";
import type { UiGlyphMeaning } from "../../../components/ui";

/** One glyph-only button: `label` is both the tooltip and the aria-label. */
export type ExamWorkspaceNoteLineAction = {
  key: string;
  meaning: UiGlyphMeaning;
  label: string;
  dataTest: string;
};

defineProps<{
  text: string;
  actions: ExamWorkspaceNoteLineAction[];
  /** The workspace is busy: every button waits like the list's other actions. */
  disabled: boolean;
}>();

defineEmits<{
  action: [key: string];
}>();
</script>

<template>
  <div
    class="note-line"
    role="group"
    :aria-label="text"
  >
    <span class="note-line__text">{{ text }}</span>
    <button
      v-for="item in actions"
      :key="item.key"
      type="button"
      class="note-line__button"
      :disabled="disabled"
      :title="item.label"
      :aria-label="item.label"
      :data-test="item.dataTest"
      @click="$emit('action', item.key)"
    >
      <UiGlyph
        :meaning="item.meaning"
        :size="16"
      />
    </button>
  </div>
</template>

<style scoped>
.note-line { display: flex; align-items: center; gap: var(--huleedu-space-1-5); }
.note-line__text { flex: 1; min-width: 0; overflow-wrap: anywhere; }
.note-line__button {
  flex: none; display: inline-flex; align-items: center; justify-content: center;
  width: 28px; height: 28px; padding: 0; border: 0; border-radius: 50%;
  background: transparent; color: var(--huleedu-navy); cursor: pointer;
}
.note-line__button:disabled { cursor: not-allowed; opacity: 0.5; }
.note-line__button:focus-visible {
  outline: 2px solid var(--huleedu-action-40); outline-offset: 2px;
}
@media (hover: hover) {
  .note-line__button:not(:disabled):hover {
    background: var(--huleedu-action-05);
  }
}
</style>
