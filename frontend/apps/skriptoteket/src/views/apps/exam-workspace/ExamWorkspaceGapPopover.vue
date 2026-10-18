<script setup lang="ts">
/**
 * Exam workspace gap-answer popover.
 *
 * Domain purpose:
 *   Let the teacher edit one gap's accepted answers as a comma-separated
 *   list right next to the gap chip. Enter and leaving the popover commit
 *   the answers; Escape discards them. Each commit is emitted once, even
 *   when the browser also fires `change` while focus returns to the chip.
 *   Enter and Escape pressed while an IME composition is active belong to
 *   the composition and are ignored. Answers the conversion wrote for the
 *   gap (automatic misspellings) show as removable chips marked
 *   "automatisk" with no AI glyph. "Visa som text" replaces the gap with
 *   its first accepted answer as plain text; it is disabled with a visible
 *   explanation on the item's last gap or while the answers field (including
 *   unsaved typing) holds no accepted answer.
 *
 *   A dropdown gap (`dropdown`) edits its options instead: one row per
 *   option with a radio for the correct one, an editable text, move up/down
 *   and remove, plus "Lägg till alternativ". Radio, add, remove and move emit
 *   the whole option state at once (one patch each); typed option text
 *   commits on `change`, Enter and leaving the popover, and rides along with
 *   the next such emit. Escape discards typed text. The correct option
 *   cannot be removed. The accepted answers, automatic answers and "Visa som
 *   text" do not apply to a dropdown gap and are hidden.
 *
 * Relationships:
 *   - Opened by `ExamWorkspaceBodyEditor`, which keys it by item and gap so
 *     the ids below never change while it is open.
 *   - Uses `parseAcceptedValues` from `examWorkspaceBodySegments`.
 */

import { computed, nextTick, onMounted, reactive, ref, useId, watch } from "vue";

import type { NativeExamChoice, NativeExamGap } from "../../../api/examWorkspace";
import { IconX } from "../../../components/icons";
import { UiGlyph } from "../../../components/ui";
import { parseAcceptedValues } from "./examWorkspaceBodySegments";
import { bodyText, plainBody } from "./examWorkspaceRichText";

const LAST_GAP_COPY = "Frågan måste behålla minst en lucka.";
const MISSING_ANSWER_COPY = "Fyll i ett godkänt svar först.";
const REMOVE_CORRECT_COPY = "Markera ett annat alternativ som rätt först";

const props = defineProps<{
  itemId: string;
  gapId: string;
  gapNumber: number;
  gap: NativeExamGap | null;
  gapCount: number;
  dropdown?: boolean;
  top: number;
  left: number;
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
const input = ref<HTMLInputElement | null>(null);
const removeHintId = useId();
const optionsLabelId = useId();
const showAsTextExplanationId = useId();
const automaticValues = computed(() => props.gap?.automatic_values ?? []);
// Pending answers as typed; the saved gap only changes when a commit lands.
const draft = ref(props.gap?.accepted_values.join(", ") ?? "");
const draftAcceptedValues = computed(() => parseAcceptedValues(draft.value));
const showAsTextDisabledReason = computed(() => {
  if (props.gapCount <= 1) {
    return LAST_GAP_COPY;
  }
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

function handleInput(event: Event): void {
  const target = event.target;
  if (target instanceof HTMLInputElement) {
    draft.value = target.value;
  }
}

// Follow an externally changed gap, but never clobber answers being typed.
watch(
  () => props.gap?.accepted_values ?? [],
  (values) => {
    if (sameValues(draftAcceptedValues.value, lastCommitted)) {
      draft.value = values.join(", ");
      lastCommitted = values;
    }
  },
);

function commit(): void {
  if (discarded || !input.value) {
    return;
  }
  const values = parseAcceptedValues(input.value.value);
  if (sameValues(values, lastCommitted)) {
    return;
  }
  lastCommitted = values;
  emit("commit", itemId, gapId, values);
}

// Typed option text by option id, until a commit or a structural edit carries it.
const optionDrafts = reactive<Record<string, string>>({});
const options = computed(() => props.gap?.options ?? []);
const correctOptionId = computed(
  () => props.gap?.correct_option_id ?? options.value[0]?.choice_id ?? "",
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
  if (!props.dropdown || event.isComposing || event.keyCode === 229 || event.key !== "Escape") {
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

function handleKeydown(event: KeyboardEvent): void {
  if (event.isComposing || event.keyCode === 229) {
    return;
  }
  if (event.key === "Escape") {
    event.preventDefault();
    discarded = true;
    emit("close", true);
  } else if (event.key === "Enter") {
    event.preventDefault();
    commit();
    emit("close", true);
  }
}

function handleFocusOut(event: FocusEvent): void {
  const next = event.relatedTarget;
  const popover = event.currentTarget as HTMLElement;
  if (next instanceof Node && popover.contains(next)) {
    return;
  }
  commit();
  commitOptionDrafts();
  emit("close", false);
}

function handleRemoveAutomaticValue(value: string): void {
  emit("removeAutomaticValue", itemId, gapId, value);
  // The chip and its button disappear; keep keyboard focus in the popover.
  void nextTick(() => input.value?.focus());
}

function handleShowAsText(): void {
  if (showAsTextDisabledReason.value !== null) {
    return;
  }
  // Persist pending edits first, so the first current accepted value is shown.
  commit();
  // The gap disappears with this conversion; later focusout/change events
  // must not write the removed gap's answers back.
  discarded = true;
  emit("showGapAsText", itemId, gapId);
}

onMounted(() => {
  if (props.dropdown) {
    const target = options.value.find((option) => bodyText(option.body) === "") ?? options.value[0];
    if (target) {
      optionInput(target.choice_id)?.focus();
    }
    return;
  }
  input.value?.focus();
  input.value?.select();
});
</script>

<template>
  <div
    ref="root"
    class="absolute z-10 grid w-[min(28rem,100%)] gap-2 border border-navy bg-modal p-3 shadow-[var(--huleedu-shadow-md)]"
    :style="{ top: `${top}px`, left: `${left}px` }"
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
        :id="removeHintId"
        class="text-[11px] leading-snug text-navy/65"
        data-test="exam-workspace-gap-option-remove-hint"
      >
        {{ REMOVE_CORRECT_COPY }}
      </p>
      <button
        type="button"
        class="btn-ghost justify-center shadow-none"
        data-test="exam-workspace-gap-option-add"
        @click="handleAddOption"
      >
        Lägg till alternativ
      </button>
    </div>

    <label
      v-if="!dropdown"
      class="grid min-w-0 gap-1 text-xs font-semibold text-navy/80"
    >
      Lucka {{ gapNumber }} – godkända svar (kommaseparerade)
      <input
        ref="input"
        class="min-h-10 w-full border border-navy/35 bg-canvas px-3 text-sm font-normal text-navy"
        type="text"
        :value="draft"
        :data-test="`exam-workspace-gap-values-${gapId}`"
        @input="handleInput"
        @change="commit"
        @keydown="handleKeydown"
      >
    </label>

    <div
      v-if="!dropdown && automaticValues.length > 0"
      class="grid min-w-0 gap-1.5"
      data-test="exam-workspace-gap-automatic-values"
    >
      <p class="text-[11px] font-semibold leading-snug text-navy/80">
        Automatiska svar
      </p>
      <ul class="flex flex-wrap gap-1.5">
        <li
          v-for="value in automaticValues"
          :key="value"
          class="inline-flex min-h-7 items-center gap-1.5 border border-navy/35 bg-panel-muted px-2 text-xs text-navy"
          :data-test="`exam-workspace-gap-automatic-${value}`"
          :data-value="value"
        >
          <span class="font-semibold">{{ value }}</span>
          <span class="text-[11px] leading-none text-navy/65">automatisk</span>
          <button
            type="button"
            class="inline-flex h-11 w-11 shrink-0 items-center justify-center border border-navy/35 bg-panel text-navy hover:bg-canvas focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action/40 sm:h-7 sm:w-7"
            :aria-label="`Ta bort automatisk stavning: ${value}`"
            :title="`Ta bort automatisk stavning: ${value}`"
            :data-test="`exam-workspace-gap-automatic-remove-${value}`"
            @click="handleRemoveAutomaticValue(value)"
          >
            <IconX :size="14" />
          </button>
        </li>
      </ul>
    </div>

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
</template>
