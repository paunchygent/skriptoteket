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
 * Relationships:
 *   - Opened by `ExamWorkspaceBodyEditor`, which keys it by item and gap so
 *     the ids below never change while it is open.
 *   - Uses `parseAcceptedValues` from `examWorkspaceBodySegments`.
 */

import { computed, nextTick, onMounted, ref, useId, watch } from "vue";

import type { NativeExamGap } from "../../../api/examWorkspace";
import { IconX } from "../../../components/icons";
import { parseAcceptedValues } from "./examWorkspaceBodySegments";

const LAST_GAP_COPY = "Frågan måste behålla minst en lucka.";
const MISSING_ANSWER_COPY = "Fyll i ett godkänt svar först.";

const props = defineProps<{
  itemId: string;
  gapId: string;
  gapNumber: number;
  gap: NativeExamGap | null;
  gapCount: number;
  top: number;
  left: number;
}>();

const emit = defineEmits<{
  commit: [itemId: string, gapId: string, acceptedValues: string[]];
  removeAutomaticValue: [itemId: string, gapId: string, value: string];
  showGapAsText: [itemId: string, gapId: string];
  close: [returnFocus: boolean];
}>();

// Captured at open: the popover is keyed by item and gap, so these stay fixed.
const itemId = props.itemId;
const gapId = props.gapId;

const input = ref<HTMLInputElement | null>(null);
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
  input.value?.focus();
  input.value?.select();
});
</script>

<template>
  <div
    class="absolute z-10 grid w-[min(28rem,100%)] gap-2 border border-navy bg-modal p-3 shadow-[var(--huleedu-shadow-md)]"
    :style="{ top: `${top}px`, left: `${left}px` }"
    role="dialog"
    :aria-label="`Godkända svar för lucka ${gapNumber}`"
    data-test="exam-workspace-gap-popover"
    @focusout="handleFocusOut"
  >
    <label class="grid min-w-0 gap-1 text-xs font-semibold text-navy/80">
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
      v-if="automaticValues.length > 0"
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
      v-if="showAsTextDisabledReason"
      :id="showAsTextExplanationId"
      class="text-[11px] leading-snug text-navy/65"
      data-test="exam-workspace-gap-as-text-disabled"
    >
      {{ showAsTextDisabledReason }}
    </p>
  </div>
</template>
