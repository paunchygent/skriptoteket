<script setup lang="ts">
/**
 * Exam workspace gap-answer popover.
 *
 * Domain purpose:
 *   Let the teacher edit one gap's accepted answers as one row per answer
 *   right next to the gap chip through `ExamWorkspaceGapAnswerList`: a text
 *   input and a remove glyph per row with a glyph-only add button ("Lägg
 *   till svar" accessible name and tooltip) under the rows. Leaving the
 *   popover commits the answers; Escape
 *   discards them. Each commit is emitted once, even when the browser also
 *   fires `change` while focus returns to the chip. Enter inside an answer
 *   row adds a row below it and never closes the popover. Enter and Escape
 *   pressed while an IME composition is active belong to the composition and
 *   are ignored. Answers the conversion wrote for the
 *   gap (automatic misspellings) show as removable chips with no AI glyph
 *   and no per-chip status tag. "Visa som text" replaces the gap with
 *   its first accepted answer as plain text; it is disabled with a visible
 *   explanation while the answers field (including unsaved typing) holds no
 *   accepted answer.
 *
 *   A dropdown gap (`dropdown`) edits its options instead: one row per
 *   option with a radio for the correct one, an editable text, move up/down
 *   and remove, plus a glyph-only add button ("Lägg till alternativ"
 *   accessible name and tooltip). Radio, add, remove and move emit
 *   the whole option state at once (one patch each); typed option text
 *   commits on `change`, Enter and leaving the popover, and rides along with
 *   the next such emit. Escape discards typed text. The correct option
 *   cannot be removed; a gap with no correct option shows no radio checked,
 *   keeps that state through add, move, remove and text edits, and lets every
 *   option be removed. The accepted answers, automatic answers and "Visa som
 *   text" do not apply to a dropdown gap and are hidden.
 *
 *   The panel is teleported to the body and anchored to the gap chip through
 *   `useExamWorkspaceAnchoredPosition` (below the chip, or above it when the
 *   space below is too small), so the editor's clipping never hides it.
 *
 * Relationships:
 *   - Opened by `ExamWorkspaceBodyEditor`, which keys it by item and gap so
 *     the ids below never change while it is open.
 *   - Reads the text-gap answers through `ExamWorkspaceGapAnswerList`,
 *     which commits on close and reports unsaved typing as `draft`.
 */

import { computed, nextTick, onMounted, reactive, ref, useId, watch } from "vue";

import type { NativeExamChoice, NativeExamGap } from "../../../api/examWorkspace";
import { UiGlyph } from "../../../components/ui";
import { useExamWorkspaceAnchoredPosition } from "./useExamWorkspaceAnchoredPosition";
import ExamWorkspaceGapAnswerList from "./ExamWorkspaceGapAnswerList.vue";
import ExamWorkspaceGapAutomaticValues from "./ExamWorkspaceGapAutomaticValues.vue";
import { bodyText, plainBody } from "./examWorkspaceRichText";

const MISSING_ANSWER_COPY = "Fyll i ett godkänt svar först.";
const REMOVE_CORRECT_COPY = "Markera ett annat alternativ som rätt först";

const props = defineProps<{
  itemId: string;
  gapId: string;
  gapNumber: number;
  gap: NativeExamGap | null;
  dropdown?: boolean;
  anchor: HTMLElement;
}>();

const emit = defineEmits<{
  commit: [itemId: string, gapId: string, acceptedValues: string[]];
  removeAutomaticValue: [itemId: string, gapId: string, value: string];
  showGapAsText: [itemId: string, gapId: string];
  updateOptions: [itemId: string, gapId: string, options: NativeExamChoice[], correctOptionId: string | null];
  close: [returnFocus: boolean];
}>();

// Captured at open: the popover is keyed by item and gap, so these stay fixed.
const itemId = props.itemId;
const gapId = props.gapId;

const root = ref<HTMLElement | null>(null);
const answerList = ref<InstanceType<typeof ExamWorkspaceGapAnswerList> | null>(null);
// The chip the popover is keyed to; the anchored position follows its viewport rect.
const anchorRef = ref<HTMLElement | null>(props.anchor);
const { position, place } = useExamWorkspaceAnchoredPosition(anchorRef, root);
const removeHintId = useId();
const optionsLabelId = useId();
const showAsTextExplanationId = useId();
const automaticValues = computed(() => props.gap?.automatic_values ?? []);
// Pending answers as last reported by the row list; the saved gap only changes on commit.
const draftAcceptedValues = ref<string[]>([...(props.gap?.accepted_values ?? [])]);
const showAsTextDisabledReason = computed(() => {
  if (!draftAcceptedValues.value[0]) {
    return MISSING_ANSWER_COPY;
  }
  return null;
});
let lastCommitted = props.gap?.accepted_values ?? [];
let discarded = false;

function sameValues(left: string[], right: string[]): boolean {
  return left.length === right.length && left.every((value, index) => value === right[index]);
}

function handleAnswersCommit(values: string[]): void {
  if (discarded) {
    return;
  }
  lastCommitted = values;
  emit("commit", itemId, gapId, values);
}

function handleAnswersDraft(values: string[]): void {
  draftAcceptedValues.value = values;
  // Rows changing the panel height re-anchor after render.
  void nextTick(() => place());
}

// Follow an externally changed gap, but never clobber answers being typed.
watch(
  () => props.gap?.accepted_values ?? [],
  (values) => {
    if (sameValues(draftAcceptedValues.value, lastCommitted)) {
      draftAcceptedValues.value = [...values];
      lastCommitted = [...values];
    }
  },
);

// The answer and option rows change the panel height; re-anchor after render.
watch(
  () => props.gap,
  () => {
    void nextTick(() => place());
  },
);

function handleFocusOut(event: FocusEvent): void {
  const next = event.relatedTarget;
  const popover = event.currentTarget as HTMLElement;
  if (next instanceof Node && popover.contains(next)) {
    return;
  }
  answerList.value?.commit();
  commitOptionDrafts();
  emit("close", false);
}

function handleRemoveAutomaticValue(value: string): void {
  emit("removeAutomaticValue", itemId, gapId, value);
  // The chip and its button disappear; keep keyboard focus in the popover.
  void nextTick(() => answerList.value?.focusFirst());
}

function handleShowAsText(): void {
  if (showAsTextDisabledReason.value !== null) {
    return;
  }
  // Persist pending edits first, so the first current accepted value is shown.
  answerList.value?.commit();
  // The gap disappears with this conversion; later focusout/change events
  // must not write the removed gap's answers back.
  discarded = true;
  emit("showGapAsText", itemId, gapId);
}

// Typed option text by option id, until a commit or a structural edit carries it.
const optionDrafts = reactive<Record<string, string>>({});
const options = computed(() => props.gap?.options ?? []);
// A gap with no correct option stays that way until the teacher picks a radio.
const correctOptionId = computed<string | null>(() => props.gap?.correct_option_id ?? null);
const hasCorrectOption = computed(() =>
  options.value.some((option) => option.choice_id === correctOptionId.value),
);

function optionText(option: NativeExamChoice): string {
  return optionDrafts[option.choice_id] ?? bodyText(option.body);
}

function optionLabel(option: NativeExamChoice, index: number): string {
  return optionText(option) || `Alternativ ${index + 1}`;
}

/** The stored options with typed text applied; untouched options keep their identity. */
function optionsWithDrafts(): NativeExamChoice[] {
  return options.value.map((option) => {
    const typed = optionDrafts[option.choice_id];
    return typed === undefined || typed === bodyText(option.body)
      ? option
      : { ...option, body: plainBody(typed.length > 0 ? typed : " ") };
  });
}

function emitOptions(next: NativeExamChoice[], correct: string | null): void {
  for (const key of Object.keys(optionDrafts)) {
    delete optionDrafts[key];
  }
  emit("updateOptions", itemId, gapId, next, correct);
}

function commitOptionDrafts(): void {
  if (discarded || Object.keys(optionDrafts).length === 0) {
    return;
  }
  const next = optionsWithDrafts();
  if (next.every((option, index) => option === options.value[index])) {
    for (const key of Object.keys(optionDrafts)) {
      delete optionDrafts[key];
    }
    return;
  }
  emitOptions(next, correctOptionId.value);
}

function handleOptionInput(choiceId: string, event: Event): void {
  const target = event.target;
  if (target instanceof HTMLInputElement) {
    optionDrafts[choiceId] = target.value;
  }
}

function handleOptionEnter(event: KeyboardEvent): void {
  if (event.isComposing || event.keyCode === 229 || event.key !== "Enter") {
    return;
  }
  event.preventDefault();
  commitOptionDrafts();
  emit("close", true);
}

function handleRootKeydown(event: KeyboardEvent): void {
  if (event.isComposing || event.keyCode === 229 || event.key !== "Escape") {
    return;
  }
  event.preventDefault();
  discarded = true;
  for (const key of Object.keys(optionDrafts)) {
    delete optionDrafts[key];
  }
  emit("close", true);
}

function optionInput(choiceId: string): HTMLInputElement | null {
  return root.value?.querySelector<HTMLInputElement>(
    `[data-test="exam-workspace-gap-option-text-${choiceId}"]`,
  ) ?? null;
}

function handleSelectCorrect(choiceId: string): void {
  emitOptions(optionsWithDrafts(), choiceId);
}

function nextOptionId(): string {
  const used = new Set(options.value.map((option) => option.choice_id));
  for (let number = 1; ; number += 1) {
    const candidate = `choice_${String(number).padStart(3, "0")}`;
    if (!used.has(candidate)) {
      return candidate;
    }
  }
}

function handleAddOption(): void {
  const choiceId = nextOptionId();
  emitOptions([...optionsWithDrafts(), { body: plainBody(" "), choice_id: choiceId }], correctOptionId.value);
  void nextTick(() => optionInput(choiceId)?.focus());
}

function handleRemoveOption(choiceId: string): void {
  if (choiceId === correctOptionId.value) {
    return;
  }
  emitOptions(
    optionsWithDrafts().filter((option) => option.choice_id !== choiceId),
    correctOptionId.value,
  );
  // The row and its button disappear; keep keyboard focus in the popover.
  void nextTick(() => root.value?.querySelector<HTMLElement>('[data-test="exam-workspace-gap-option-add"]')?.focus());
}

function handleMoveOption(index: number, step: -1 | 1): void {
  const next = optionsWithDrafts();
  const target = index + step;
  if (target < 0 || target >= next.length) {
    return;
  }
  const moved = next[index];
  next[index] = next[target];
  next[target] = moved;
  emitOptions(next, correctOptionId.value);
  // The clicked button moves with the row or becomes disabled; the text stays put.
  void nextTick(() => optionInput(moved.choice_id)?.focus());
}

onMounted(() => {
  if (props.dropdown) {
    const target = options.value.find((option) => bodyText(option.body) === "") ?? options.value[0];
    if (target) {
      optionInput(target.choice_id)?.focus();
    }
    return;
  }
  answerList.value?.focusFirst();
  const focused = document.activeElement;
  if (focused instanceof HTMLInputElement) {
    focused.select();
  }
});
</script>

<template>
  <Teleport to="body">
    <div
      ref="root"
      class="fixed z-30 grid w-[min(28rem,calc(100vw-16px))] gap-2 overflow-y-auto border border-navy bg-modal p-3 shadow-[var(--huleedu-shadow-md)]"
      :style="{ top: `${position.top}px`, left: `${position.left}px`, maxHeight: `${position.maxHeight}px` }"
      role="dialog"
      :aria-label="dropdown ? `Alternativ för lucka ${gapNumber}` : `Godkända svar för lucka ${gapNumber}`"
      data-test="exam-workspace-gap-popover"
      @focusout="handleFocusOut"
      @keydown="handleRootKeydown"
    >
      <div
        v-if="dropdown"
        class="grid min-w-0 gap-1.5"
        role="group"
        :aria-labelledby="optionsLabelId"
        data-test="exam-workspace-gap-options"
      >
        <p
          :id="optionsLabelId"
          class="text-xs font-semibold text-navy/80"
        >
          Lucka {{ gapNumber }} – alternativ i rullistan
        </p>
        <div
          v-for="(option, index) in options"
          :key="option.choice_id"
          class="flex min-w-0 items-center gap-1"
          :data-test="`exam-workspace-gap-option-${option.choice_id}`"
        >
          <input
            type="radio"
            class="h-4 w-4 shrink-0"
            :name="`gap-correct-${gapId}`"
            :checked="option.choice_id === correctOptionId"
            :aria-label="`Rätt svar: ${optionLabel(option, index)}`"
            :data-test="`exam-workspace-gap-option-correct-${option.choice_id}`"
            @change="handleSelectCorrect(option.choice_id)"
          >
          <input
            class="min-h-10 min-w-0 flex-1 border border-navy/35 bg-canvas px-3 text-sm font-normal text-navy"
            type="text"
            :value="optionText(option)"
            :aria-label="`Alternativ ${index + 1}`"
            :data-test="`exam-workspace-gap-option-text-${option.choice_id}`"
            @input="handleOptionInput(option.choice_id, $event)"
            @change="commitOptionDrafts"
            @keydown="handleOptionEnter"
          >
          <button
            type="button"
            class="xw-rm"
            :disabled="index === 0"
            aria-label="Flytta upp"
            title="Flytta upp"
            :data-test="`exam-workspace-gap-option-up-${option.choice_id}`"
            @click="handleMoveOption(index, -1)"
          >
            <UiGlyph
              meaning="move-up"
              :size="16"
            />
          </button>
          <button
            type="button"
            class="xw-rm"
            :disabled="index === options.length - 1"
            aria-label="Flytta ned"
            title="Flytta ned"
            :data-test="`exam-workspace-gap-option-down-${option.choice_id}`"
            @click="handleMoveOption(index, 1)"
          >
            <UiGlyph
              meaning="move-down"
              :size="16"
            />
          </button>
          <button
            type="button"
            class="xw-rm"
            :disabled="option.choice_id === correctOptionId"
            :aria-describedby="option.choice_id === correctOptionId ? removeHintId : undefined"
            aria-label="Ta bort alternativet"
            title="Ta bort alternativet"
            :data-test="`exam-workspace-gap-option-remove-${option.choice_id}`"
            @click="handleRemoveOption(option.choice_id)"
          >
            <UiGlyph
              meaning="delete"
              :size="16"
            />
          </button>
        </div>
        <p
          v-if="hasCorrectOption"
          :id="removeHintId"
          class="text-[11px] leading-snug text-navy/65"
          data-test="exam-workspace-gap-option-remove-hint"
        >
          {{ REMOVE_CORRECT_COPY }}
        </p>
        <button
          type="button"
          class="btn-ghost justify-center shadow-none"
          aria-label="Lägg till alternativ"
          title="Lägg till alternativ"
          data-test="exam-workspace-gap-option-add"
          @click="handleAddOption"
        >
          <UiGlyph
            meaning="add"
            :size="16"
          />
        </button>
      </div>

      <div
        v-if="!dropdown"
        class="grid min-w-0 gap-1.5"
      >
        <p class="text-xs font-semibold text-navy/80">
          Lucka {{ gapNumber }} – godkända svar
        </p>
        <ExamWorkspaceGapAnswerList
          ref="answerList"
          :values="gap?.accepted_values ?? []"
          :label="`Godkända svar för lucka ${gapNumber}`"
          :test-id="`exam-workspace-gap-values-${gapId}`"
          @commit="handleAnswersCommit"
          @draft="handleAnswersDraft"
        />
      </div>

      <ExamWorkspaceGapAutomaticValues
        v-if="!dropdown && automaticValues.length > 0"
        :values="automaticValues"
        @remove="handleRemoveAutomaticValue"
      />

      <button
        v-if="!dropdown"
        type="button"
        class="btn-ghost justify-center shadow-none"
        :disabled="showAsTextDisabledReason !== null"
        :aria-describedby="showAsTextDisabledReason !== null ? showAsTextExplanationId : undefined"
        data-test="exam-workspace-gap-as-text"
        @click="handleShowAsText"
      >
        Visa som text
      </button>
      <p
        v-if="!dropdown && showAsTextDisabledReason"
        :id="showAsTextExplanationId"
        class="text-[11px] leading-snug text-navy/65"
        data-test="exam-workspace-gap-as-text-disabled"
      >
        {{ showAsTextDisabledReason }}
      </p>
    </div>
  </Teleport>
</template>
