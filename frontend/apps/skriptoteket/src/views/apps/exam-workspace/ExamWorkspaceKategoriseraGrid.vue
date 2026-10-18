<script setup lang="ts">
/**
 * Exam workspace Kategorisera grid.
 *
 * Domain purpose:
 *   Edit a matching item as the Exam.net Kategorisera grid (Q7–Q9): the row
 *   texts, the column (category) texts, and the correct ticks, where a row
 *   has one or more correct columns and a column may serve several rows or
 *   none. Row and category texts are rich entries on the shared editor, so
 *   the marks the source gave them show and toggle. An emptied text still
 *   saves; empty bodies and an incomplete key are marked with the Swedish
 *   guidance the export blocker uses.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceQuestionEditor` for matching items; the tick
 *     value and the derived points sit in the editor's points row.
 *   - Emits typed update events; `useExamWorkspaceDocument` owns the state.
 *   - Reads the rules from `examWorkspaceAnswerKeyRules`,
 *     `examWorkspaceItemSaveRules` and `examWorkspaceRichText`.
 */

import { useId } from "vue";

import type { NativeExamBodyParagraph, NativeExamItem, NativeExamMatchPair } from "../../../api/examWorkspace";
import ExamWorkspaceRichTextEntry from "./ExamWorkspaceRichTextEntry.vue";
import {
  INCOMPLETE_MATCH_KEY_GUIDANCE,
  isIncompleteMatchingItem,
} from "./examWorkspaceAnswerKeyRules";
import { EMPTY_MATCH_TEXT_GUIDANCE, hasEmptyMatchText } from "./examWorkspaceItemSaveRules";
import { bodyText } from "./examWorkspaceRichText";
import { isEmptyBody } from "./examWorkspaceRichTextDocument";

const props = defineProps<{
  disabled?: boolean;
  item: NativeExamItem;
}>();

const emit = defineEmits<{
  updateEntryBody: [side: "left" | "right", entryId: string, body: NativeExamBodyParagraph[], structural: boolean];
  updatePairs: [pairs: NativeExamMatchPair[]];
}>();

const textHintId = useId();
const keyHintId = useId();

function isTicked(leftId: string, rightId: string): boolean {
  return props.item.answer_key.match_pairs.some(
    (pair) => pair.left_id === leftId && pair.right_id === rightId,
  );
}

/** Rebuild the full tick list in row and column order, with one cell toggled. */
function handleTick(leftId: string, rightId: string, event: Event): void {
  const checked = (event.target as HTMLInputElement).checked;
  const pairs: NativeExamMatchPair[] = [];
  for (const left of props.item.match_left) {
    for (const right of props.item.match_right) {
      const toggled = left.left_id === leftId && right.right_id === rightId;
      if (toggled ? checked : isTicked(left.left_id, right.right_id)) {
        pairs.push({ left_id: left.left_id, right_id: right.right_id });
      }
    }
  }
  emit("updatePairs", pairs);
}

function entryBorderClass(body: NativeExamBodyParagraph[]): string {
  return isEmptyBody(body) ? "border-warning" : "border-navy/35";
}
</script>

<template>
  <fieldset
    class="grid gap-2"
    data-test="exam-workspace-kategorisera-grid"
  >
    <legend class="mb-2 text-xs font-semibold text-navy/80">
      Kategorisera
    </legend>
    <div class="overflow-x-auto">
      <table class="border-collapse text-sm text-navy">
        <thead>
          <tr>
            <th
              scope="col"
              class="sr-only"
            >
              Rad
            </th>
            <th
              v-for="(right, rightIndex) in item.match_right"
              :key="right.right_id"
              scope="col"
              class="min-w-32 p-1 align-bottom"
            >
              <ExamWorkspaceRichTextEntry
                :key="`${item.item_id}-${right.right_id}`"
                :body="right.body"
                :border-class="entryBorderClass(right.body)"
                :described-by="isEmptyBody(right.body) ? textHintId : undefined"
                :disabled="disabled"
                :invalid="isEmptyBody(right.body)"
                :label="`Text för kategori ${rightIndex + 1}`"
                :test-id="`exam-workspace-match-right-text-${right.right_id}`"
                class="font-semibold"
                @update-body="(body, structural) => emit('updateEntryBody', 'right', right.right_id, body, structural)"
              />
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(left, leftIndex) in item.match_left"
            :key="left.left_id"
            class="border-t border-navy/15"
          >
            <th
              scope="row"
              class="min-w-48 p-1 font-normal"
            >
              <ExamWorkspaceRichTextEntry
                :key="`${item.item_id}-${left.left_id}`"
                :body="left.body"
                :border-class="entryBorderClass(left.body)"
                :described-by="isEmptyBody(left.body) ? textHintId : undefined"
                :disabled="disabled"
                :invalid="isEmptyBody(left.body)"
                :label="`Text för rad ${leftIndex + 1}`"
                :test-id="`exam-workspace-match-left-text-${left.left_id}`"
                @update-body="(body, structural) => emit('updateEntryBody', 'left', left.left_id, body, structural)"
              />
            </th>
            <td
              v-for="right in item.match_right"
              :key="right.right_id"
              class="p-1 text-center"
            >
              <input
                class="h-5 w-5 accent-navy"
                type="checkbox"
                :checked="isTicked(left.left_id, right.right_id)"
                :disabled="disabled"
                :aria-label="`${bodyText(left.body) || `Rad ${leftIndex + 1}`}: ${bodyText(right.body)}`"
                :aria-describedby="isIncompleteMatchingItem(item) ? keyHintId : undefined"
                :data-test="`exam-workspace-match-tick-${left.left_id}-${right.right_id}`"
                @change="handleTick(left.left_id, right.right_id, $event)"
              >
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <p
      v-if="hasEmptyMatchText(item)"
      :id="textHintId"
      class="border-l-4 border-warning pl-2 text-sm leading-snug text-navy"
      data-test="exam-workspace-match-hint"
    >
      {{ EMPTY_MATCH_TEXT_GUIDANCE }}
    </p>
    <p
      v-if="isIncompleteMatchingItem(item)"
      :id="keyHintId"
      class="border-l-4 border-warning pl-2 text-sm leading-snug text-navy"
      data-test="exam-workspace-match-key-hint"
    >
      {{ INCOMPLETE_MATCH_KEY_GUIDANCE }}
    </p>
  </fieldset>
</template>
