<script setup lang="ts">
/**
 * Exam workspace matching editor.
 *
 * Domain purpose:
 *   Edit the two lists of a matching question: numbered left rows with their
 *   own text input and a select for the correct lettered answer, and lettered
 *   right entries with their own text input. A row or answer without text and
 *   an incomplete answer key are marked invalid at the field with a Swedish
 *   hint, because the save refuses them. While `disabled` (a save or load is
 *   running) every control is disabled.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceItemEditor` for matching items only.
 *   - Emits typed update events; `useExamWorkspaceDocument` owns the state
 *     (`updateItemMatchEntryText`, `updateItemMatchPairs`).
 *   - Reads the empty-text guidance from `examWorkspaceItemSaveRules` and the
 *     incomplete-key guidance from `examWorkspaceAnswerKeyRules`.
 */

import { useId } from "vue";

import type { NativeExamItem, NativeExamMatchPair } from "../../../api/examWorkspace";
import {
  INCOMPLETE_MATCH_KEY_GUIDANCE,
  isIncompleteMatchingItem,
} from "./examWorkspaceAnswerKeyRules";
import {
  EMPTY_MATCH_TEXT_GUIDANCE,
  hasEmptyMatchText,
  isEmptyChoiceText,
} from "./examWorkspaceItemSaveRules";

const props = defineProps<{
  item: NativeExamItem;
  disabled?: boolean;
}>();

const emit = defineEmits<{
  updateMatchEntryText: [
    itemId: string,
    side: "left" | "right",
    entryId: string,
    text: string,
  ];
  updateMatchPairs: [itemId: string, pairs: NativeExamMatchPair[]];
}>();

const matchHintId = useId();
const matchKeyHintId = useId();

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
  <fieldset
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
</template>
