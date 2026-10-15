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
 *   points, so adding it leaves the total unchanged.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceItemEditor` for free-text items only; the
 *     editor makes its points field read-only while criteria exist.
 *   - Emits the full criteria list; `useExamWorkspaceDocument`
 *     (`updateItemCriteria`) owns the state.
 *   - Reads the rules and Swedish guidance from `examWorkspaceItemSaveRules`.
 */

import { ref, useId, watch } from "vue";

import type { NativeExamCriterion, NativeExamItem } from "../../../api/examWorkspace";
import { IconPlus, IconTrash } from "../../../components/icons";
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
  update: [criteria: NativeExamCriterion[]];
}>();

const textHintId = useId();
const pointsHintId = useId();
/** Rows whose typed points are not a whole number of at least 1; never emitted. */
const invalidPoints = ref<Set<number>>(new Set());

watch(
  () => props.item.item_id,
  () => {
    invalidPoints.value = new Set();
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
  const text = (event.target as HTMLInputElement).value;
  emit("update", replaceAt(index, { ...props.item.criteria[index], text }));
}

function handlePoints(index: number, event: Event): void {
  const raw = (event.target as HTMLInputElement).value.trim();
  const next = new Set(invalidPoints.value);
  if (!isWholePoints(raw)) {
    next.add(index);
    invalidPoints.value = next;
    return;
  }
  next.delete(index);
  invalidPoints.value = next;
  emit("update", replaceAt(index, { ...props.item.criteria[index], points: Number(raw) }));
}

function handleAdd(): void {
  const current = props.item.points;
  const first = props.item.criteria.length === 0;
  const points = first && current !== null && Number.isInteger(current) && current >= 1 ? current : 1;
  emit("update", [...props.item.criteria, { text: "", points }]);
}

function handleRemove(index: number): void {
  invalidPoints.value = new Set(
    [...invalidPoints.value].filter((row) => row !== index).map((row) => (row > index ? row - 1 : row)),
  );
  emit(
    "update",
    props.item.criteria.filter((_, candidate) => candidate !== index),
  );
}

function isEmptyText(criterion: NativeExamCriterion): boolean {
  return criterion.text.trim().length === 0;
}
</script>

<template>
  <fieldset
    class="grid gap-2"
    data-test="exam-workspace-criteria"
  >
    <legend class="mb-2 text-xs font-semibold text-navy/80">
      Bedömningskriterier
    </legend>
    <div
      v-for="(criterion, index) in item.criteria"
      :key="index"
      class="grid grid-cols-[minmax(0,1fr)_auto_auto] items-center gap-2"
    >
      <input
        class="min-h-10 w-full border bg-panel px-3 text-sm text-navy"
        :class="isEmptyText(criterion) ? 'border-warning' : 'border-navy/35'"
        type="text"
        :value="criterion.text"
        :disabled="disabled"
        :aria-label="`Kriterium ${index + 1}`"
        :aria-invalid="isEmptyText(criterion) ? 'true' : undefined"
        :aria-describedby="isEmptyText(criterion) ? textHintId : undefined"
        :data-test="`exam-workspace-criterion-text-${index}`"
        @input="handleText(index, $event)"
      >
      <input
        class="min-h-10 w-20 border bg-panel px-3 text-sm text-navy"
        :class="invalidPoints.has(index) ? 'border-warning' : 'border-navy/35'"
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
      >
      <button
        type="button"
        class="inline-flex h-10 w-10 items-center justify-center border border-navy/35 bg-panel text-navy hover:bg-canvas disabled:opacity-50"
        :disabled="disabled"
        :title="`Ta bort kriterium ${index + 1}`"
        :aria-label="`Ta bort kriterium ${index + 1}`"
        :data-test="`exam-workspace-criterion-remove-${index}`"
        @click="handleRemove(index)"
      >
        <IconTrash :size="14" />
      </button>
    </div>
    <div>
      <button
        type="button"
        class="inline-flex min-h-10 items-center gap-2 border border-navy/35 bg-panel px-3 text-sm font-semibold text-navy hover:bg-canvas disabled:opacity-50"
        :disabled="disabled"
        title="Lägg till kriterium"
        aria-label="Lägg till kriterium"
        data-test="exam-workspace-criterion-add"
        @click="handleAdd"
      >
        <IconPlus :size="14" />
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
  </fieldset>
</template>
