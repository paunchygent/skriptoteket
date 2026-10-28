<script setup lang="ts">
/**
 * Exam workspace Kort svar field.
 *
 * Domain purpose:
 *   Show a Kort svar question as exactly two fields: "Frågetext" (the
 *   rich-text question without its answer paragraph, with the mark toolbar
 *   and no gap button) and "Godkända svar" (one row per accepted answer,
 *   with the automatic answers under it). No gap chip, no popover, no
 *   "Visa som text". Every Frågetext edit re-attaches the answer paragraph
 *   before it is emitted, so the
 *   gap record never drops. While `disabled` is set, nothing can be edited
 *   and no change is forwarded.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceQuestionEditor` instead of
 *     `ExamWorkspaceBodyEditor` when the item is a Kort svar.
 *   - Emits the BodyEditor update names the question editor forwards:
 *     `updateBody`, `updateGapValues`, `removeAutomaticValue`.
 *   - `ExamWorkspaceRichTextEditor` owns the Frågetext text,
 *     `ExamWorkspaceMarkToolbar` its glyph buttons and, through this field's
 *     `toolbar-end` slot, its last AI group,
 *     `ExamWorkspaceGapAnswerList` the Godkända svar rows, and
 *     `ExamWorkspaceGapAutomaticValues` the automatic answers.
 *   - `examWorkspaceShortAnswer` splits the body and re-attaches the answer
 *     paragraph; `examWorkspaceRichTextTarget` is the shared active target
 *     the toolbar reads and calls.
 */

import { computed, ref, useId } from "vue";

import type { NativeExamBodyParagraph, NativeExamItem } from "../../../api/examWorkspace";
import ExamWorkspaceGapAnswerList from "./ExamWorkspaceGapAnswerList.vue";
import ExamWorkspaceGapAutomaticValues from "./ExamWorkspaceGapAutomaticValues.vue";
import ExamWorkspaceMarkToolbar from "./ExamWorkspaceMarkToolbar.vue";
import ExamWorkspaceRichTextEditor from "./ExamWorkspaceRichTextEditor.vue";
import { useExamWorkspacePictureControl } from "./examWorkspacePictureService";
import { shortAnswerParts, withShortAnswerQuestion } from "./examWorkspaceShortAnswer";
import { useExamWorkspaceRichTextToolbar } from "./useExamWorkspaceRichTextToolbar";

const props = defineProps<{
  item: NativeExamItem;
  disabled?: boolean;
  /** Asset URL per asset id; a mapped picture renders, an unmapped one keeps its placeholder. */
  assetUrls?: Record<string, string>;
}>();

const emit = defineEmits<{
  updateBody: [itemId: string, body: NativeExamBodyParagraph[], structural: boolean];
  updateGapValues: [itemId: string, gapId: string, acceptedValues: string[]];
  removeAutomaticValue: [itemId: string, gapId: string, value: string];
}>();

const questionLabelId = useId();
const answerLabelId = useId();
const editor = ref<InstanceType<typeof ExamWorkspaceRichTextEditor> | null>(null);
const parts = computed(() => shortAnswerParts(props.item));
const { activeMarks, activeHeading, activeRichTextTarget, toggleMark, toggleHeading } =
  useExamWorkspaceRichTextToolbar();


/** The picture button: its state and where a chosen file goes. */
const {
  enabled: picturesEnabled,
  selected: pictureSelected,
  busy: pictureBusy,
  add: handleAddPicture,
} = useExamWorkspacePictureControl(
  () => activeRichTextTarget.value,
  () => editor.value,
);

function handleQuestionUpdate(body: NativeExamBodyParagraph[], structural: boolean): void {
  if (props.disabled) {
    return;
  }
  const current = parts.value;
  if (current === null) {
    return;
  }
  emit("updateBody", props.item.item_id, withShortAnswerQuestion(current, body), structural);
}

function handleAnswersCommit(values: string[]): void {
  if (props.disabled) {
    return;
  }
  const current = parts.value;
  if (current === null) {
    return;
  }
  emit("updateGapValues", props.item.item_id, current.gap.gap_id, values);
}

function handleAutomaticValueRemoval(value: string): void {
  if (props.disabled) {
    return;
  }
  const current = parts.value;
  if (current === null) {
    return;
  }
  emit("removeAutomaticValue", props.item.item_id, current.gap.gap_id, value);
}
</script>

<template>
  <div
    v-if="parts !== null"
    class="mb-4 grid gap-1.5"
    data-test="exam-workspace-short-answer"
  >
    <div
      class="grid gap-1.5"
      role="group"
      :aria-labelledby="questionLabelId"
    >
      <div
        :id="questionLabelId"
        class="xw-label"
      >
        Frågetext
      </div>
      <div class="xw-rich">
        <ExamWorkspaceMarkToolbar
          class="xw-rich__bar"
          :active-marks="activeMarks"
          :active-heading="activeHeading"
          :disabled="disabled"
          show-headings
          :show-picture="picturesEnabled"
          :picture-selected="pictureSelected"
          :picture-busy="pictureBusy"
          question-text
          @toggle-mark="toggleMark"
          @toggle-heading="toggleHeading"
          @add-picture="handleAddPicture"
        >
          <template #end>
            <slot name="toolbar-end" />
          </template>
        </ExamWorkspaceMarkToolbar>
        <div class="xw-rich__body grid gap-2">
          <ExamWorkspaceRichTextEditor
            :key="item.item_id"
            ref="editor"
            :body="parts.question"
            label="Frågetext"
            test-id="exam-workspace-short-answer-question"
            variant="field"
            :disabled="disabled"
            :asset-urls="assetUrls"
            :pictures="picturesEnabled"
            @update="handleQuestionUpdate"
          />
        </div>
      </div>
    </div>

    <div
      class="grid gap-1.5"
      role="group"
      :aria-labelledby="answerLabelId"
    >
      <div
        :id="answerLabelId"
        class="xw-label"
      >
        Godkända svar
      </div>
      <ExamWorkspaceGapAnswerList
        :values="parts.gap.accepted_values"
        label="Godkända svar"
        test-id="exam-workspace-short-answer-values"
        :disabled="disabled"
        @commit="handleAnswersCommit"
      />
      <ExamWorkspaceGapAutomaticValues
        v-if="parts.gap.automatic_values.length > 0"
        :values="parts.gap.automatic_values"
        :disabled="disabled"
        @remove="handleAutomaticValueRemoval"
      />
    </div>
  </div>
</template>
