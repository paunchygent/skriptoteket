<script setup lang="ts">
/**
 * The exam workspace's editor column (TASK-SKRIPT-40-04-03).
 *
 * Domain purpose:
 *   Show the editor for what the teacher selected: the exam instruction, an
 *   instruction with its deluppgifter, a question, or the empty state when no exam is open.
 *
 * Relationships:
 *   - Edits through the `editing` composable result, whose `structure`
 *     commands it also calls; the selection and presentation state arrive
 *     as props from `ExamWorkspaceView`, which owns them.
 */

import { computed } from "vue";

import type { NativeExamDocument } from "../../../api/examWorkspace";
import type { TeacherItemKind } from "./examWorkspaceItemEdits";
import { examWorkspaceQuestionLabels } from "./examWorkspaceListEntries";
import type { ExamWorkspaceItemEntry, ExamWorkspaceListEntry, ExamWorkspaceParentEntry } from "./examWorkspaceListEntries";
import { freeTextWritingLines, type FreeTextWritingLines } from "./examWorkspaceWritingLines";
import ExamWorkspaceExamInstructionEditor from "./ExamWorkspaceExamInstructionEditor.vue";
import ExamWorkspaceInstructionEditor from "./ExamWorkspaceInstructionEditor.vue";
import ExamWorkspaceQuestionEditor from "./ExamWorkspaceQuestionEditor.vue";
import type { useExamWorkspaceEditing } from "./useExamWorkspaceEditing";
import type { ExamWorkspaceNotice } from "./useExamWorkspaceStructure";

type ExamWorkspaceItem = NativeExamDocument["items"][number];
type ExamWorkspaceParent = NativeExamDocument["parents"][number];

const props = defineProps<{
  editing: ReturnType<typeof useExamWorkspaceEditing>;
  workspaceDocument: NativeExamDocument | null;
  examInstructionsSelected: boolean;
  selectedParent: ExamWorkspaceParent | null;
  selectedParentEntry: ExamWorkspaceParentEntry | null;
  parentChildren: ExamWorkspaceItemEntry[];
  entries: ExamWorkspaceListEntry[];
  selectedItem: ExamWorkspaceItem | null;
  itemEntry: ExamWorkspaceItemEntry | null;
  itemParent: { id: string; label: string; text: string } | null;
  itemChild: { index: number; count: number } | null;
  itemNotice: ExamWorkspaceNotice | null;
  converting: boolean;
  disabled: boolean;
  importOpen: boolean;
  openDrawerShown: boolean;
}>();

defineEmits<{
  "open-drawer": [];
  select: [id: string];
  "add-child": [kind: TeacherItemKind];
  "move-selected": [delta: -1 | 1];
  "toggle-import": [];
  "toggle-reviewed": [];
  "dismiss-item-notice": [];
}>();

const { structure, assetUrls } = props.editing;

/** Every free-text question with its display label and writing-line count, for the Skrivyta popover. */
const freeTextWritingLinesSummary = computed<FreeTextWritingLines[]>(() =>
  props.workspaceDocument
    ? freeTextWritingLines(props.workspaceDocument, examWorkspaceQuestionLabels(props.workspaceDocument))
    : [],
);

/** The display label of one part in the Flytta till list. */
function moveTargetLabel(entry: ExamWorkspaceParentEntry): string {
  const excerpt = entry.text || "Tom instruktion";
  return entry.label ? `${entry.label} · ${excerpt}` : `Instruktion · ${excerpt}`;
}

/**
 * The places Flytta till offers, in list order: every part with its list label
 * and instruction excerpt (G3).
 */
const moveTargets = computed<{ id: string; label: string }[]>(() =>
  props.entries
    .filter((entry): entry is ExamWorkspaceParentEntry => entry.kind === "parent")
    .map((entry) => ({ id: entry.id, label: moveTargetLabel(entry) })),
);

/** The part the selected question sits in; null when it is standalone. */
const currentParentId = computed(() => props.itemEntry?.parentId ?? null);
</script>

<template>
  <div
    class="ws__editor"
    data-test="exam-workspace-workspace"
  >
    <div
      v-if="!workspaceDocument"
      class="ws__empty"
      data-test="exam-workspace-empty"
    >
      <h2>Inget prov öppet</h2>
      <p>Skapa ett nytt prov, öppna ett sparat prov eller importera från Word eller DigiExam.</p>
      <button
        v-if="!openDrawerShown"
        type="button"
        class="xw-btn"
        data-test="exam-workspace-empty-open"
        @click="$emit('open-drawer')"
      >
        Öppna
      </button>
    </div>
    <div
      v-else
      class="ws__in"
    >
      <ExamWorkspaceExamInstructionEditor
        v-if="examInstructionsSelected"
        :instructions="workspaceDocument.instructions"
        :disabled="disabled"
        :asset-urls="assetUrls"
        @update-instructions="editing.setExamInstructions"
      />
      <ExamWorkspaceInstructionEditor
        v-else-if="selectedParent && selectedParentEntry"
        :parent="selectedParent"
        :label="selectedParentEntry.label"
        :children="parentChildren"
        :subtotal="selectedParentEntry.points"
        :disabled="disabled"
        :notice="structure.deleteNotice.value"
        :asset-urls="assetUrls"
        @update-instruction="(body, structural) => editing.setParentInstruction(selectedParent!.parent_id, body, structural)"
        @goto-child="$emit('select', $event)"
        @move-child="(itemId, delta) => structure.moveChild(selectedParent!.parent_id, itemId, delta)"
        @delete-child="structure.deleteItem"
        @add-child="(kind) => $emit('add-child', kind)"
        @delete-parent="(mode) => structure.deleteParent(selectedParent!.parent_id, mode)"
        @dismiss-notice="structure.dismissDeleteNotice"
      />
      <ExamWorkspaceQuestionEditor
        v-else-if="selectedItem && itemEntry"
        :item="selectedItem"
        :label="itemEntry.label"
        :origin="workspaceDocument.origin.kind"
        :parent="itemParent"
        :child="itemChild"
        :converting="converting"
        :disabled="disabled"
        :notice="itemNotice"
        :import-open="importOpen"
        :move-targets="moveTargets"
        :current-parent-id="currentParentId"
        :asset-urls="assetUrls"
        :free-text-writing-lines="freeTextWritingLinesSummary"
        @change-type="(kind) => structure.changeType(selectedItem!.item_id, kind)"
        @change-shape="(shape) => editing.changeItemShape(selectedItem!.item_id, shape)"
        @move="(delta) => $emit('move-selected', delta)"
        @remove="structure.deleteItem(selectedItem!.item_id)"
        @move-to="(targetParentId) => structure.moveItem(selectedItem!.item_id, targetParentId)"
        @toggle-import="$emit('toggle-import')"
        @toggle-reviewed="$emit('toggle-reviewed')"
        @retry="(kind) => editing.retryItem(selectedItem!.item_id, kind)"
        @goto-parent="$emit('select', $event)"
        @dismiss-notice="$emit('dismiss-item-notice')"
        @undo-interpretation="editing.undoItemInterpretation"
        @remove-automatic-value="editing.removeItemAutomaticValue"
        @create-gap="editing.createItemGap"
        @show-gap-as-text="editing.showItemGapAsText"
        @revert-gap="editing.revertItemGap"
        @restore-kept-gap="editing.restoreItemKeptGap"
        @add-ordering-step="editing.addItemOrderingStep"
        @move-ordering-step="editing.moveItemOrderingStep"
        @remove-ordering-step="editing.removeItemOrderingStep"
        @shuffle-ordering-steps="editing.shuffleItemOrderingSteps"
        @update-choice-body="editing.updateItemChoiceBody"
        @update-correct-choices="editing.updateItemCorrectChoices"
        @update-criteria="editing.updateItemCriteria"
        @update-gap-values="editing.updateItemGapValues"
        @update-gap-options="editing.updateItemGapOptions"
        @update-match-entry-body="editing.updateItemMatchEntryBody"
        @update-match-pairs="editing.updateItemMatchPairs"
        @update-body="editing.updateItemBody"
        @update-points="editing.updateItemPoints"
        @update-tick-points="editing.updateItemTickPoints"
        @update-writing-lines="editing.updateItemWritingLines"
        @apply-writing-lines-to-all="editing.applyWritingLinesToAllFreeText"
      />
      <p
        v-else
        class="xw-muted"
      >
        Välj en fråga i listan.
      </p>
    </div>
  </div>
</template>

<style scoped>
.ws__editor { min-width: 0; min-height: 0; overflow-y: auto; }
.ws__in { max-width: var(--xw-editor-measure); margin: 0 auto; padding: var(--huleedu-space-6) var(--huleedu-space-8) var(--huleedu-space-12); }
.ws__empty {
  height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: var(--huleedu-space-2);
  padding: var(--huleedu-space-8); text-align: center; color: var(--huleedu-navy-70);
}
.ws__empty h2 { margin: 0; font-size: var(--huleedu-text-xl); color: var(--huleedu-navy); }
.ws__empty p { max-width: 360px; margin: 0 0 var(--huleedu-space-4); font-size: var(--huleedu-text-sm); }
@media (max-width: 1279px) {
  .ws__in { padding: var(--huleedu-space-4) var(--huleedu-space-5) var(--huleedu-space-12); }
}
@media (min-width: 1280px) {
  /* Below its minimum the editor keeps its minimum layout and scrolls inside itself. */
  .ws__editor { overflow-x: auto; }
  .ws__in { min-width: var(--xw-editor-min); }
}
@media (max-width: 767px) {
  .ws__in { padding: var(--huleedu-space-3) var(--huleedu-space-4) var(--huleedu-space-12); }
}
</style>
