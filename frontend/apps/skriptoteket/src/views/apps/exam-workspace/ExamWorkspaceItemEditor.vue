<script setup lang="ts">
/**
 * Exam workspace item detail editor.
 *
 * Domain purpose:
 *   Edit one native exam item: title, prompt text, points, and answer-key
 *   values, plus the mark-as-reviewed action for items that need review.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceView` for the selected table row.
 *   - Emits typed update events; `useExamWorkspaceDocument` owns the state.
 */

import { computed } from "vue";

import { IconCheck, IconWarning } from "../../../components/icons";

import type { NativeExamItem } from "../../../api/examWorkspace";
import { examWorkspaceReviewReasonLabel, examWorkspaceTypeLabel } from "./examWorkspaceRows";
import {
  isPartiallyKeyedGapItem,
  PARTIAL_GAP_KEY_GUIDANCE,
} from "./examWorkspaceAnswerKeyRules";

const props = defineProps<{
  item: NativeExamItem;
}>();

const hasPartialGapKey = computed(() => isPartiallyKeyedGapItem(props.item));

const emit = defineEmits<{
  markReviewed: [itemId: string];
  updateBodyText: [itemId: string, paragraphIndex: number, segmentIndex: number, text: string];
  updateChoiceText: [itemId: string, choiceId: string, text: string];
  updateCorrectChoices: [itemId: string, correctChoiceIds: string[]];
  updateGapValues: [itemId: string, gapId: string, acceptedValues: string[]];
  updatePoints: [itemId: string, points: number | null];
  updateTitle: [itemId: string, title: string];
}>();

function handleTitleInput(event: Event): void {
  const input = event.target as HTMLInputElement;
  emit("updateTitle", props.item.item_id, input.value);
}

function handlePointsInput(event: Event): void {
  const input = event.target as HTMLInputElement;
  const raw = input.value.trim().replace(",", ".");
  if (raw.length === 0) {
    emit("updatePoints", props.item.item_id, null);
    return;
  }
  const parsed = Number(raw);
  emit("updatePoints", props.item.item_id, Number.isFinite(parsed) ? parsed : null);
}

function handleBodyTextInput(
  paragraphIndex: number,
  segmentIndex: number,
  event: Event,
): void {
  const input = event.target as HTMLTextAreaElement;
  emit("updateBodyText", props.item.item_id, paragraphIndex, segmentIndex, input.value);
}

function handleGapValuesChange(gapId: string, event: Event): void {
  const input = event.target as HTMLInputElement;
  const acceptedValues = input.value
    .split(",")
    .map((value) => value.trim())
    .filter((value) => value.length > 0);
  emit("updateGapValues", props.item.item_id, gapId, acceptedValues);
}

function handleChoiceTextInput(choiceId: string, event: Event): void {
  const input = event.target as HTMLInputElement;
  emit("updateChoiceText", props.item.item_id, choiceId, input.value);
}

function isCorrectChoice(choiceId: string): boolean {
  return props.item.answer_key.correct_choice_ids.includes(choiceId);
}

function handleSingleCorrectChoice(choiceId: string): void {
  emit("updateCorrectChoices", props.item.item_id, [choiceId]);
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
  emit("updateCorrectChoices", props.item.item_id, orderedChoiceIds);
}
</script>

<template>
  <section
    class="grid gap-4 border border-navy/20 bg-canvas p-3"
    :aria-label="`Redigera fråga ${item.sequence}`"
    data-test="exam-workspace-item-editor"
  >
    <header class="flex flex-wrap items-center justify-between gap-3">
      <h3 class="text-sm font-semibold leading-tight text-navy">
        Fråga {{ item.sequence }}
        <span class="font-normal text-navy/65">– {{ examWorkspaceTypeLabel(item.kind) }}</span>
      </h3>
      <div
        class="flex flex-wrap items-center gap-3"
        data-test="exam-workspace-review-badge"
      >
        <span
          v-if="item.review.state === 'review_required'"
          class="inline-flex items-center gap-2 text-xs font-semibold leading-tight text-navy"
        >
          <IconWarning
            :size="18"
            class="h-[1.125rem] w-[1.125rem] shrink-0 text-warning"
            aria-hidden="true"
          />
          Behöver granskas
        </span>
        <span
          v-else
          class="inline-flex items-center gap-2 text-xs font-semibold leading-tight text-navy"
        >
          <IconCheck
            :size="18"
            class="h-[1.125rem] w-[1.125rem] shrink-0 text-success"
            aria-hidden="true"
          />
          Granskad
        </span>
        <button
          v-if="item.review.state === 'review_required'"
          type="button"
          class="btn-ghost shadow-none"
          data-test="exam-workspace-mark-reviewed"
          @click="emit('markReviewed', item.item_id)"
        >
          Markera som granskad
        </button>
      </div>
    </header>

    <ul
      v-if="item.review.state === 'review_required' && item.review.reasons.length > 0"
      class="list-disc pl-5 text-xs leading-snug text-navy/70"
      data-test="exam-workspace-review-reasons"
    >
      <li
        v-for="reason in item.review.reasons"
        :key="reason"
      >
        {{ examWorkspaceReviewReasonLabel(reason) }}
      </li>
    </ul>

    <div class="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto] md:items-end">
      <label class="grid gap-1 text-xs font-semibold text-navy/80">
        Rubrik
        <input
          class="min-h-10 w-full border border-navy/35 bg-panel px-3 text-sm font-normal text-navy"
          type="text"
          :value="item.title ?? ''"
          data-test="exam-workspace-item-title-input"
          @input="handleTitleInput"
        >
      </label>
      <label class="grid gap-1 text-xs font-semibold text-navy/80">
        Poäng
        <input
          class="min-h-10 w-28 border border-navy/35 bg-panel px-3 text-sm font-normal text-navy"
          type="number"
          min="0"
          step="any"
          inputmode="decimal"
          :value="item.points ?? ''"
          data-test="exam-workspace-item-points-input"
          @input="handlePointsInput"
        >
      </label>
    </div>

    <fieldset class="grid gap-2 border border-navy/20 bg-panel p-3">
      <legend class="px-1 text-xs font-semibold text-navy/80">
        Frågetext
      </legend>
      <div
        v-for="(paragraph, paragraphIndex) in item.body"
        :key="paragraphIndex"
        class="flex flex-wrap items-start gap-2"
      >
        <template
          v-for="(segment, segmentIndex) in paragraph.segments"
          :key="segmentIndex"
        >
          <textarea
            v-if="segment.kind === 'text'"
            class="min-h-20 min-w-[12rem] flex-1 border border-navy/35 bg-panel px-3 py-2 text-sm text-navy"
            :value="segment.text"
            :aria-label="`Textavsnitt ${segmentIndex + 1} i stycke ${paragraphIndex + 1}`"
            :data-test="`exam-workspace-body-text-${paragraphIndex}-${segmentIndex}`"
            @input="handleBodyTextInput(paragraphIndex, segmentIndex, $event)"
          />
          <span
            v-else-if="segment.kind === 'gap'"
            class="inline-flex h-10 items-center border border-navy/35 bg-panel-muted px-2 font-mono text-xs text-navy"
            :data-test="`exam-workspace-body-gap-${paragraphIndex}-${segmentIndex}`"
          >[___]</span>
          <span
            v-else
            class="inline-flex h-10 items-center border border-navy/35 bg-panel-muted px-2 text-xs text-navy"
          >Bild</span>
        </template>
      </div>
      <p
        v-if="item.kind === 'free_text'"
        class="text-[11px] leading-snug text-navy/65"
      >
        Fritextfråga – eleven svarar med egen text.
      </p>
    </fieldset>

    <fieldset
      v-if="item.kind === 'single_choice' || item.kind === 'multiple_response'"
      class="grid gap-2 border border-navy/20 bg-panel p-3"
    >
      <legend class="px-1 text-xs font-semibold text-navy/80">
        Svarsalternativ
      </legend>
      <div
        v-for="choice in item.choices"
        :key="choice.choice_id"
        class="grid grid-cols-[auto_minmax(0,1fr)] items-center gap-2"
      >
        <input
          v-if="item.kind === 'single_choice'"
          type="radio"
          class="h-4 w-4"
          :name="`exam-workspace-correct-${item.item_id}`"
          :checked="isCorrectChoice(choice.choice_id)"
          :aria-label="`Rätt svar: ${choice.choice_id}`"
          :data-test="`exam-workspace-choice-correct-${choice.choice_id}`"
          @change="handleSingleCorrectChoice(choice.choice_id)"
        >
        <input
          v-else
          type="checkbox"
          class="h-4 w-4"
          :checked="isCorrectChoice(choice.choice_id)"
          :aria-label="`Rätt svar: ${choice.choice_id}`"
          :data-test="`exam-workspace-choice-correct-${choice.choice_id}`"
          @change="handleMultipleCorrectChoice(choice.choice_id, $event)"
        >
        <input
          class="min-h-10 w-full border border-navy/35 bg-panel px-3 text-sm text-navy"
          type="text"
          :value="choice.text"
          :aria-label="`Text för svarsalternativ ${choice.choice_id}`"
          :data-test="`exam-workspace-choice-text-${choice.choice_id}`"
          @input="handleChoiceTextInput(choice.choice_id, $event)"
        >
      </div>
      <p class="text-[11px] leading-snug text-navy/65">
        Markera rätt svar.
      </p>
    </fieldset>

    <fieldset
      v-if="item.kind === 'gap_fill' && item.gaps.length > 0"
      class="grid gap-2 border border-navy/20 bg-panel p-3"
    >
      <legend class="px-1 text-xs font-semibold text-navy/80">
        Luckor
      </legend>
      <label
        v-for="(gap, gapIndex) in item.gaps"
        :key="gap.gap_id"
        class="grid gap-1 text-xs font-semibold text-navy/80"
      >
        Lucka {{ gapIndex + 1 }} – godkända svar (kommaseparerade)
        <input
          class="min-h-10 w-full border border-navy/35 bg-panel px-3 text-sm font-normal text-navy"
          type="text"
          :value="gap.accepted_values.join(', ')"
          :data-test="`exam-workspace-gap-values-${gap.gap_id}`"
          @change="handleGapValuesChange(gap.gap_id, $event)"
        >
        <span
          v-if="gap.hint"
          class="text-[11px] font-normal leading-snug text-navy/65"
        >
          Ledtråd: {{ gap.hint }}
        </span>
      </label>
      <p
        v-if="hasPartialGapKey"
        class="text-xs leading-snug text-navy/70"
        role="status"
        aria-live="polite"
        data-test="exam-workspace-gap-key-hint"
      >
        {{ PARTIAL_GAP_KEY_GUIDANCE }}
      </p>
    </fieldset>
  </section>
</template>
