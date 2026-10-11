<script setup lang="ts">
/**
 * Exam workspace responsive editor pane.
 *
 * Domain purpose:
 *   Arrange the Redigera surface for the current layout: on desktop and
 *   tablet the question list sits beside the dominating item editor, on phones
 *   the editor is the whole screen. The question details drawer docks beside
 *   the editor on desktop and overlays it on tablet and phone. The pane shows
 *   the selected question's save readiness, export blockers, and waiting
 *   answer-key proposal in the drawer and the attention count on the editor.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceView` for the open document in Redigera mode.
 *   - Receives the layout from `useExamWorkspaceLayout` through the view and
 *     composes `ExamWorkspaceQuestionList`, `ExamWorkspaceItemTable`,
 *     `ExamWorkspaceItemEditor`, and `ExamWorkspaceItemDrawer`.
 *   - Holds no state: every edit, step, add, and proposal decision is emitted
 *     to the view, which owns it through the workspace composables.
 */

import { computed } from "vue";

import type {
  ExamWorkspaceAnswerKeyProposal,
  NativeExamBodySegment,
  NativeExamItem,
  NativeExamMatchPair,
} from "../../../api/examWorkspace";
import ExamWorkspaceItemDrawer from "./ExamWorkspaceItemDrawer.vue";
import ExamWorkspaceItemEditor from "./ExamWorkspaceItemEditor.vue";
import ExamWorkspaceItemTable from "./ExamWorkspaceItemTable.vue";
import ExamWorkspaceQuestionList from "./ExamWorkspaceQuestionList.vue";
import type { ExamWorkspaceItemRow } from "./examWorkspaceRows";
import type { ExamWorkspaceLayout } from "./useExamWorkspaceLayout";

const props = defineProps<{
  detailsOpen: boolean;
  disabled: boolean;
  exportBlockersByItemId: Record<string, string[]>;
  itemCount: number;
  itemRows: ExamWorkspaceItemRow[];
  layout: ExamWorkspaceLayout;
  proposalItemIds: string[];
  readinessByItemId: Record<string, string[]>;
  selectedItem: NativeExamItem | null;
  selectedItemId: string | null;
  selectedPosition: number;
  selectedProposal: ExamWorkspaceAnswerKeyProposal | null;
}>();

const emit = defineEmits<{
  add: [];
  approveProposal: [itemId: string];
  dismissProposal: [itemId: string];
  editProposal: [itemId: string];
  markReviewed: [itemId: string];
  select: [itemId: string];
  step: [offset: number];
  "update:detailsOpen": [open: boolean];
  updateChoiceText: [itemId: string, choiceId: string, text: string];
  updateCorrectChoices: [itemId: string, correctChoiceIds: string[]];
  updateGapValues: [itemId: string, gapId: string, acceptedValues: string[]];
  updateMatchEntryText: [
    itemId: string,
    side: "left" | "right",
    entryId: string,
    text: string,
  ];
  updateMatchPairs: [itemId: string, pairs: NativeExamMatchPair[]];
  updateParagraphSegments: [
    itemId: string,
    paragraphIndex: number,
    segments: NativeExamBodySegment[],
  ];
  updatePoints: [itemId: string, points: number | null];
  updateTitle: [itemId: string, title: string];
}>();

const isPhone = computed(() => props.layout === "phone");

const selectedParentChild = computed(
  () => props.itemRows.find((row) => row.itemId === props.selectedItemId)?.parentChild ?? null,
);

const selectedReadiness = computed(() =>
  props.selectedItem ? (props.readinessByItemId[props.selectedItem.item_id] ?? []) : [],
);

const selectedServerBlockers = computed(() =>
  props.selectedItem ? (props.exportBlockersByItemId[props.selectedItem.item_id] ?? []) : [],
);

const redigeraGridClass = computed(() => {
  if (props.layout === "desktop") {
    return "min-h-0 flex-1 grid-cols-[minmax(15rem,19rem)_minmax(0,1fr)] grid-rows-[minmax(0,1fr)]";
  }
  return props.layout === "tablet"
    ? "min-h-0 flex-1 grid-cols-[minmax(12rem,15rem)_minmax(0,1fr)] grid-rows-[minmax(0,1fr)]"
    : "grid-cols-1";
});
</script>

<template>
  <div
    class="grid min-h-0"
    :class="redigeraGridClass"
  >
    <ExamWorkspaceQuestionList
      v-if="!isPhone"
      :count="itemCount"
      :disabled="disabled"
      @add="emit('add')"
    >
      <ExamWorkspaceItemTable
        :export-blockers-by-item-id="exportBlockersByItemId"
        :proposal-item-ids="proposalItemIds"
        :readiness-by-item-id="readinessByItemId"
        :rows="itemRows"
        :selected-item-id="selectedItemId"
        @select="emit('select', $event)"
      />
    </ExamWorkspaceQuestionList>

    <div class="relative flex min-h-0 min-w-0">
      <div
        class="min-w-0 flex-1"
        :class="isPhone ? undefined : 'min-h-0 overflow-y-auto'"
      >
        <div :class="isPhone ? 'py-4' : 'mx-auto w-full max-w-[60rem] p-6'">
          <ExamWorkspaceItemEditor
            v-if="selectedItem"
            :attention-count="selectedReadiness.length + (selectedProposal ? 1 : 0)"
            :details-open="detailsOpen"
            :disabled="disabled"
            :item="selectedItem"
            :parent-child="selectedParentChild"
            :position="selectedPosition"
            :show-navigation="!isPhone"
            :total="itemCount"
            @mark-reviewed="emit('markReviewed', $event)"
            @next="emit('step', 1)"
            @previous="emit('step', -1)"
            @toggle-details="emit('update:detailsOpen', !detailsOpen)"
            @update-choice-text="
              (itemId, choiceId, text) => emit('updateChoiceText', itemId, choiceId, text)
            "
            @update-correct-choices="
              (itemId, correctChoiceIds) => emit('updateCorrectChoices', itemId, correctChoiceIds)
            "
            @update-gap-values="
              (itemId, gapId, acceptedValues) =>
                emit('updateGapValues', itemId, gapId, acceptedValues)
            "
            @update-match-entry-text="
              (itemId, side, entryId, text) =>
                emit('updateMatchEntryText', itemId, side, entryId, text)
            "
            @update-match-pairs="(itemId, pairs) => emit('updateMatchPairs', itemId, pairs)"
            @update-paragraph-segments="
              (itemId, paragraphIndex, segments) =>
                emit('updateParagraphSegments', itemId, paragraphIndex, segments)
            "
            @update-points="(itemId, points) => emit('updatePoints', itemId, points)"
            @update-title="(itemId, title) => emit('updateTitle', itemId, title)"
          />
          <p
            v-else
            class="text-sm text-navy/65"
          >
            Välj en fråga i listan.
          </p>
        </div>
      </div>
      <ExamWorkspaceItemDrawer
        v-if="detailsOpen && selectedItem"
        :disabled="disabled"
        :item="selectedItem"
        :layout="layout"
        :proposed-item="selectedProposal?.proposed_item ?? null"
        :readiness="selectedReadiness"
        :server-blockers="selectedServerBlockers"
        @approve="emit('approveProposal', $event)"
        @close="emit('update:detailsOpen', false)"
        @dismiss="emit('dismissProposal', $event)"
        @edit="emit('editProposal', $event)"
      />
    </div>
  </div>
</template>
