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
import { Check } from "lucide-vue-next";

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

const promptDraft = ref("");
const titleDraft = ref("");

const canApplyPromptPatch = computed(() => {
  const value = promptDraft.value.trim();
  return (
    props.question.sourceItemFingerprint !== null &&
    !props.disabled &&
    value.length > 0 &&
    value !== props.question.promptText.trim()
  );
});

const canApplyTitlePatch = computed(() => {
  const value = titleDraft.value.trim();
  return (
    props.question.sourceItemFingerprint !== null &&
    !props.disabled &&
    value.length > 0 &&
    value !== props.question.title.trim()
  );
});

function resetDraft(): void {
  promptDraft.value = props.question.promptText;
  titleDraft.value = props.question.title;
}

function applyPromptPatch(): void {
  if (!canApplyPromptPatch.value) return;
  emit("applyItemTextPatch", props.question, {
    field: "prompt_lines",
    value: promptDraft.value,
  });
}

function applyTitlePatch(): void {
  if (!canApplyTitlePatch.value) return;
  emit("applyItemTextPatch", props.question, {
    field: "item_title",
    value: titleDraft.value,
  });
}

watch(() => [props.question.itemId, props.question.promptText, props.question.title], resetDraft, {
  immediate: true,
});
</script>

<template>
  <section
    class="mt-5 grid gap-4"
    data-test="exam-converter-item-text-patch-editor"
  >
    <div class="grid gap-2">
      <label
        class="text-sm font-semibold leading-tight text-navy"
        for="exam-converter-item-title-patch-input"
      >
        Rubrik
      </label>
      <input
        id="exam-converter-item-title-patch-input"
        v-model="titleDraft"
        class="min-h-10 border border-navy/35 bg-panel px-3 text-sm text-navy"
        data-test="exam-converter-item-title-patch-input"
        :disabled="disabled"
        type="text"
      >
      <button
        type="button"
        class="btn-ghost inline-flex w-fit items-center gap-2 shadow-none"
        :disabled="!canApplyTitlePatch"
        data-test="exam-converter-apply-item-title-patch-action"
        @click="applyTitlePatch"
      >
        <Check
          class="h-4 w-4"
          aria-hidden="true"
        />
        Spara rubrik
      </button>
    </div>
    <div class="grid gap-2">
      <label
        class="text-sm font-semibold leading-tight text-navy"
        for="exam-converter-item-text-patch-input"
      >
        Frågetext
      </label>
      <textarea
        id="exam-converter-item-text-patch-input"
        v-model="promptDraft"
        class="min-h-24 resize-y border border-navy/35 bg-panel px-3 py-2 text-sm leading-relaxed text-navy"
        data-test="exam-converter-item-text-patch-input"
        :disabled="disabled"
      />
      <button
        type="button"
        class="btn-ghost inline-flex w-fit items-center gap-2 shadow-none"
        :disabled="!canApplyPromptPatch"
        data-test="exam-converter-apply-item-text-patch-action"
        @click="applyPromptPatch"
      >
        <Check
          class="h-4 w-4"
          aria-hidden="true"
        />
        Spara frågetext
      </button>
    </div>
  </section>
</template>
