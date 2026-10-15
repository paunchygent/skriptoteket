<script setup lang="ts">
/**
 * Exam workspace rich text entry.
 *
 * Domain purpose:
 *   Edit one choice option or one matching entry as rich text: every stored
 *   paragraph renders as its own editable line with the five kept marks, in
 *   the compact input surface a choice and a Kategorisera cell need. The
 *   entry never offers gaps or pictures of its own; if a stored body somehow
 *   carries one, it still renders as a fixed atom, so an edit can never drop
 *   it silently. Ctrl/Cmd+B, I and U toggle marks while the teacher edits.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceChoiceField` for each choice and by
 *     `ExamWorkspaceKategoriseraGrid` for every row and category.
 *   - Emits the whole entry body on any paragraph edit;
 *     `examWorkspaceItemEdits` applies it to the document.
 */

import type { NativeExamBodyParagraph, NativeExamBodySegment } from "../../../api/examWorkspace";
import ExamWorkspaceBodyParagraph from "./ExamWorkspaceBodyParagraph.vue";

const props = withDefaults(
  defineProps<{
    body: NativeExamBodyParagraph[];
    disabled?: boolean;
    label: string;
    testId: string;
    invalid?: boolean;
    describedBy?: string;
    /** The paragraph border colour, so an empty or correct entry can mark itself. */
    borderClass?: string;
  }>(),
  { disabled: false, invalid: false, describedBy: undefined, borderClass: "border-navy/35" },
);

const emit = defineEmits<{
  updateBody: [body: NativeExamBodyParagraph[]];
  focusEntry: [];
}>();

function handleSegments(paragraphIndex: number, segments: NativeExamBodySegment[]): void {
  emit(
    "updateBody",
    props.body.map((paragraph, index) =>
      index === paragraphIndex ? { ...paragraph, segments } : paragraph,
    ),
  );
}
</script>

<template>
  <div class="grid gap-1">
    <ExamWorkspaceBodyParagraph
      v-for="(paragraph, paragraphIndex) in body"
      :key="paragraphIndex"
      :paragraph="paragraph"
      :paragraph-index="paragraphIndex"
      :gaps="[]"
      :disabled="disabled"
      :border-class="borderClass"
      :interactive-gaps="false"
      :label="body.length > 1 ? `${label}, stycke ${paragraphIndex + 1}` : label"
      :test-id="body.length > 1 ? `${testId}-${paragraphIndex}` : testId"
      :aria-invalid="invalid ? 'true' : undefined"
      :aria-describedby="describedBy"
      variant="input"
      @update-segments="(segments) => handleSegments(paragraphIndex, segments)"
      @focus-paragraph="emit('focusEntry')"
    />
  </div>
</template>
