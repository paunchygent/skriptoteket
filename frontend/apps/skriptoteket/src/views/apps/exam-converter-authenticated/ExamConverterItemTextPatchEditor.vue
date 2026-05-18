<script setup lang="ts">
/**
 * Exam Converter item text correction editor.
 *
 * Domain purpose:
 *   Collect teacher-owned visible item text patches for source-bound unified
 *   correction submission without mutating the source IR or artifact state.
 *
 * Relationships:
 *   - Rendered by `ExamConverterQuestionReviewShell`.
 *   - Emits bounded title/prompt patches consumed by
 *     `digiexamTeacherCorrectionOverlay`.
 *   - Complements point and manual answer-key correction editors.
 */

import { computed, ref, watch } from "vue";
import { CheckCheck } from "lucide-vue-next";

import type { ExamConverterQuestionReviewRow } from "./digiexamIrReviewParser";
import type { ExamConverterItemTextPatchCorrection } from "./digiexamTeacherCorrectionOverlay";

const props = defineProps<{
  disabled: boolean;
  question: ExamConverterQuestionReviewRow;
}>();

const emit = defineEmits<{
  applyItemTextPatch: [
    question: ExamConverterQuestionReviewRow,
    patch: ExamConverterItemTextPatchCorrection,
  ];
}>();

const selectedField = ref<ExamConverterItemTextPatchCorrection["field"]>("prompt_lines");
const textDraft = ref("");

const sourceValue = computed(() =>
  selectedField.value === "item_title" ? props.question.title : props.question.promptText,
);

const canApplyTextPatch = computed(() => {
  const value = textDraft.value.trim();
  return (
    props.question.sourceItemFingerprint !== null &&
    !props.disabled &&
    value.length > 0 &&
    value !== sourceValue.value.trim()
  );
});

function resetDraft(): void {
  selectedField.value = "prompt_lines";
  textDraft.value = props.question.promptText;
}

function applyItemTextPatch(): void {
  if (!canApplyTextPatch.value) return;
  emit("applyItemTextPatch", props.question, {
    field: selectedField.value,
    value: textDraft.value,
  });
}

watch(() => [props.question.itemId, props.question.promptText, props.question.title], resetDraft, {
  immediate: true,
});
watch(selectedField, () => {
  textDraft.value = sourceValue.value;
});
</script>

<template>
  <section
    class="mt-4 grid gap-3 border border-navy/20 bg-canvas p-3"
    data-test="exam-converter-item-text-patch-editor"
  >
    <div class="flex flex-wrap items-center gap-2">
      <label class="text-sm font-semibold leading-tight text-navy">
        Text
      </label>
      <select
        v-model="selectedField"
        class="min-h-9 border border-navy/35 bg-panel px-2 text-sm text-navy"
        data-test="exam-converter-item-text-patch-field"
        :disabled="disabled"
      >
        <option value="prompt_lines">
          Frågetext
        </option>
        <option value="item_title">
          Rubrik
        </option>
      </select>
    </div>
    <textarea
      v-model="textDraft"
      class="min-h-24 resize-y border border-navy/35 bg-panel px-3 py-2 text-sm leading-relaxed text-navy"
      data-test="exam-converter-item-text-patch-input"
      :disabled="disabled"
    />
    <button
      type="button"
      class="btn-ghost inline-flex w-fit items-center gap-2 shadow-none"
      :disabled="!canApplyTextPatch"
      data-test="exam-converter-apply-item-text-patch-action"
      @click="applyItemTextPatch"
    >
      <CheckCheck
        class="h-4 w-4"
        aria-hidden="true"
      />
      Skicka text
    </button>
  </section>
</template>
