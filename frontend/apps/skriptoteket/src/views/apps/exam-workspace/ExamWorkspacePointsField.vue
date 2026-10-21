<script setup lang="ts">
/**
 * Exam workspace points field.
 *
 * Domain purpose:
 *   Edit the question's points and, for a Kategorisera grid, its points per
 *   tick (Q10). Points may be 0; empty points are marked "Saknas", negative
 *   points show blocking guidance, and points the import spread from the
 *   section total show an "Uppskattad utifrån avsnittets totalpoäng" cue. A
 *   grid's points are its tick value times its ticks, and a free-text item's
 *   points are its criteria sum, so those inputs are read-only. A tick value
 *   is a number of at least 0 with at most 2 decimals; while the typed tick
 *   value is invalid the last valid value stays in the document and the field
 *   is marked.
 *
 *   Right after an import, a question whose points differ from the source
 *   shows "Provtexten: {n} p" next to the field, naming every printed value
 *   when its own lines printed two different ones (TASK-SKRIPT-40-04-23).
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceQuestionEditor` at the bottom of every
 *     question, for every item kind.
 *   - Receives the item, the lock and the converting state; the editor owns
 *     the document state.
 *   - Emits the typed value; `useExamWorkspaceItemEdits` owns the state.
 */

import { computed, inject, ref, useId } from "vue";

import type { NativeExamItem } from "../../../api/examWorkspace";
import { UiGlyph } from "../../../components/ui";
import { hasNegativePoints, NEGATIVE_POINTS_GUIDANCE } from "./examWorkspaceItemSaveRules";
import { EXAM_WORKSPACE_IMPORT_POINTS_KEY, examWorkspaceSourcePointsHintText } from "./examWorkspaceImportPoints";

/** A tick value is a number of at least 0 with at most 2 decimals (Q10). */
const TICK_POINTS_PATTERN = /^\d+(\.\d{1,2})?$/;

const props = defineProps<{
  item: NativeExamItem;
  disabled: boolean;
  converting: boolean;
}>();

const emit = defineEmits<{
  updatePoints: [points: number | null];
  updateTickPoints: [tickPoints: string];
}>();

const pointsId = useId();
const pointsMessageId = useId();
const tickId = useId();
const tickInvalid = ref(false);

const isGrid = computed(() => props.item.kind === "matching");
const hasCriteria = computed(() => props.item.criteria.length > 0);
const pointsMissing = computed(() => props.item.points === null);
const pointsNegative = computed(() => hasNegativePoints(props.item));
/** Points the import spread from the section total; shown as a nonblocking cue until the teacher sets them. */
const pointsEstimated = computed(
  () => props.item.points_estimated && !pointsMissing.value && !pointsNegative.value && !isGrid.value && !hasCriteria.value,
);
const importPoints = inject(EXAM_WORKSPACE_IMPORT_POINTS_KEY, null);
/** The source's printed points while this question is marked by the import line; shown as a nonblocking cue. */
const sourcePointsHint = computed(() => {
  if (props.converting) {
    return null;
  }
  if (importPoints?.value.has(props.item.item_id) !== true) {
    return null;
  }
  return examWorkspaceSourcePointsHintText(props.item);
});

function handlePointsInput(event: Event): void {
  const target = event.target;
  if (!(target instanceof HTMLInputElement)) {
    return;
  }
  const raw = target.value.trim().replace(",", ".");
  if (raw.length === 0) {
    emit("updatePoints", null);
    return;
  }
  const parsed = Number(raw);
  emit("updatePoints", Number.isFinite(parsed) ? parsed : null);
}

/** Keep the last valid tick value in the document; mark the field while the typed value is invalid. */
function handleTickPointsInput(event: Event): void {
  const target = event.target;
  if (!(target instanceof HTMLInputElement)) {
    return;
  }
  const raw = target.value.trim().replace(",", ".");
  const valid = TICK_POINTS_PATTERN.test(raw);
  tickInvalid.value = !valid;
  if (valid) {
    emit("updateTickPoints", String(Number(raw)));
  }
}
</script>

<template>
  <div class="pts">
    <template v-if="isGrid && !converting">
      <label
        class="xw-label pts__label"
        :for="tickId"
      >Poäng per kryss</label>
      <input
        :id="tickId"
        class="xw-input pts__input"
        type="number"
        min="0"
        step="0.01"
        inputmode="decimal"
        :value="item.tick_points ?? ''"
        :disabled="disabled"
        :aria-invalid="tickInvalid || undefined"
        data-test="exam-workspace-item-tick-points-input"
        @input="handleTickPointsInput"
      >
    </template>
    <label
      class="xw-label pts__label"
      :for="pointsId"
    >Poäng</label>
    <!-- A grid's points are its tick value times its ticks (Q10), and a free-text item's points are its criteria sum, so they are read-only. -->
    <input
      :id="pointsId"
      class="xw-input pts__input"
      type="number"
      min="0"
      step="any"
      inputmode="decimal"
      :value="item.points ?? ''"
      :disabled="disabled"
      :readonly="isGrid || hasCriteria"
      :title="isGrid ? 'Poäng per kryss × antal kryss' : hasCriteria ? 'Summan av kriteriernas poäng' : undefined"
      :aria-invalid="pointsMissing || pointsNegative || undefined"
      :aria-describedby="pointsMissing || pointsNegative || pointsEstimated ? pointsMessageId : undefined"
      data-test="exam-workspace-item-points-input"
      @input="handlePointsInput"
    >
    <span
      v-if="sourcePointsHint !== null"
      class="xw-warn pts__msg"
      data-test="exam-workspace-points-source"
    >{{ sourcePointsHint }}</span>
    <span
      v-if="pointsNegative"
      :id="pointsMessageId"
      class="xw-errline pts__msg"
      data-test="exam-workspace-points-hint"
    ><UiGlyph
      meaning="blocker"
      :size="16"
    />{{ NEGATIVE_POINTS_GUIDANCE }}</span>
    <span
      v-else-if="pointsMissing && !converting"
      :id="pointsMessageId"
      class="xw-errline pts__msg"
      data-test="exam-workspace-points-missing"
    ><UiGlyph
      meaning="blocker"
      :size="16"
    />Saknas</span>
    <span
      v-else-if="pointsEstimated && !converting"
      :id="pointsMessageId"
      class="xw-hint pts__msg"
      data-test="exam-workspace-points-estimated"
    ><UiGlyph
      meaning="info"
      :size="16"
    />Uppskattad utifrån avsnittets totalpoäng</span>
  </div>
</template>

<style scoped>
.pts { display: flex; flex-wrap: wrap; align-items: center; gap: var(--huleedu-space-2) var(--huleedu-space-3); margin-top: var(--huleedu-space-5); }
.pts .pts__label { margin: 0; }
.pts__input { width: 96px; }
.pts__input[readonly] { background: var(--huleedu-navy-02); }
.pts__msg { margin: 0; }
</style>
