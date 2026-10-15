<script setup lang="ts">
/**
 * Exam workspace item editor.
 *
 * Domain purpose:
 *   Edit one native exam item as the dominating Redigera surface:
 *   points, the question text with inline gaps, choices with the correct
 *   answer, the Kategorisera grid with its tick value, and
 *   the mark-as-reviewed action. Previous/next and the details
 *   drawer toggle sit in the editor header so moving between questions
 *   never needs the list. Points that are not greater than zero and an
 *   empty choice text are marked invalid at the field with a Swedish hint,
 *   because the save refuses them. While `disabled` (a save or load is
 *   running, or the item is a placeholder whose batch still converts) every
 *   edit control is disabled; navigation and the details toggle stay
 *   available.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceView` for the selected item.
 *   - Delegates the question text and gap answers to
 *     `ExamWorkspaceBodyEditor`, the Kategorisera grid to
 *     `ExamWorkspaceKategoriseraGrid` and the Fritext criteria to
 *     `ExamWorkspaceCriteriaField`; while criteria exist the points are
 *     their sum and read-only.
 *   - Emits typed update events; `useExamWorkspaceDocument` owns the state.
 *   - Reads the save rules from `examWorkspaceItemSaveRules`.
 *   - Provides the shared rich-text target registry: the one formatting
 *     toolbar and every rich surface (question, choice, Kategorisera entry)
 *     edit the selection the teacher is looking at, never a stale one.
 *   - Tells the teacher when the question is a child of a parent, which
 *     it cannot move, remove or retype here.
 */

import { computed, ref, useId, watch } from "vue";

import { IconAi, IconCheck, IconNextPage, IconPreviousPage, IconUndo, IconWarning } from "../../../components/icons";

import type {
  NativeExamBodyParagraph,
  NativeExamBodySegment,
  NativeExamCriterion,
  NativeExamItem,
  NativeExamMatchPair,
} from "../../../api/examWorkspace";
import ExamWorkspaceBodyEditor from "./ExamWorkspaceBodyEditor.vue";
import ExamWorkspaceChoiceField from "./ExamWorkspaceChoiceField.vue";
import ExamWorkspaceCriteriaField from "./ExamWorkspaceCriteriaField.vue";
import ExamWorkspaceKategoriseraGrid from "./ExamWorkspaceKategoriseraGrid.vue";
import {
  hasNonPositivePoints,
  NON_POSITIVE_POINTS_GUIDANCE,
} from "./examWorkspaceItemSaveRules";
import { PARENT_CHILD_LOCKED_COPY } from "./examWorkspaceParents";
import type { ExamWorkspaceParentChild } from "./examWorkspaceParents";
import { provideRichTextTargetRegistry } from "./examWorkspaceRichTextTarget";
import { examWorkspaceAiKeyLabel, examWorkspaceTypeLabel } from "./examWorkspaceRows";

const props = defineProps<{
  attentionCount: number;
  /** Asset URL per asset id, handed to the question-text editor for picture rendering. */
  assetUrls?: Record<string, string>;
  detailsOpen: boolean;
  disabled?: boolean;
  item: NativeExamItem;
  parentChild?: ExamWorkspaceParentChild | null;
  position: number;
  showNavigation: boolean;
  total: number;
}>();

provideRichTextTargetRegistry();

const emit = defineEmits<{
  markReviewed: [itemId: string];
  undoInterpretation: [itemId: string];
  removeAutomaticValue: [itemId: string, gapId: string, value: string];
  showGapAsText: [itemId: string, gapId: string];
  next: [];
  previous: [];
  toggleDetails: [];
  updateChoiceBody: [itemId: string, choiceId: string, body: NativeExamBodyParagraph[]];
  updateCorrectChoices: [itemId: string, correctChoiceIds: string[]];
  updateCriteria: [itemId: string, criteria: NativeExamCriterion[]];
  updateGapValues: [itemId: string, gapId: string, acceptedValues: string[]];
  updateMatchEntryBody: [
    itemId: string,
    side: "left" | "right",
    entryId: string,
    body: NativeExamBodyParagraph[],
  ];
  updateMatchPairs: [itemId: string, pairs: NativeExamMatchPair[]];
  updateParagraphSegments: [
    itemId: string,
    paragraphIndex: number,
    segments: NativeExamBodySegment[],
  ];
  updateParagraphHeading: [
    itemId: string,
    paragraphIndex: number,
    headingLevel: NativeExamBodyParagraph["heading_level"],
  ];
  updatePoints: [itemId: string, points: number | null];
  updateTickPoints: [itemId: string, tickPoints: string];
}>();

const pointsHintId = useId();

const TYPE_CONFIDENCE_THRESHOLD = 0.95;

const aiKeyLabel = computed(() => examWorkspaceAiKeyLabel(props.item.answer_key.origin));

const typeUncertain = computed(
  () =>
    typeof props.item.review.confidence === "number" &&
    props.item.review.confidence < TYPE_CONFIDENCE_THRESHOLD,
);

const pointsInvalid = computed(() => props.item.points === null || hasNonPositivePoints(props.item));
const hasCriteria = computed(() => props.item.criteria.length > 0);

const isGrid = computed(() => props.item.kind === "matching");

/** A tick value is a positive number with at most 2 decimals (Q10). */
const TICK_POINTS_PATTERN = /^\d+(\.\d{1,2})?$/;

const tickInvalid = ref(false);

watch(
  () => props.item.item_id,
  () => {
    tickInvalid.value = false;
  },
);

/** Keep the last valid tick value in the document; mark the field while the typed value is invalid. */
function handleTickPointsInput(event: Event): void {
  const raw = (event.target as HTMLInputElement).value.trim().replace(",", ".");
  const valid = TICK_POINTS_PATTERN.test(raw) && Number(raw) > 0;
  tickInvalid.value = !valid;
  if (valid) {
    emit("updateTickPoints", props.item.item_id, String(Number(raw)));
  }
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
      <span class="inline-flex h-6 w-6 shrink-0 items-center justify-center">
        <span
          v-if="aiKeyLabel"
          role="img"
          :aria-label="aiKeyLabel"
          :title="aiKeyLabel"
          data-test="exam-workspace-editor-ai-key"
        >
          <IconAi
            :size="18"
            aria-hidden="true"
          />
        </span>
      </span>
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
          v-if="item.review.state === 'review_required' || item.answer_key.origin === 'machine_proposed'"
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
        <span class="inline-flex h-11 w-11 shrink-0 items-center justify-center sm:h-9 sm:w-9">
          <button
            v-if="item.answer_key.origin === 'ai_interpreted'"
            type="button"
            class="inline-flex h-11 w-11 items-center justify-center border border-navy/35 bg-panel hover:bg-canvas disabled:opacity-40 sm:h-9 sm:w-9"
            aria-label="Ångra AI-tolkningen"
            title="Ångra AI-tolkningen"
            :disabled="disabled"
            data-test="exam-workspace-undo-interpretation"
            @click="emit('undoInterpretation', item.item_id)"
          >
            <IconUndo
              :size="18"
              aria-hidden="true"
            />
          </button>
        </span>
        <span class="inline-flex h-11 w-11 shrink-0 items-center justify-center sm:h-9 sm:w-9">
          <button
            v-if="item.review.state === 'review_required' || aiKeyLabel"
            type="button"
            class="inline-flex h-11 w-11 items-center justify-center border border-navy/35 bg-panel hover:bg-canvas disabled:opacity-40 sm:h-9 sm:w-9"
            aria-label="Markera som granskad"
            title="Markera som granskad"
            :disabled="disabled"
            data-test="exam-workspace-mark-reviewed"
            @click="emit('markReviewed', item.item_id)"
          >
            <IconCheck
              :size="18"
              aria-hidden="true"
            />
          </button>
        </span>
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

    <div
      v-if="item.answer_key.origin === 'absent' && item.facit_text"
      class="border-l-4 border-navy/35 pl-3 text-sm text-navy"
      data-test="exam-workspace-original-facit"
    >
      <p class="text-xs font-semibold text-navy/80">Facit i originalet</p>
      <p class="whitespace-pre-wrap">{{ item.facit_text }}</p>
    </div>

    <div class="grid gap-3">
      <div class="flex flex-wrap items-end gap-3">
        <label
          v-if="item.kind === 'matching'"
          class="grid gap-1 text-xs font-semibold text-navy/80"
        >
          Poäng per kryss
          <input
            class="min-h-10 w-28 border bg-panel px-3 text-sm font-normal text-navy"
            :class="tickInvalid ? 'border-warning' : 'border-navy/35'"
            type="number"
            min="0.01"
            step="0.01"
            inputmode="decimal"
            :value="item.tick_points ?? ''"
            :disabled="disabled"
            :aria-invalid="tickInvalid ? 'true' : undefined"
            data-test="exam-workspace-item-tick-points-input"
            @input="handleTickPointsInput"
          >
        </label>
        <label class="grid gap-1 text-xs font-semibold text-navy/80">
          Poäng
          <!-- A grid's points are its tick value times its ticks (Q10), and a free-text item's points are its criteria sum, so they are read-only. -->
          <input
            class="min-h-10 w-28 border px-3 text-sm font-normal text-navy"
            :class="[
              pointsInvalid ? 'border-warning' : 'border-navy/35',
              isGrid || hasCriteria ? 'bg-canvas' : 'bg-panel',
            ]"
            type="number"
            min="0"
            step="any"
            inputmode="decimal"
            :value="item.points ?? ''"
            :disabled="disabled"
            :readonly="isGrid || hasCriteria"
            :title="isGrid ? 'Poäng per kryss × antal kryss' : hasCriteria ? 'Summan av kriteriernas poäng' : undefined"
            :aria-invalid="pointsInvalid ? 'true' : undefined"
            :aria-describedby="hasNonPositivePoints(item) ? pointsHintId : undefined"
            data-test="exam-workspace-item-points-input"
            @input="handlePointsInput"
          >
        </label>
      </div>
      <p
        v-if="hasNonPositivePoints(item)"
        :id="pointsHintId"
        class="border-l-4 border-warning pl-2 text-sm leading-snug text-navy"
        data-test="exam-workspace-points-hint"
      >
        {{ NON_POSITIVE_POINTS_GUIDANCE }}
      </p>
    </div>

    <ExamWorkspaceBodyEditor
      :asset-urls="assetUrls"
      :disabled="disabled"
      :item="item"
      @update-gap-values="(itemId, gapId, values) => emit('updateGapValues', itemId, gapId, values)"
      @remove-automatic-value="(itemId, gapId, value) => emit('removeAutomaticValue', itemId, gapId, value)"
      @show-gap-as-text="(itemId, gapId) => emit('showGapAsText', itemId, gapId)"
      @update-paragraph-segments="(itemId, index, segments) => emit('updateParagraphSegments', itemId, index, segments)"
      @update-paragraph-heading="(itemId, index, headingLevel) => emit('updateParagraphHeading', itemId, index, headingLevel)"
    />

    <ExamWorkspaceCriteriaField
      v-if="item.kind === 'free_text'"
      :disabled="disabled"
      :item="item"
      @update="(criteria) => emit('updateCriteria', item.item_id, criteria)"
    />

    <ExamWorkspaceChoiceField
      :disabled="disabled"
      :item="item"
      @update-body="(choiceId, body) => emit('updateChoiceBody', item.item_id, choiceId, body)"
      @update-correct-choices="
        (correctChoiceIds) => emit('updateCorrectChoices', item.item_id, correctChoiceIds)
      "
    />

    <ExamWorkspaceKategoriseraGrid
      v-if="item.kind === 'matching'"
      :disabled="disabled"
      :item="item"
      @update-entry-body="
        (side, entryId, body) => emit('updateMatchEntryBody', item.item_id, side, entryId, body)
      "
      @update-pairs="(pairs) => emit('updateMatchPairs', item.item_id, pairs)"
    />
  </section>
</template>
