<script setup lang="ts">
/**
 * Exam workspace gap-answer popover.
 *
 * Domain purpose:
 *   Let the teacher edit one gap's accepted answers as a comma-separated
 *   list right next to the gap chip. Enter and leaving the popover commit
 *   the answers; Escape discards them. Each commit is emitted once, even
 *   when the browser also fires `change` while focus returns to the chip.
 *
 * Relationships:
 *   - Opened by `ExamWorkspaceBodyEditor`, which keys it by item and gap so
 *     the ids below never change while it is open.
 *   - Uses `parseAcceptedValues` from `examWorkspaceBodySegments`.
 */

import { onMounted, ref } from "vue";

import type { NativeExamGap } from "../../../api/examWorkspace";
import { parseAcceptedValues } from "./examWorkspaceBodySegments";

const props = defineProps<{
  itemId: string;
  gapId: string;
  gapNumber: number;
  gap: NativeExamGap | null;
  top: number;
  left: number;
}>();

const emit = defineEmits<{
  commit: [itemId: string, gapId: string, acceptedValues: string[]];
  close: [returnFocus: boolean];
}>();

// Captured at open: the popover is keyed by item and gap, so these stay fixed.
const itemId = props.itemId;
const gapId = props.gapId;

const input = ref<HTMLInputElement | null>(null);
let lastCommitted = props.gap?.accepted_values ?? [];
let discarded = false;

function sameValues(left: string[], right: string[]): boolean {
  return left.length === right.length && left.every((value, index) => value === right[index]);
}

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

onMounted(() => {
  input.value?.focus();
  input.value?.select();
});
</script>

<template>
  <div
    class="absolute z-10 grid w-72 max-w-full gap-2 border border-navy bg-panel p-3 shadow-[4px_4px_0_0_rgba(0,0,0,0.15)]"
    :style="{ top: `${top}px`, left: `${left}px` }"
    role="dialog"
    :aria-label="`Godkända svar för lucka ${gapNumber}`"
    data-test="exam-workspace-gap-popover"
    @focusout="handleFocusOut"
  >
    <label class="grid gap-1 text-xs font-semibold text-navy/80">
      Lucka {{ gapNumber }} – godkända svar (kommaseparerade)
      <input
        ref="input"
        class="min-h-10 w-full border border-navy/35 bg-canvas px-3 text-sm font-normal text-navy"
        type="text"
        :value="gap?.accepted_values.join(', ') ?? ''"
        :data-test="`exam-workspace-gap-values-${gapId}`"
        @change="commit"
        @keydown="handleKeydown"
      >
    </label>
    <span
      v-if="gap?.hint"
      class="text-[11px] leading-snug text-navy/65"
    >
      Ledtråd: {{ gap.hint }}
    </span>
  </div>
</template>
