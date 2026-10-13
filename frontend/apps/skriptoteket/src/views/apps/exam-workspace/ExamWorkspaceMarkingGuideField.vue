<script setup lang="ts">
/**
 * Exam workspace marking-guide field.
 *
 * Domain purpose:
 *   Let the teacher read and edit the rättningsmall (marking guide) of a
 *   free-text question as a multi-line text. The guide is printed in the
 *   answer-key exports and is never sent to students. An emptied field is
 *   saved as no guide.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceItemEditor` for free-text items only.
 *   - Emits the typed text; `useExamWorkspaceDocument` owns the state
 *     (`updateItemMarkingGuide`), which stores `marking_guide` on the item.
 */

defineProps<{
  disabled?: boolean;
  guide: string | null;
}>();

const emit = defineEmits<{
  update: [guide: string | null];
}>();

function handleInput(event: Event): void {
  const textarea = event.target as HTMLTextAreaElement;
  emit("update", textarea.value.trim().length > 0 ? textarea.value : null);
}
</script>

<template>
  <label class="grid gap-1 text-xs font-semibold text-navy/80">
    Rättningsmall
    <textarea
      class="min-h-24 w-full border border-navy/35 bg-panel px-3 py-2 text-sm font-normal leading-snug text-navy"
      rows="4"
      :value="guide ?? ''"
      :disabled="disabled"
      data-test="exam-workspace-marking-guide-input"
      @input="handleInput"
    />
  </label>
</template>
