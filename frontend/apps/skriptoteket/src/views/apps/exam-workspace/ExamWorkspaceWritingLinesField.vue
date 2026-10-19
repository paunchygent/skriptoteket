<script setup lang="ts">
/**
 * Exam workspace Skrivyta field.
 *
 * Domain purpose:
 *   Size a free-text question's printed writing area (W4) in one answer-block
 *   row: boxless − and + tools around a fixed-width count ("N rader"), a
 *   separator, and the word tool "Alla fritextfrågor", which opens a confirm
 *   popover. The stepper emits the next count, clamped to the house range by
 *   the pure transition the command applies. The popover names how many
 *   free-text questions the count applies to and which ones differ today;
 *   "Använd N rader" emits the current count for every free-text question and
 *   closes. When every free-text question already has the count, the same tool
 *   opens a confirmation with only "Stäng". The tool is disabled only while the
 *   whole field is locked, never because the counts already match.
 *
 *   Escape, "Avbryt", "Stäng" and a pointer press outside the tool and popover
 *   close the popover and return focus to the tool. Opening moves focus to the
 *   primary action. The popover is absolutely positioned under the tool, so
 *   opening it and changing the count never move or resize anything in the row.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceQuestionEditor` for a free-text item that
 *     carries a writing-line count, in the answer block above its criteria.
 *   - Receives the count from the item and the free-text summary from
 *     `ExamWorkspaceEditorPane`; the editor renders no field when the item has
 *     no count.
 *   - Emits the values; `useExamWorkspaceItemEdits` (`updateItemWritingLines`)
 *     and `useExamWorkspaceDocumentFields` (`applyWritingLinesToAllFreeText`)
 *     own the state.
 *   - Reads the house bounds, the summary type and the differing-label rule
 *     from `examWorkspaceWritingLines`, and joins labels with `swedishList`.
 */

import { computed, nextTick, onBeforeUnmount, ref, useId, watch } from "vue";

import { UiGlyph } from "../../../components/ui";
import { swedishList } from "./examWorkspaceStructure";
import {
  labelsWithOtherWritingLines,
  MAX_WRITING_LINES,
  MIN_WRITING_LINES,
  type FreeTextWritingLines,
} from "./examWorkspaceWritingLines";

const props = defineProps<{
  disabled?: boolean;
  /** The question's writing-line count; the editor renders the field only when the item has one. */
  lines: number;
  /** Every free-text question in the exam with its display label and count, in document order. */
  freeText: FreeTextWritingLines[];
  /**
   * The id of the element that states why the controls are locked, when the
   * question is locked for a reason the teacher cannot read from the buttons
   * themselves; null or omitted when no such reason applies.
   */
  lockedReasonId?: string | null;
}>();

const emit = defineEmits<{
  update: [lines: number];
  applyToAll: [lines: number];
}>();

function rowsLabel(count: number): string {
  return count === 1 ? "1 rad" : `${count} rader`;
}

const labelId = useId();
const popoverId = useId();
const label = computed(() => rowsLabel(props.lines));
const atMin = computed(() => props.lines <= MIN_WRITING_LINES);
const atMax = computed(() => props.lines >= MAX_WRITING_LINES);
/** The bound each stepper button is stopped by, or undefined while it can move. */
const minReason = computed(() => (atMin.value ? `Minst ${MIN_WRITING_LINES} rad` : undefined));
const maxReason = computed(() => (atMax.value ? `Högst ${MAX_WRITING_LINES} rader` : undefined));
/** The lock notice the buttons point at, only while the whole field is locked. */
const lockReasonId = computed(() => (props.disabled && props.lockedReasonId ? props.lockedReasonId : undefined));

/** The labels of the free-text questions that would change; empty when all already match. */
const otherLabels = computed(() => labelsWithOtherWritingLines(props.freeText, props.lines));
const matched = computed(() => otherLabels.value.length === 0);

const open = ref(false);
const applyWrap = ref<HTMLElement | null>(null);
const tool = ref<HTMLButtonElement | null>(null);
const primary = ref<HTMLButtonElement | null>(null);

function step(delta: -1 | 1): void {
  emit("update", props.lines + delta);
}

function onPointerDown(event: Event): void {
  const target = event.target;
  if (target instanceof Node && applyWrap.value?.contains(target)) {
    return;
  }
  close(false);
}

function close(returnFocus: boolean): void {
  open.value = false;
  if (returnFocus) {
    void nextTick(() => tool.value?.focus());
  }
}

function toggle(): void {
  if (open.value) {
    close(true);
    return;
  }
  open.value = true;
}

function confirm(): void {
  emit("applyToAll", props.lines);
  close(true);
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key !== "Escape" || !open.value || event.isComposing) {
    return;
  }
  event.preventDefault();
  event.stopPropagation();
  close(true);
}

watch(open, async (isOpen) => {
  if (!isOpen) {
    document.removeEventListener("pointerdown", onPointerDown, true);
    return;
  }
  document.addEventListener("pointerdown", onPointerDown, true);
  await nextTick();
  primary.value?.focus();
});

// A locked field cannot confirm anything, so a popover left open closes with it.
watch(
  () => props.disabled,
  (isDisabled) => {
    if (isDisabled) {
      close(false);
    }
  },
);

onBeforeUnmount(() => {
  document.removeEventListener("pointerdown", onPointerDown, true);
});
</script>

<template>
  <div
    class="xw-answer-row"
    role="group"
    :aria-labelledby="labelId"
    data-test="exam-workspace-writing-lines"
  >
    <div
      :id="labelId"
      class="xw-answer-label"
    >
      Skrivyta
    </div>
    <div class="xw-answer-controls xw-lines">
      <button
        type="button"
        class="xw-tool"
        :disabled="disabled || atMin"
        :title="minReason"
        :aria-describedby="lockReasonId"
        aria-label="Färre rader"
        data-test="exam-workspace-writing-lines-minus"
        @click="step(-1)"
      >
        <UiGlyph
          meaning="decrement"
          :size="16"
        />
      </button>
      <span
        class="xw-lines__value"
        data-test="exam-workspace-writing-lines-count"
      >{{ label }}</span>
      <button
        type="button"
        class="xw-tool"
        :disabled="disabled || atMax"
        :title="maxReason"
        :aria-describedby="lockReasonId"
        aria-label="Fler rader"
        data-test="exam-workspace-writing-lines-plus"
        @click="step(1)"
      >
        <UiGlyph
          meaning="add"
          :size="16"
        />
      </button>
      <span
        class="xw-toolsep"
        aria-hidden="true"
      />
      <span
        ref="applyWrap"
        class="xw-lines__apply"
        @keydown="onKeydown"
      >
        <button
          ref="tool"
          type="button"
          class="xw-tool xw-tool--word"
          :disabled="disabled"
          aria-haspopup="dialog"
          :aria-expanded="open"
          :aria-controls="open ? popoverId : undefined"
          :aria-describedby="lockReasonId"
          title="Samma skrivyta för alla fritextfrågor"
          data-test="exam-workspace-writing-lines-apply-all"
          @click="toggle"
        >
          <UiGlyph
            meaning="copy"
            :size="16"
          />
          Alla fritextfrågor
        </button>
        <div
          v-if="open"
          :id="popoverId"
          class="xw-pop"
          role="dialog"
          aria-label="Samma skrivyta för alla fritextfrågor"
          data-test="exam-workspace-writing-lines-popover"
        >
          <template v-if="matched">
            <div class="xw-pop__ok">
              <UiGlyph
                meaning="completed"
                :size="18"
              />
              <div>
                <h3>Samma skrivyta för alla fritextfrågor</h3>
                <p v-if="freeText.length === 1">
                  Det här är provets enda fritextfråga.
                </p>
                <p v-else>
                  Alla {{ freeText.length }} fritextfrågor har redan {{ rowsLabel(lines) }}.
                </p>
              </div>
            </div>
            <div class="xw-pop__acts">
              <button
                ref="primary"
                type="button"
                class="xw-btn xw-btn--ghost"
                data-test="exam-workspace-writing-lines-close"
                @click="close(true)"
              >
                Stäng
              </button>
            </div>
          </template>
          <template v-else>
            <h3>Samma skrivyta för alla fritextfrågor</h3>
            <p>Alla {{ freeText.length }} fritextfrågor får {{ rowsLabel(lines) }}.</p>
            <p>{{ swedishList(otherLabels) }} har i dag en annan skrivyta.</p>
            <div class="xw-pop__acts">
              <button
                type="button"
                class="xw-btn xw-btn--ghost"
                data-test="exam-workspace-writing-lines-cancel"
                @click="close(true)"
              >
                Avbryt
              </button>
              <button
                ref="primary"
                type="button"
                class="xw-btn xw-btn--primary"
                data-test="exam-workspace-writing-lines-apply-confirm"
                @click="confirm"
              >
                Använd {{ rowsLabel(lines) }}
              </button>
            </div>
          </template>
        </div>
      </span>
    </div>
  </div>
</template>
