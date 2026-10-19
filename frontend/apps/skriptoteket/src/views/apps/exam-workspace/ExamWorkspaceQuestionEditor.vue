<script setup lang="ts">
/**
 * Exam workspace question editor.
 *
 * Domain purpose:
 *   Edit the selected question: its header (number, type, Import, the review
 *   check and ⋮), the Import box, the question text, its answers by type, the
 *   key line naming where the answer key came from, and the points. A
 *   deluppgift shows its instruction collapsed above the text, with a way to
 *   edit it. After a type change an inline notice names what the change
 *   removed; the header's Ångra brings it back. Points may be 0; empty points
 *   are marked "Saknas". While the question still converts, the text from the
 *   file shows and nothing can change.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceView` for a selected question.
 *   - Composes `ExamWorkspaceQuestionHead`, `ExamWorkspaceImportBox` and the
 *     existing answer fields (`ExamWorkspaceBodyEditor`,
 *     `ExamWorkspaceShortAnswerField`, `ExamWorkspaceChoiceField`,
 *     `ExamWorkspaceCriteriaField`, `ExamWorkspaceKategoriseraGrid`). A Kort
 *     svar question renders the Kort svar branch (`ExamWorkspaceShortAnswerField`
 *     with only Fråga and Svar) instead of the Frågetext body editor.
 *   - Provides the shared rich-text target registry, so the one formatting
 *     toolbar edits the surface the teacher last selected.
 *   - Holds no document state; every edit is emitted with the item id.
 */

import { computed, ref, useId, watch } from "vue";

import type {
  NativeExamBodyParagraph,
  NativeExamChoice,
  NativeExamCriterion,
  NativeExamDocument,
  NativeExamItem,
  NativeExamItemKind,
  NativeExamMatchPair,
} from "../../../api/examWorkspace";
import { UiGlyph } from "../../../components/ui";
import ExamWorkspaceBodyEditor from "./ExamWorkspaceBodyEditor.vue";
import ExamWorkspaceChoiceField from "./ExamWorkspaceChoiceField.vue";
import ExamWorkspaceCriteriaField from "./ExamWorkspaceCriteriaField.vue";
import ExamWorkspaceImportBox from "./ExamWorkspaceImportBox.vue";
import ExamWorkspaceInlineNotice from "./ExamWorkspaceInlineNotice.vue";
import ExamWorkspaceKategoriseraGrid from "./ExamWorkspaceKategoriseraGrid.vue";
import ExamWorkspaceOrderingField from "./ExamWorkspaceOrderingField.vue";
import ExamWorkspacePointsField from "./ExamWorkspacePointsField.vue";
import ExamWorkspaceQuestionHead from "./ExamWorkspaceQuestionHead.vue";
import ExamWorkspaceQuestionTools from "./ExamWorkspaceQuestionTools.vue";
import ExamWorkspaceShortAnswerField from "./ExamWorkspaceShortAnswerField.vue";
import ExamWorkspaceWritingLinesField from "./ExamWorkspaceWritingLinesField.vue";
import { canUndoInterpretation, isTeacherReviewed } from "./examWorkspaceItemEdits";
import { examWorkspaceItemReadiness } from "./examWorkspaceItemReadiness";
import { examWorkspaceItemTypeLabel } from "./examWorkspaceRows";
import { isShortAnswer } from "./examWorkspaceShortAnswer";
import { provideRichTextTargetRegistry } from "./examWorkspaceRichTextTarget";
import type { ExamWorkspaceNotice } from "./useExamWorkspaceStructure";

/** A type the labeler read with less confidence than this is marked for checking. */
const TYPE_CONFIDENCE_THRESHOLD = 0.95;

const props = withDefaults(
  defineProps<{
    item: NativeExamItem;
    label: string;
    origin: NativeExamDocument["origin"]["kind"];
    /** The instruction above a deluppgift; null for a standalone question. */
    parent: { id: string; label: string; text: string } | null;
    child: { index: number; count: number } | null;
    converting: boolean;
    disabled: boolean;
    /** What the last type change removed, shown until the teacher closes it. */
    /** The last command's inline outcome for this question. */
    notice: ExamWorkspaceNotice | null;
    importOpen: boolean;
    /** The places Flytta till offers, in list order. */
    moveTargets?: { id: string; label: string }[];
    /** The part the question sits in; null when it is standalone. */
    currentParentId?: string | null;
    assetUrls?: Record<string, string>;
    /** The writing-line count every free-text question shares, or null when they differ. */
    allFreeTextWritingLines?: number | null;
  }>(),
  { allFreeTextWritingLines: null, assetUrls: undefined, currentParentId: null, moveTargets: () => [] },
);

provideRichTextTargetRegistry();

const emit = defineEmits<{
  changeType: [kind: NativeExamItemKind];
  move: [delta: -1 | 1];
  remove: [];
  moveTo: [targetParentId: string | null];
  toggleImport: [];
  toggleReviewed: [];
  retry: [kind: NativeExamItemKind];
  gotoParent: [parentId: string];
  dismissNotice: [];
  undoInterpretation: [itemId: string];
  removeAutomaticValue: [itemId: string, gapId: string, value: string];
  createGap: [itemId: string, body: NativeExamBodyParagraph[], gapId: string, seed: string];
  showGapAsText: [itemId: string, gapId: string];
  addOrderingStep: [itemId: string];
  moveOrderingStep: [itemId: string, choiceId: string, delta: -1 | 1];
  removeOrderingStep: [itemId: string, choiceId: string];
  shuffleOrderingSteps: [itemId: string];
  updateChoiceBody: [itemId: string, choiceId: string, body: NativeExamBodyParagraph[], structural: boolean];
  updateCorrectChoices: [itemId: string, correctChoiceIds: string[]];
  updateCriteria: [itemId: string, criteria: NativeExamCriterion[], structural: boolean];
  updateGapValues: [itemId: string, gapId: string, acceptedValues: string[]];
  updateGapOptions: [itemId: string, gapId: string, options: NativeExamChoice[], correctOptionId: string | null, structural: boolean];
  updateMatchEntryBody: [
    itemId: string,
    side: "left" | "right",
    entryId: string,
    body: NativeExamBodyParagraph[],
    structural: boolean,
  ];
  updateMatchPairs: [itemId: string, pairs: NativeExamMatchPair[]];
  updateBody: [itemId: string, body: NativeExamBodyParagraph[], structural: boolean];
  updatePoints: [itemId: string, points: number | null];
  updateTickPoints: [itemId: string, tickPoints: string];
  updateWritingLines: [itemId: string, lines: number];
  applyWritingLinesToAll: [lines: number];
}>();

/** The converting notice's stable id, so the locked fields can point at their reason. */
const convertingNoticeId = useId();
const parentOpen = ref(false);

watch(
  () => props.item.item_id,
  () => {
    parentOpen.value = false;
  },
);

const locked = computed(() => props.disabled || props.converting);
// The same rule as the list and the server's export blocker (`is_unbuilt_question`).
const unbuilt = computed(() => examWorkspaceItemReadiness(props.item).includes("unbuilt_question"));
const reviewed = computed(() => isTeacherReviewed(props.item));
const typeUncertain = computed(
  () => typeof props.item.review.confidence === "number" && props.item.review.confidence < TYPE_CONFIDENCE_THRESHOLD,
);
const isGrid = computed(() => props.item.kind === "matching");
const showFields = computed(() => !props.converting && !unbuilt.value);
/** True when this free-text question already carries the shared writing-line count. */
const allFreeTextWritingLinesMatch = computed(
  () => props.allFreeTextWritingLines === props.item.writing_lines,
);

/** Where the answer key came from, with the key text the file printed. */
const keyLine = computed(() => {
  const facit = props.item.facit_text;
  if (!facit) return null;
  const origin = props.item.answer_key.origin;
  if (origin === "ai_interpreted") return { ai: true, lead: "Facit tolkat av AI ur", facit };
  if (origin === "absent") return { ai: false, lead: "Facit i provfilen:", facit };
  return { ai: false, lead: "Facit ur provfilen:", facit };
});
</script>

<template>
  <section
    class="qed"
    :aria-label="`Redigera fråga ${label}`"
    data-test="exam-workspace-item-editor"
  >
    <ExamWorkspaceQuestionHead
      :label="label"
      :kind="item.kind"
      :type-label="examWorkspaceItemTypeLabel(item, unbuilt)"
      :unbuilt="unbuilt"
      :converting="converting"
      :child="child"
      :disabled="disabled"
      :suggested-kind="item.suggested_kind"
      :move-targets="moveTargets"
      :current-parent-id="currentParentId"
      @change-type="emit('changeType', $event)"
      @move="emit('move', $event)"
      @remove="emit('remove')"
      @move-to="emit('moveTo', $event)"
    >
      <template #tools>
        <ExamWorkspaceQuestionTools
          :has-import="item.import_record !== null"
          :import-open="importOpen"
          :reviewed="reviewed"
          :disabled="locked"
          @toggle-import="emit('toggleImport')"
          @toggle-reviewed="emit('toggleReviewed')"
        />
      </template>
    </ExamWorkspaceQuestionHead>

    <p
      v-if="typeUncertain && !unbuilt"
      class="xw-hint qed__line"
      data-test="exam-workspace-type-uncertain"
    >
      <UiGlyph
        meaning="info"
        :size="16"
      />Kontrollera frågetypen.
    </p>

    <ExamWorkspaceInlineNotice
      v-if="notice"
      :notice="notice"
      @dismiss="emit('dismissNotice')"
    />

    <ExamWorkspaceImportBox
      :item="item"
      :origin="origin"
      :open="importOpen"
      :disabled="locked"
      @retry="emit('retry', $event)"
    />

    <div
      v-if="converting"
      :id="convertingNoticeId"
      class="xw-notice qed__notice"
      data-test="exam-workspace-converting-notice"
    >
      <UiGlyph
        meaning="busy"
        :size="16"
        class="xw-spin"
      /><span>Frågan konverteras fortfarande. Texten från provfilen visas tills den är klar och går inte att ändra under tiden.</span>
    </div>

    <div
      v-if="parent"
      class="pref"
      data-test="exam-workspace-parent-ref"
    >
      <button
        type="button"
        class="pref__head"
        :aria-expanded="parentOpen"
        @click="parentOpen = !parentOpen"
      >
        <UiGlyph
          meaning="instruction"
          :size="16"
        /><span class="pref__title">Instruktion till fråga {{ parent.label }}</span><span class="pref__excerpt">{{ parent.text }}</span><UiGlyph
          meaning="open-list"
          :size="16"
          class="pref__chevron"
        />
      </button>
      <div
        v-if="parentOpen"
        class="pref__body"
      >
        <p>{{ parent.text }}</p>
        <button
          type="button"
          class="xw-btn xw-btn--compact"
          data-test="exam-workspace-edit-instruction"
          @click="emit('gotoParent', parent.id)"
        >
          Redigera instruktionen
        </button>
      </div>
    </div>

    <ExamWorkspaceShortAnswerField
      v-if="isShortAnswer(item)"
      :item="item"
      :disabled="locked"
      :asset-urls="assetUrls"
      @update-body="(itemId, body, structural) => emit('updateBody', itemId, body, structural)"
      @update-gap-values="(itemId, gapId, values) => emit('updateGapValues', itemId, gapId, values)"
      @remove-automatic-value="(itemId, gapId, value) => emit('removeAutomaticValue', itemId, gapId, value)"
    />

    <ExamWorkspaceBodyEditor
      v-else
      :asset-urls="assetUrls"
      :disabled="locked"
      :item="item"
      @update-gap-values="(itemId, gapId, values) => emit('updateGapValues', itemId, gapId, values)"
      @update-gap-options="(itemId, gapId, options, correctOptionId, structural) => emit('updateGapOptions', itemId, gapId, options, correctOptionId, structural)"
      @remove-automatic-value="(itemId, gapId, value) => emit('removeAutomaticValue', itemId, gapId, value)"
      @create-gap="(itemId, body, gapId, seed) => emit('createGap', itemId, body, gapId, seed)"
      @show-gap-as-text="(itemId, gapId) => emit('showGapAsText', itemId, gapId)"
      @update-body="(itemId, body, structural) => emit('updateBody', itemId, body, structural)"
    />

    <template v-if="showFields">
      <ExamWorkspaceWritingLinesField
        v-if="item.kind === 'free_text' && item.writing_lines !== null"
        :lines="item.writing_lines"
        :disabled="locked"
        :all-free-text-match="allFreeTextWritingLinesMatch"
        :locked-reason-id="converting ? convertingNoticeId : null"
        @update="(lines) => emit('updateWritingLines', item.item_id, lines)"
        @apply-to-all="(lines) => emit('applyWritingLinesToAll', lines)"
      />
      <ExamWorkspaceCriteriaField
        v-if="item.kind === 'free_text'"
        :disabled="locked"
        :item="item"
        @update="(criteria, structural) => emit('updateCriteria', item.item_id, criteria, structural)"
      />
      <ExamWorkspaceChoiceField
        :disabled="locked"
        :item="item"
        @update-body="(choiceId, body, structural) => emit('updateChoiceBody', item.item_id, choiceId, body, structural)"
        @update-correct-choices="(ids) => emit('updateCorrectChoices', item.item_id, ids)"
      />
      <ExamWorkspaceOrderingField
        v-if="item.kind === 'ordering'"
        :disabled="locked"
        :item="item"
        @add-step="emit('addOrderingStep', item.item_id)"
        @move-step="(choiceId, delta) => emit('moveOrderingStep', item.item_id, choiceId, delta)"
        @remove-step="(choiceId) => emit('removeOrderingStep', item.item_id, choiceId)"
        @shuffle="emit('shuffleOrderingSteps', item.item_id)"
        @update-body="(choiceId, body, structural) => emit('updateChoiceBody', item.item_id, choiceId, body, structural)"
      />
      <ExamWorkspaceKategoriseraGrid
        v-if="isGrid"
        :disabled="locked"
        :item="item"
        @update-entry-body="
          (side, entryId, body, structural) =>
            emit('updateMatchEntryBody', item.item_id, side, entryId, body, structural)
        "
        @update-pairs="(pairs) => emit('updateMatchPairs', item.item_id, pairs)"
      />
    </template>

    <div
      v-if="keyLine && !converting"
      class="keyline"
      data-test="exam-workspace-original-facit"
    >
      <UiGlyph
        :meaning="keyLine.ai ? 'ai-assist' : 'document'"
        :size="16"
        :class="{ 'xw-ai': keyLine.ai }"
      />
      <span class="xw-grow">{{ keyLine.lead }} <q>{{ keyLine.facit }}</q></span>
      <button
        v-if="keyLine.ai && canUndoInterpretation(item)"
        type="button"
        class="xw-btn xw-btn--compact"
        title="Ångra AI-tolkningen och lämna frågan utan facit"
        :disabled="locked"
        data-test="exam-workspace-undo-interpretation"
        @click="emit('undoInterpretation', item.item_id)"
      >
        <UiGlyph
          meaning="undo"
          :size="16"
        />Ångra AI-tolkningen
      </button>
    </div>

    <ExamWorkspacePointsField
      :item="item"
      :disabled="locked"
      :converting="converting"
      @update-points="(points) => emit('updatePoints', item.item_id, points)"
      @update-tick-points="(tickPoints) => emit('updateTickPoints', item.item_id, tickPoints)"
    />
  </section>
</template>

<style scoped>
.qed { display: flex; flex-direction: column; min-width: 0; }
.qed__line { margin: -8px 0 12px; }
.qed__notice { margin-bottom: var(--huleedu-space-3); }
.pref {
  margin-bottom: var(--huleedu-space-3); border: 1px solid var(--huleedu-panel-border);
  border-radius: var(--huleedu-radius-lg); background: var(--huleedu-navy-02);
}
.pref__head {
  all: unset; box-sizing: border-box; display: flex; align-items: center; gap: var(--huleedu-space-2); width: 100%;
  min-height: 40px; padding: 0 var(--huleedu-space-3); cursor: pointer; font-size: var(--huleedu-text-sm);
}
.pref__head:focus-visible { outline: 2px solid var(--huleedu-action-40); }
.pref__title { font-weight: var(--huleedu-font-medium); white-space: nowrap; }
.pref__excerpt { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--huleedu-navy-60); }
.pref__head[aria-expanded="true"] .pref__chevron { transform: rotate(180deg); }
.pref__head[aria-expanded="true"] .pref__excerpt { visibility: hidden; }
.pref__body {
  padding: 0 var(--huleedu-space-3) var(--huleedu-space-3); font-size: var(--huleedu-text-sm); line-height: 1.55;
  font-family: var(--huleedu-font-serif);
}
.pref__body p { margin: 0 0 var(--huleedu-space-2); white-space: pre-line; }
.keyline {
  display: flex; align-items: center; gap: var(--huleedu-space-2); margin-top: var(--huleedu-space-3);
  font-size: var(--huleedu-text-sm); color: var(--huleedu-navy-70);
}
.keyline q { font-family: var(--huleedu-font-serif); color: var(--huleedu-navy); }
@media (max-width: 767px) {
  .keyline { flex-wrap: wrap; }
}
</style>
