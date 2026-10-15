<script setup lang="ts">
/**
 * Exam workspace responsive editor pane.
 *
 * Domain purpose:
 *   Arrange the Redigera surface for the current layout: on desktop and
 *   tablet the question list sits beside the dominating item editor, on phones
 *   the editor is the whole screen. The question details drawer docks beside
 *   the editor on desktop and overlays it on tablet and phone. The pane shows
 *   the selected question's save readiness and export blockers in the
 *   drawer and the attention count on the editor.
 *   A selected placeholder whose batch still converts disables its editor and
 *   drawer; the question list stays usable.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceView` for the open document in Redigera mode.
 *   - Receives the layout from `useExamWorkspaceLayout` through the view and
 *     composes `ExamWorkspaceQuestionList`, `ExamWorkspaceItemTable`,
 *     `ExamWorkspaceItemEditor`, and `ExamWorkspaceItemDrawer`.
 *   - Holds no state: every edit, step, add, and reconversion is emitted to
 *     the view, which owns it through the workspace composables; the open
 *     document's picture URLs are handed down to the item editor, and the
 *     exam's shared instructions are shown once, read-only, above the
 *     question list with the same renderer as a parent's stem.
 */

import { computed } from "vue";

import type {
  NativeExamBodySegment,
  NativeExamCriterion,
  NativeExamItem,
  NativeExamItemKind,
  NativeExamMatchPair,
} from "../../../api/examWorkspace";
import ExamWorkspaceItemDrawer from "./ExamWorkspaceItemDrawer.vue";
import ExamWorkspaceItemEditor from "./ExamWorkspaceItemEditor.vue";
import ExamWorkspaceItemTable from "./ExamWorkspaceItemTable.vue";
import ExamWorkspaceQuestionList from "./ExamWorkspaceQuestionList.vue";
import ExamWorkspaceSharedInstruction from "./ExamWorkspaceSharedInstruction.vue";
import type { TeacherItemKind } from "./examWorkspaceItemEdits";
import type { ExamWorkspaceSharedParagraph } from "./examWorkspaceSharedInstruction";
import type { ExamWorkspaceItemRow } from "./examWorkspaceRows";
import type { ExamWorkspaceLayout } from "./useExamWorkspaceLayout";

const props = defineProps<{
  /** Asset URL per asset id, handed down to the question-text editor. */
  assetUrls?: Record<string, string>;
  detailsOpen: boolean;
  disabled: boolean;
  exportBlockersByItemId: Record<string, string[]>;
  /** The exam's shared instructions, already resolved for read-only display. */
  globalInstructions: ExamWorkspaceSharedParagraph[];
  itemCount: number;
  itemRows: ExamWorkspaceItemRow[];
  layout: ExamWorkspaceLayout;
  readinessByItemId: Record<string, string[]>;
  selectedItem: NativeExamItem | null;
  selectedItemId: string | null;
  /** The selected item is a placeholder whose batch still converts; its editor and drawer are disabled. */
  selectedItemLocked: boolean;
  selectedPosition: number;
}>();

const emit = defineEmits<{
  add: [kind: TeacherItemKind];
  markReviewed: [itemId: string];
  undoInterpretation: [itemId: string];
  removeAutomaticValue: [itemId: string, gapId: string, value: string];
  showGapAsText: [itemId: string, gapId: string];
  retry: [itemId: string, kind: NativeExamItemKind];
  select: [itemId: string];
  step: [offset: number];
  "update:detailsOpen": [open: boolean];
  updateChoiceText: [itemId: string, choiceId: string, text: string];
  updateCorrectChoices: [itemId: string, correctChoiceIds: string[]];
  updateCriteria: [itemId: string, criteria: NativeExamCriterion[]];
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
      @add="emit('add', $event)"
    >
      <ExamWorkspaceSharedInstruction
        v-if="globalInstructions.length > 0"
        :paragraphs="globalInstructions"
        class="border-b border-navy/15 bg-canvas px-3 py-2"
        data-test="exam-workspace-global-instruction"
      />
      <ExamWorkspaceItemTable
        :export-blockers-by-item-id="exportBlockersByItemId"
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
            :asset-urls="assetUrls"
            :attention-count="selectedReadiness.length"
            :details-open="detailsOpen"
            :disabled="disabled || selectedItemLocked"
            :item="selectedItem"
            :parent-child="selectedParentChild"
            :position="selectedPosition"
            :show-navigation="!isPhone"
            :total="itemCount"
            @mark-reviewed="emit('markReviewed', $event)"
            @undo-interpretation="emit('undoInterpretation', $event)"
            @remove-automatic-value="(itemId, gapId, value) => emit('removeAutomaticValue', itemId, gapId, value)"
            @show-gap-as-text="(itemId, gapId) => emit('showGapAsText', itemId, gapId)"
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
            @update-criteria="(itemId, criteria) => emit('updateCriteria', itemId, criteria)"
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
        :disabled="disabled || selectedItemLocked"
        :item="selectedItem"
        :layout="layout"
        :readiness="selectedReadiness"
        :server-blockers="selectedServerBlockers"
        @close="emit('update:detailsOpen', false)"
        @retry="(itemId, kind) => emit('retry', itemId, kind)"
      />
    </div>
  </div>
</template>
