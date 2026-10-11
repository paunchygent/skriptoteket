<script setup lang="ts">
/**
 * Exam workspace item editor.
 *
 * Domain purpose:
 *   Edit one native exam item as the dominating Redigera surface: title,
 *   points, the question text with inline gaps, choices with the correct
 *   answer, matching lists with the correct right entry per left entry, and
 *   the mark-as-reviewed action. Previous/next and the details
 *   drawer toggle sit in the editor header so moving between questions
 *   never needs the list. Points that are not greater than zero and an
 *   empty choice text are marked invalid at the field with a Swedish hint,
 *   because the save refuses them. While `disabled` (a save or load is
 *   running) every edit control is disabled so no typed edit is lost;
 *   navigation and the details toggle stay available.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceView` for the selected item.
 *   - Delegates the question text and gap answers to
 *     `ExamWorkspaceBodyEditor`.
 *   - Emits typed update events; `useExamWorkspaceDocument` owns the state.
 *   - Reads the save rules from `examWorkspaceItemSaveRules`.
 *   - Tells the teacher when the question is a child of a parent, which
 *     it cannot move, remove or retype here.
 */

import { computed, useId } from "vue";

import { IconCheck, IconNextPage, IconPreviousPage, IconWarning } from "../../../components/icons";

import type {
  NativeExamBodySegment,
  NativeExamItem,
  NativeExamMatchPair,
} from "../../../api/examWorkspace";
import {
  INCOMPLETE_MATCH_KEY_GUIDANCE,
  isIncompleteMatchingItem,
} from "./examWorkspaceAnswerKeyRules";
import ExamWorkspaceBodyEditor from "./ExamWorkspaceBodyEditor.vue";
import ExamWorkspaceMarkingGuideField from "./ExamWorkspaceMarkingGuideField.vue";
import {
  EMPTY_CHOICE_TEXT_GUIDANCE,
  EMPTY_MATCH_TEXT_GUIDANCE,
  hasEmptyChoiceText,
  hasEmptyMatchText,
  hasNonPositivePoints,
  isEmptyChoiceText,
  NON_POSITIVE_POINTS_GUIDANCE,
} from "./examWorkspaceItemSaveRules";
import { PARENT_CHILD_LOCKED_COPY } from "./examWorkspaceParents";
import type { ExamWorkspaceParentChild } from "./examWorkspaceParents";
import { examWorkspaceTypeLabel } from "./examWorkspaceRows";

const props = defineProps<{
  attentionCount: number;
  detailsOpen: boolean;
  disabled?: boolean;
  item: NativeExamItem;
  parentChild?: ExamWorkspaceParentChild | null;
  position: number;
  showNavigation: boolean;
  total: number;
}>();

const emit = defineEmits<{
  markReviewed: [itemId: string];
  next: [];
  previous: [];
  toggleDetails: [];
  updateChoiceText: [itemId: string, choiceId: string, text: string];
  updateCorrectChoices: [itemId: string, correctChoiceIds: string[]];
  updateGapValues: [itemId: string, gapId: string, acceptedValues: string[]];
  updateMatchEntryText: [
    itemId: string,
    side: "left" | "right",
    entryId: string,
    text: string,
  ];
  updateMarkingGuide: [itemId: string, guide: string | null];
  updateMatchPairs: [itemId: string, pairs: NativeExamMatchPair[]];
  updateParagraphSegments: [
    itemId: string,
    paragraphIndex: number,
    segments: NativeExamBodySegment[],
  ];
  updatePoints: [itemId: string, points: number | null];
  updateTitle: [itemId: string, title: string];
}>();

const pointsHintId = useId();
const choiceHintId = useId();
const matchHintId = useId();
const matchKeyHintId = useId();

const TYPE_CONFIDENCE_THRESHOLD = 0.95;

const typeUncertain = computed(
  () =>
    typeof props.item.review.confidence === "number" &&
    props.item.review.confidence < TYPE_CONFIDENCE_THRESHOLD,
);

const pointsInvalid = computed(() => props.item.points === null || hasNonPositivePoints(props.item));

function choiceTextClass(choiceId: string, text: string): string {
  if (isEmptyChoiceText(text)) {
    return "border-warning";
  }
  return isCorrectChoice(choiceId)
    ? "border-success shadow-[inset_4px_0_0_var(--color-success)]"
    : "border-navy/35";
}

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

function choiceLetter(index: number): string {
  return String.fromCharCode(65 + index);
}

function matchTextClass(text: string): string {
  return isEmptyChoiceText(text) ? "border-warning" : "border-navy/35";
}

function handleMatchEntryTextInput(side: "left" | "right", entryId: string, event: Event): void {
  const input = event.target as HTMLInputElement;
  emit("updateMatchEntryText", props.item.item_id, side, entryId, input.value);
}

function selectedRightId(leftId: string): string {
  return props.item.answer_key.match_pairs.find((pair) => pair.left_id === leftId)?.right_id ?? "";
}

/** Rebuild the full pair list in left order, with the new choice for one left entry. */
function handleMatchPairSelect(leftId: string, event: Event): void {
  const select = event.target as HTMLSelectElement;
  const pairs: NativeExamMatchPair[] = [];
  for (const left of props.item.match_left) {
    const rightId = left.left_id === leftId ? select.value : selectedRightId(left.left_id);
    if (rightId !== "") {
      pairs.push({ left_id: left.left_id, right_id: rightId });
    }
  }
  emit("updateMatchPairs", props.item.item_id, pairs);
}
</script>

<template>
  <section
    class="grid content-start gap-5"
    :aria-label="`Redigera fråga ${item.sequence}`"
    data-test="exam-workspace-item-editor"
  >
    <header class="flex flex-wrap items-center gap-x-4 gap-y-2">
      <div
        v-if="showNavigation"
        class="flex items-center"
      >
        <button
          type="button"
          class="inline-flex h-9 w-9 items-center justify-center border border-navy/35 bg-panel hover:bg-canvas disabled:opacity-40"
          aria-label="Föregående fråga"
          :disabled="position <= 1"
          data-test="exam-workspace-item-previous"
          @click="emit('previous')"
        >
          <IconPreviousPage :size="18" />
        </button>
        <button
          type="button"
          class="-ml-px inline-flex h-9 w-9 items-center justify-center border border-navy/35 bg-panel hover:bg-canvas disabled:opacity-40"
          aria-label="Nästa fråga"
          :disabled="position >= total"
          data-test="exam-workspace-item-next"
          @click="emit('next')"
        >
          <IconNextPage :size="18" />
        </button>
      </div>
      <h2 class="shrink-0 whitespace-nowrap text-base font-semibold leading-tight text-navy">
        Fråga {{ item.sequence }}
        <span class="font-normal text-navy/65">– {{ examWorkspaceTypeLabel(item.kind) }}</span>
      </h2>
      <span
        v-if="typeUncertain"
        class="text-xs text-navy/65"
        data-test="exam-workspace-type-uncertain"
      >Kontrollera frågetypen</span>
      <div
        class="ml-auto flex flex-wrap items-center gap-3"
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
          :disabled="disabled"
          data-test="exam-workspace-mark-reviewed"
          @click="emit('markReviewed', item.item_id)"
        >
          Markera som granskad
        </button>
        <button
          type="button"
          class="btn-ghost shadow-none"
          :aria-pressed="detailsOpen ? 'true' : 'false'"
          data-test="exam-workspace-item-details-toggle"
          @click="emit('toggleDetails')"
        >
          Detaljer
          <span
            v-if="attentionCount > 0"
            class="ml-1 inline-flex h-5 min-w-5 items-center justify-center bg-warning px-1 text-[11px] font-bold leading-none text-navy"
            :aria-label="`${attentionCount} att åtgärda`"
          >{{ attentionCount }}</span>
        </button>
      </div>
    </header>

    <p
      v-if="parentChild"
      class="border-l-4 border-navy/35 pl-2 text-sm leading-snug text-navy"
      data-test="exam-workspace-parent-child-note"
    >
      Deluppgift {{ parentChild.childIndex + 1 }} av {{ parentChild.childCount }}. Den gemensamma
      instruktionen visas i listan över frågor. {{ PARENT_CHILD_LOCKED_COPY }}
    </p>

    <div class="grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
      <label class="grid gap-1 text-xs font-semibold text-navy/80">
        Rubrik
        <input
          class="min-h-10 w-full border border-navy/35 bg-panel px-3 text-sm font-normal text-navy"
          type="text"
          :value="item.title ?? ''"
          :disabled="disabled"
          data-test="exam-workspace-item-title-input"
          @input="handleTitleInput"
        >
      </label>
      <label class="grid gap-1 text-xs font-semibold text-navy/80">
        Poäng
        <input
          class="min-h-10 w-28 border bg-panel px-3 text-sm font-normal text-navy"
          :class="pointsInvalid ? 'border-warning' : 'border-navy/35'"
          type="number"
          min="0"
          step="any"
          inputmode="decimal"
          :value="item.points ?? ''"
          :disabled="disabled"
          :aria-invalid="pointsInvalid ? 'true' : undefined"
          :aria-describedby="hasNonPositivePoints(item) ? pointsHintId : undefined"
          data-test="exam-workspace-item-points-input"
          @input="handlePointsInput"
        >
      </label>
      <p
        v-if="hasNonPositivePoints(item)"
        :id="pointsHintId"
        class="border-l-4 border-warning pl-2 text-sm leading-snug text-navy sm:col-span-2"
        data-test="exam-workspace-points-hint"
      >
        {{ NON_POSITIVE_POINTS_GUIDANCE }}
      </p>
    </div>

    <ExamWorkspaceBodyEditor
      :disabled="disabled"
      :item="item"
      @update-gap-values="(itemId, gapId, values) => emit('updateGapValues', itemId, gapId, values)"
      @update-paragraph-segments="(itemId, index, segments) => emit('updateParagraphSegments', itemId, index, segments)"
    />

    <ExamWorkspaceMarkingGuideField
      v-if="item.kind === 'free_text'"
      :disabled="disabled"
      :guide="item.marking_guide ?? null"
      @update="(guide) => emit('updateMarkingGuide', item.item_id, guide)"
    />

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
        class="grid grid-cols-[auto_auto_minmax(0,1fr)] items-center gap-2"
      >
        <input
          v-if="item.kind === 'single_choice'"
          type="radio"
          class="h-5 w-5"
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
          class="h-5 w-5"
          :checked="isCorrectChoice(choice.choice_id)"
          :disabled="disabled"
          :aria-label="`Rätt svar: alternativ ${choiceLetter(choiceIndex)}`"
          :data-test="`exam-workspace-choice-correct-${choice.choice_id}`"
          @change="handleMultipleCorrectChoice(choice.choice_id, $event)"
        >
        <span
          class="w-5 text-center text-sm font-semibold text-navy/70"
          aria-hidden="true"
        >{{ choiceLetter(choiceIndex) }}</span>
        <input
          class="min-h-10 w-full border bg-panel px-3 text-base text-navy"
          :class="choiceTextClass(choice.choice_id, choice.text)"
          type="text"
          :value="choice.text"
          :disabled="disabled"
          :aria-invalid="isEmptyChoiceText(choice.text) ? 'true' : undefined"
          :aria-describedby="isEmptyChoiceText(choice.text) ? choiceHintId : undefined"
          :aria-label="`Text för svarsalternativ ${choiceLetter(choiceIndex)}`"
          :data-test="`exam-workspace-choice-text-${choice.choice_id}`"
          @input="handleChoiceTextInput(choice.choice_id, $event)"
        >
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

    <fieldset
      v-if="item.kind === 'matching'"
      class="grid gap-2"
    >
      <legend class="mb-2 text-xs font-semibold text-navy/80">
        Matchning – välj rätt svar för varje rad
      </legend>
      <div
        v-for="(left, leftIndex) in item.match_left"
        :key="left.left_id"
        class="grid grid-cols-[auto_minmax(0,1fr)] items-center gap-2 sm:grid-cols-[auto_minmax(0,1fr)_minmax(0,16rem)]"
      >
        <span
          class="w-5 text-center text-sm font-semibold text-navy/70"
          aria-hidden="true"
        >{{ leftIndex + 1 }}</span>
        <input
          class="min-h-10 w-full border bg-panel px-3 text-base text-navy"
          :class="matchTextClass(left.text)"
          type="text"
          :value="left.text"
          :disabled="disabled"
          :aria-invalid="isEmptyChoiceText(left.text) ? 'true' : undefined"
          :aria-describedby="isEmptyChoiceText(left.text) ? matchHintId : undefined"
          :aria-label="`Text för rad ${leftIndex + 1}`"
          :data-test="`exam-workspace-match-left-text-${left.left_id}`"
          @input="handleMatchEntryTextInput('left', left.left_id, $event)"
        >
        <select
          class="col-start-2 min-h-10 w-full border border-navy/35 bg-panel px-3 text-base text-navy sm:col-start-auto"
          :value="selectedRightId(left.left_id)"
          :disabled="disabled"
          :aria-label="`Rätt svar för rad ${leftIndex + 1}`"
          :data-test="`exam-workspace-match-pair-${left.left_id}`"
          @change="handleMatchPairSelect(left.left_id, $event)"
        >
          <option value="">
            Inget svar valt
          </option>
          <option
            v-for="(right, rightIndex) in item.match_right"
            :key="right.right_id"
            :value="right.right_id"
          >
            {{ choiceLetter(rightIndex) }} – {{ right.text }}
          </option>
        </select>
      </div>
      <div
        v-for="(right, rightIndex) in item.match_right"
        :key="right.right_id"
        class="grid grid-cols-[auto_minmax(0,1fr)] items-center gap-2"
      >
        <span
          class="w-5 text-center text-sm font-semibold text-navy/70"
          aria-hidden="true"
        >{{ choiceLetter(rightIndex) }}</span>
        <input
          class="min-h-10 w-full border bg-panel px-3 text-base text-navy"
          :class="matchTextClass(right.text)"
          type="text"
          :value="right.text"
          :disabled="disabled"
          :aria-invalid="isEmptyChoiceText(right.text) ? 'true' : undefined"
          :aria-describedby="isEmptyChoiceText(right.text) ? matchHintId : undefined"
          :aria-label="`Text för svar ${choiceLetter(rightIndex)}`"
          :data-test="`exam-workspace-match-right-text-${right.right_id}`"
          @input="handleMatchEntryTextInput('right', right.right_id, $event)"
        >
      </div>
      <p
        v-if="hasEmptyMatchText(item)"
        :id="matchHintId"
        class="border-l-4 border-warning pl-2 text-sm leading-snug text-navy"
        data-test="exam-workspace-match-hint"
      >
        {{ EMPTY_MATCH_TEXT_GUIDANCE }}
      </p>
      <p
        v-if="isIncompleteMatchingItem(item)"
        :id="matchKeyHintId"
        class="border-l-4 border-warning pl-2 text-sm leading-snug text-navy"
        data-test="exam-workspace-match-key-hint"
      >
        {{ INCOMPLETE_MATCH_KEY_GUIDANCE }}
      </p>
    </fieldset>
  </section>
</template>
