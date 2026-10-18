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
 *     existing answer fields (`ExamWorkspaceBodyEditor`, `ExamWorkspaceChoiceField`,
 *     `ExamWorkspaceCriteriaField`, `ExamWorkspaceKategoriseraGrid`).
 *   - Provides the shared rich-text target registry, so the one formatting
 *     toolbar edits the surface the teacher last selected.
 *   - Holds no document state; every edit is emitted with the item id.
 */

import { computed, ref, useId, watch } from "vue";

import type {
  NativeExamBodyParagraph,
  NativeExamBodySegment,
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
import ExamWorkspaceQuestionHead from "./ExamWorkspaceQuestionHead.vue";
import ExamWorkspaceQuestionTools from "./ExamWorkspaceQuestionTools.vue";
import { isTeacherReviewed } from "./examWorkspaceItemEdits";
import { examWorkspaceItemReadiness } from "./examWorkspaceItemReadiness";
import { hasNegativePoints, NEGATIVE_POINTS_GUIDANCE } from "./examWorkspaceItemSaveRules";
import { provideRichTextTargetRegistry } from "./examWorkspaceRichTextTarget";
import type { ExamWorkspaceNotice } from "./useExamWorkspaceStructure";

/** A type the labeler read with less confidence than this is marked for checking. */
const TYPE_CONFIDENCE_THRESHOLD = 0.95;
/** A tick value is a number of at least 0 with at most 2 decimals (Q10). */
const TICK_POINTS_PATTERN = /^\d+(\.\d{1,2})?$/;

const props = defineProps<{
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
  assetUrls?: Record<string, string>;
}>();

provideRichTextTargetRegistry();

const emit = defineEmits<{
  changeType: [kind: NativeExamItemKind];
  move: [delta: -1 | 1];
  remove: [];
  toggleImport: [];
  toggleReviewed: [];
  retry: [kind: NativeExamItemKind];
  gotoParent: [parentId: string];
  dismissNotice: [];
  undoInterpretation: [itemId: string];
  removeAutomaticValue: [itemId: string, gapId: string, value: string];
  showGapAsText: [itemId: string, gapId: string];
  updateChoiceBody: [itemId: string, choiceId: string, body: NativeExamBodyParagraph[]];
  updateCorrectChoices: [itemId: string, correctChoiceIds: string[]];
  updateCriteria: [itemId: string, criteria: NativeExamCriterion[]];
  updateGapValues: [itemId: string, gapId: string, acceptedValues: string[]];
  updateGapOptions: [itemId: string, gapId: string, options: NativeExamChoice[], correctOptionId: string];
  updateMatchEntryBody: [itemId: string, side: "left" | "right", entryId: string, body: NativeExamBodyParagraph[]];
  updateMatchPairs: [itemId: string, pairs: NativeExamMatchPair[]];
  updateParagraphSegments: [itemId: string, paragraphIndex: number, segments: NativeExamBodySegment[]];
  updateParagraphHeading: [itemId: string, paragraphIndex: number, headingLevel: NativeExamBodyParagraph["heading_level"]];
  updatePoints: [itemId: string, points: number | null];
  updateTickPoints: [itemId: string, tickPoints: string];
}>();

const pointsId = useId();
const pointsMessageId = useId();
const tickId = useId();
const parentOpen = ref(false);
const tickInvalid = ref(false);

watch(
  () => props.item.item_id,
  () => {
    tickInvalid.value = false;
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
const hasCriteria = computed(() => props.item.criteria.length > 0);
const pointsMissing = computed(() => props.item.points === null);
const pointsNegative = computed(() => hasNegativePoints(props.item));
/** Points the import spread from the section total; shown as a nonblocking cue until the teacher sets them. */
const pointsEstimated = computed(
  () => props.item.points_estimated && !pointsMissing.value && !pointsNegative.value && !isGrid.value && !hasCriteria.value,
);
const showFields = computed(() => !props.converting && !unbuilt.value);

/** Where the answer key came from, with the key text the file printed. */
const keyLine = computed(() => {
  const facit = props.item.facit_text;
  if (!facit) return null;
  const origin = props.item.answer_key.origin;
  if (origin === "ai_interpreted") return { ai: true, lead: "Facit tolkat av AI ur", facit };
  if (origin === "absent") return { ai: false, lead: "Facit i provfilen:", facit };
  return { ai: false, lead: "Facit ur provfilen:", facit };
});

function handlePointsInput(event: Event): void {
  const raw = (event.target as HTMLInputElement).value.trim().replace(",", ".");
  if (raw.length === 0) {
    emit("updatePoints", props.item.item_id, null);
    return;
  }
  const parsed = Number(raw);
  emit("updatePoints", props.item.item_id, Number.isFinite(parsed) ? parsed : null);
}

/** Keep the last valid tick value in the document; mark the field while the typed value is invalid. */
function handleTickPointsInput(event: Event): void {
  const raw = (event.target as HTMLInputElement).value.trim().replace(",", ".");
  const valid = TICK_POINTS_PATTERN.test(raw);
  tickInvalid.value = !valid;
  if (valid) {
    emit("updateTickPoints", props.item.item_id, String(Number(raw)));
  }
}
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
      :unbuilt="unbuilt"
      :converting="converting"
      :child="child"
      :disabled="disabled"
      :suggested-kind="item.suggested_kind"
      @change-type="emit('changeType', $event)"
      @move="emit('move', $event)"
      @remove="emit('remove')"
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

    <ExamWorkspaceBodyEditor
      :asset-urls="assetUrls"
      :disabled="locked"
      :item="item"
      @update-gap-values="(itemId, gapId, values) => emit('updateGapValues', itemId, gapId, values)"
      @update-gap-options="(itemId, gapId, options, correctOptionId) => emit('updateGapOptions', itemId, gapId, options, correctOptionId)"
      @remove-automatic-value="(itemId, gapId, value) => emit('removeAutomaticValue', itemId, gapId, value)"
      @show-gap-as-text="(itemId, gapId) => emit('showGapAsText', itemId, gapId)"
      @update-paragraph-segments="(itemId, index, segments) => emit('updateParagraphSegments', itemId, index, segments)"
      @update-paragraph-heading="(itemId, index, level) => emit('updateParagraphHeading', itemId, index, level)"
    />

    <template v-if="showFields">
      <ExamWorkspaceCriteriaField
        v-if="item.kind === 'free_text'"
        :disabled="locked"
        :item="item"
        @update="(criteria) => emit('updateCriteria', item.item_id, criteria)"
      />
      <ExamWorkspaceChoiceField
        :disabled="locked"
        :item="item"
        @update-body="(choiceId, body) => emit('updateChoiceBody', item.item_id, choiceId, body)"
        @update-correct-choices="(ids) => emit('updateCorrectChoices', item.item_id, ids)"
      />
      <ExamWorkspaceKategoriseraGrid
        v-if="isGrid"
        :disabled="locked"
        :item="item"
        @update-entry-body="(side, entryId, body) => emit('updateMatchEntryBody', item.item_id, side, entryId, body)"
        @update-pairs="(pairs) => emit('updateMatchPairs', item.item_id, pairs)"
      />
      <div
        v-if="keyLine"
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
          v-if="keyLine.ai"
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
    </template>

    <div class="pts">
      <template v-if="isGrid && !converting">
        <label
          class="xw-label pts__label"
          :for="tickId"
        >Poäng per kryss</label>
        <input
          :id="tickId"
          class="xw-input pts__input"
          type="number"
          min="0"
          step="0.01"
          inputmode="decimal"
          :value="item.tick_points ?? ''"
          :disabled="locked"
          :aria-invalid="tickInvalid || undefined"
          data-test="exam-workspace-item-tick-points-input"
          @input="handleTickPointsInput"
        >
      </template>
      <label
        class="xw-label pts__label"
        :for="pointsId"
      >Poäng</label>
      <!-- A grid's points are its tick value times its ticks (Q10), and a free-text item's points are its criteria sum, so they are read-only. -->
      <input
        :id="pointsId"
        class="xw-input pts__input"
        type="number"
        min="0"
        step="any"
        inputmode="decimal"
        :value="item.points ?? ''"
        :disabled="locked"
        :readonly="isGrid || hasCriteria"
        :title="isGrid ? 'Poäng per kryss × antal kryss' : hasCriteria ? 'Summan av kriteriernas poäng' : undefined"
        :aria-invalid="pointsMissing || pointsNegative || undefined"
        :aria-describedby="pointsMissing || pointsNegative || pointsEstimated ? pointsMessageId : undefined"
        data-test="exam-workspace-item-points-input"
        @input="handlePointsInput"
      >
      <span
        v-if="pointsNegative"
        :id="pointsMessageId"
        class="xw-errline pts__msg"
        data-test="exam-workspace-points-hint"
      ><UiGlyph
        meaning="blocker"
        :size="16"
      />{{ NEGATIVE_POINTS_GUIDANCE }}</span>
      <span
        v-else-if="pointsMissing && !converting"
        :id="pointsMessageId"
        class="xw-errline pts__msg"
        data-test="exam-workspace-points-missing"
      ><UiGlyph
        meaning="blocker"
        :size="16"
      />Saknas</span>
      <span
        v-else-if="pointsEstimated && !converting"
        :id="pointsMessageId"
        class="xw-hint pts__msg"
        data-test="exam-workspace-points-estimated"
      ><UiGlyph
        meaning="info"
        :size="16"
      />Uppskattad utifrån avsnittets totalpoäng</span>
    </div>
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
.pts { display: flex; flex-wrap: wrap; align-items: center; gap: var(--huleedu-space-2) var(--huleedu-space-3); margin-top: var(--huleedu-space-5); }
.pts .pts__label { margin: 0; }
.pts__input { width: 96px; }
.pts__input[readonly] { background: var(--huleedu-navy-02); }
.pts__msg { margin: 0; }
@media (max-width: 767px) {
  .keyline { flex-wrap: wrap; }
}
</style>
