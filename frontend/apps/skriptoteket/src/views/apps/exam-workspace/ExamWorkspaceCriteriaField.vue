<script setup lang="ts">
/**
 * Exam workspace Fritext criteria.
 *
 * Domain purpose:
 *   Edit the bedömningskriterier of a free-text question: one row per
 *   criterion with its text and whole points (at least 1). The criteria are
 *   the teacher's point breakdown, so a non-empty list sets the question's
 *   points to their sum, and Exam.net receives one 1-point row per criterion
 *   point. The first added criterion takes the question's current whole
 *   points, so adding it leaves the total unchanged. An added row's text field
 *   takes focus, and leaving a points field with invalid points restores its
 *   last valid points. Adding a row is a structural edit (stored at once);
 *   text, points and remove edits are typing (stored after the pause).
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceQuestionEditor` for free-text items only; the
 *     editor makes its points field read-only while criteria exist.
 *   - Emits the full criteria list; `useExamWorkspaceDocument`
 *     (`updateItemCriteria`) owns the state.
 *   - Reads the rules and Swedish guidance from `examWorkspaceItemSaveRules`.
 */

import { nextTick, ref, useId, watch } from "vue";

import type { NativeExamCriterion, NativeExamItem } from "../../../api/examWorkspace";
import { UiGlyph } from "../../../components/ui";
import {
  EMPTY_CRITERION_TEXT_GUIDANCE,
  hasEmptyCriterionText,
  INVALID_CRITERION_POINTS_GUIDANCE,
} from "./examWorkspaceItemSaveRules";

const props = defineProps<{
  disabled?: boolean;
  item: NativeExamItem;
}>();

const emit = defineEmits<{
  update: [criteria: NativeExamCriterion[], structural: boolean];
}>();

const labelId = useId();
const textHintId = useId();
const pointsHintId = useId();
/** Rows whose typed points are not a whole number of at least 1; never emitted. */
const invalidPoints = ref<Set<number>>(new Set());
const root = ref<HTMLDivElement | null>(null);
/** The row an add asked for; its text field takes focus when the parent renders it. */
const pendingFocusRow = ref<number | null>(null);

watch(
  () => props.item.item_id,
  () => {
    invalidPoints.value = new Set();
    pendingFocusRow.value = null;
  },
);

watch(
  () => props.item.criteria.length,
  async (length) => {
    const row = pendingFocusRow.value;
    if (row === null || length <= row) {
      return;
    }
    pendingFocusRow.value = null;
    await nextTick();
    root.value
      ?.querySelector<HTMLInputElement>(`[data-test="exam-workspace-criterion-text-${row}"]`)
      ?.focus();
  },
);

function isWholePoints(raw: string): boolean {
  return /^\d+$/.test(raw) && Number(raw) >= 1;
}

function replaceAt(index: number, criterion: NativeExamCriterion): NativeExamCriterion[] {
  return props.item.criteria.map((current, candidate) =>
    candidate === index ? criterion : current,
  );
}

function handleText(index: number, event: Event): void {
  if (!(event.target instanceof HTMLInputElement)) {
    return;
  }
  const text = event.target.value;
  emit("update", replaceAt(index, { ...props.item.criteria[index], text }), false);
}

function handlePoints(index: number, event: Event): void {
  if (!(event.target instanceof HTMLInputElement)) {
    return;
  }
  const raw = event.target.value.trim();
  const next = new Set(invalidPoints.value);
  if (!isWholePoints(raw)) {
    next.add(index);
    invalidPoints.value = next;
    return;
  }
  next.delete(index);
  invalidPoints.value = next;
  emit("update", replaceAt(index, { ...props.item.criteria[index], points: Number(raw) }), false);
}

/** Leaving a field with invalid points restores its last valid points. */
function handlePointsBlur(index: number, event: FocusEvent): void {
  if (!invalidPoints.value.has(index)) {
    return;
  }
  if (!(event.target instanceof HTMLInputElement)) {
    return;
  }
  event.target.value = String(props.item.criteria[index].points);
  const next = new Set(invalidPoints.value);
  next.delete(index);
  invalidPoints.value = next;
}

function handleAdd(): void {
  const current = props.item.points;
  const first = props.item.criteria.length === 0;
  const points = first && current !== null && Number.isInteger(current) && current >= 1 ? current : 1;
  pendingFocusRow.value = props.item.criteria.length;
  // Adding a row is a structural edit: it is stored at once.
  emit("update", [...props.item.criteria, { text: "", points }], true);
}

function handleRemove(index: number): void {
  invalidPoints.value = new Set(
    [...invalidPoints.value].filter((row) => row !== index).map((row) => (row > index ? row - 1 : row)),
  );
  emit(
    "update",
    props.item.criteria.filter((_, candidate) => candidate !== index),
    false,
  );
}

function isEmptyText(criterion: NativeExamCriterion): boolean {
  return criterion.text.trim().length === 0;
}
</script>

<template>
  <div
    ref="root"
    class="xw-answer-row"
    role="group"
    :aria-labelledby="labelId"
    data-test="exam-workspace-criteria"
  >
    <div
      :id="labelId"
      class="xw-answer-label"
    >
      Bedömningskriterier
    </div>
    <div class="grid min-w-0 gap-1.5">
      <div class="xw-answer-criteria">
        <div
          v-for="(criterion, index) in item.criteria"
          :key="index"
          class="xw-answer-criterion"
        >
          <input
            class="xw-input"
            :class="{ 'xw-input--warning': isEmptyText(criterion) }"
            type="text"
            :value="criterion.text"
            :disabled="disabled"
            :aria-label="`Kriterium ${index + 1}`"
            :aria-invalid="isEmptyText(criterion) ? 'true' : undefined"
            :aria-describedby="isEmptyText(criterion) ? textHintId : undefined"
            :data-test="`exam-workspace-criterion-text-${index}`"
            @input="handleText(index, $event)"
          >
          <span class="xw-answer-points">
            <input
              class="xw-input"
              :class="{ 'xw-input--warning': invalidPoints.has(index) }"
              type="number"
              min="1"
              step="1"
              inputmode="numeric"
              :value="criterion.points"
              :disabled="disabled"
              :aria-label="`Poäng för kriterium ${index + 1}`"
              :aria-invalid="invalidPoints.has(index) ? 'true' : undefined"
              :aria-describedby="invalidPoints.has(index) ? pointsHintId : undefined"
              :data-test="`exam-workspace-criterion-points-${index}`"
              @input="handlePoints(index, $event)"
              @blur="handlePointsBlur(index, $event)"
            >
            <span
              class="xw-answer-points__unit"
              aria-hidden="true"
            >p</span>
          </span>
          <button
            type="button"
            class="xw-tool xw-tool--danger"
            :disabled="disabled"
            :title="`Ta bort kriterium ${index + 1}`"
            :aria-label="`Ta bort kriterium ${index + 1}`"
            :data-test="`exam-workspace-criterion-remove-${index}`"
            @click="handleRemove(index)"
          >
            <UiGlyph
              meaning="delete"
              :size="16"
            />
          </button>
        </div>
      </div>
      <div>
        <button
          type="button"
          class="xw-tool xw-tool--word"
          :disabled="disabled"
          title="Lägg till kriterium"
          aria-label="Lägg till kriterium"
          data-test="exam-workspace-criterion-add"
          @click="handleAdd"
        >
          <UiGlyph
            meaning="add"
            :size="16"
          />
          Kriterium
        </button>
      </div>
      <p
        v-if="hasEmptyCriterionText(item)"
        :id="textHintId"
        class="border-l-4 border-warning pl-2 text-sm leading-snug text-navy"
        data-test="exam-workspace-criterion-text-hint"
      >
        {{ EMPTY_CRITERION_TEXT_GUIDANCE }}
      </p>
      <p
        v-if="invalidPoints.size > 0"
        :id="pointsHintId"
        class="border-l-4 border-warning pl-2 text-sm leading-snug text-navy"
        data-test="exam-workspace-criterion-points-hint"
      >
        {{ INVALID_CRITERION_POINTS_GUIDANCE }}
      </p>
    </div>
  </div>
</template>
