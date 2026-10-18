<script setup lang="ts">
/**
 * Exam workspace choice field.
 *
 * Domain purpose:
 *   Edit a single-choice or multiple-response item's options as rich text:
 *   each option is one editable entry that shows and toggles the kept marks,
 *   next to the radio or checkbox that declares the correct answer. An
 *   option whose body carries no text still saves; the field marks it with
 *   the Swedish hint the export blocker uses. While `disabled` is set, every
 *   control is disabled.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceQuestionEditor` for choice kinds.
 *   - Emits typed update events; `useExamWorkspaceDocument` owns the state.
 *   - Reads the empty-body rule from `examWorkspaceItemSaveRules`.
 */

import { useId } from "vue";

import type { NativeExamBodyParagraph, NativeExamItem } from "../../../api/examWorkspace";
import ExamWorkspaceRichTextEntry from "./ExamWorkspaceRichTextEntry.vue";
import { EMPTY_CHOICE_TEXT_GUIDANCE, hasEmptyChoiceText } from "./examWorkspaceItemSaveRules";
import { isEmptyBody } from "./examWorkspaceRichText";

const props = defineProps<{
  disabled?: boolean;
  item: NativeExamItem;
}>();

const emit = defineEmits<{
  updateBody: [choiceId: string, body: NativeExamBodyParagraph[]];
  updateCorrectChoices: [correctChoiceIds: string[]];
}>();

const choiceHintId = useId();

function isCorrectChoice(choiceId: string): boolean {
  return props.item.answer_key.correct_choice_ids.includes(choiceId);
}

function choiceBorderClass(choiceId: string, body: NativeExamBodyParagraph[]): string {
  if (isEmptyBody(body)) {
    return "border-warning";
  }
  return isCorrectChoice(choiceId)
    ? "border-success shadow-[inset_4px_0_0_var(--color-success)]"
    : "border-navy/35";
}

function handleSingleCorrectChoice(choiceId: string): void {
  emit("updateCorrectChoices", [choiceId]);
}

function handleMultipleCorrectChoice(choiceId: string, event: Event): void {
  const input = event.target as HTMLInputElement;
  const selected = new Set(props.item.answer_key.correct_choice_ids);
  if (input.checked) {
    selected.add(choiceId);
  } else {
    selected.delete(choiceId);
  }
  const orderedChoiceIds = props.item.choices
    .map((choice) => choice.choice_id)
    .filter((candidateChoiceId) => selected.has(candidateChoiceId));
  emit("updateCorrectChoices", orderedChoiceIds);
}

function choiceLetter(index: number): string {
  return String.fromCharCode(65 + index);
}
</script>

<template>
  <fieldset
    v-if="item.kind === 'single_choice' || item.kind === 'multiple_response'"
    class="grid gap-2"
  >
    <legend class="mb-2 text-xs font-semibold text-navy/80">
      Svarsalternativ – markera {{ item.kind === 'single_choice' ? 'det rätta svaret' : 'alla rätta svar' }}
    </legend>
    <div
      v-for="(choice, choiceIndex) in item.choices"
      :key="choice.choice_id"
      class="grid grid-cols-[auto_auto_minmax(0,1fr)] items-start gap-2"
    >
      <input
        v-if="item.kind === 'single_choice'"
        type="radio"
        class="mt-2 h-5 w-5"
        :name="`exam-workspace-correct-${item.item_id}`"
        :checked="isCorrectChoice(choice.choice_id)"
        :disabled="disabled"
        :aria-label="`Rätt svar: alternativ ${choiceLetter(choiceIndex)}`"
        :data-test="`exam-workspace-choice-correct-${choice.choice_id}`"
        @change="handleSingleCorrectChoice(choice.choice_id)"
      >
      <input
        v-else
        type="checkbox"
        class="mt-2 h-5 w-5"
        :checked="isCorrectChoice(choice.choice_id)"
        :disabled="disabled"
        :aria-label="`Rätt svar: alternativ ${choiceLetter(choiceIndex)}`"
        :data-test="`exam-workspace-choice-correct-${choice.choice_id}`"
        @change="handleMultipleCorrectChoice(choice.choice_id, $event)"
      >
      <span
        class="mt-2 w-5 text-center text-sm font-semibold text-navy/70"
        aria-hidden="true"
      >{{ choiceLetter(choiceIndex) }}</span>
      <ExamWorkspaceRichTextEntry
        :key="`${item.item_id}-${choice.choice_id}`"
        :body="choice.body"
        :border-class="choiceBorderClass(choice.choice_id, choice.body)"
        :described-by="isEmptyBody(choice.body) ? choiceHintId : undefined"
        :disabled="disabled"
        :invalid="isEmptyBody(choice.body)"
        :label="`Text för svarsalternativ ${choiceLetter(choiceIndex)}`"
        :test-id="`exam-workspace-choice-text-${choice.choice_id}`"
        @update-body="(body) => emit('updateBody', choice.choice_id, body)"
      />
    </div>
    <p
      v-if="hasEmptyChoiceText(item)"
      :id="choiceHintId"
      class="border-l-4 border-warning pl-2 text-sm leading-snug text-navy"
      data-test="exam-workspace-choice-text-hint"
    >
      {{ EMPTY_CHOICE_TEXT_GUIDANCE }}
    </p>
  </fieldset>
</template>
