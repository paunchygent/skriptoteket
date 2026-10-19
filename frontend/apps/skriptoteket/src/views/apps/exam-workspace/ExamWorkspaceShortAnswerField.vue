<script setup lang="ts">
/**
 * Exam workspace Kort svar field.
 *
 * Domain purpose:
 *   Show a Kort svar question as exactly two fields: "Fråga" (the rich-text
 *   question without its answer paragraph, with the mark toolbar and no gap
 *   button) and "Svar" (one row per accepted answer, with the automatic
 *   answers under it). No gap chip, no popover, no "Visa som text". Every
 *   Fråga edit re-attaches the answer paragraph before it is emitted, so the
 *   gap record never drops. While `disabled` is set, nothing can be edited
 *   and no change is forwarded.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceQuestionEditor` instead of
 *     `ExamWorkspaceBodyEditor` when the item is a Kort svar.
 *   - Emits the BodyEditor update names the question editor forwards:
 *     `updateBody`, `updateGapValues`, `removeAutomaticValue`.
 *   - `ExamWorkspaceRichTextEditor` owns the Fråga text,
 *     `ExamWorkspaceMarkToolbar` its glyph buttons,
 *     `ExamWorkspaceGapAnswerList` the Svar rows, and
 *     `ExamWorkspaceGapAutomaticValues` the automatic answers.
 *   - `examWorkspaceShortAnswer` splits the body and re-attaches the answer
 *     paragraph; `examWorkspaceRichTextTarget` is the shared active target
 *     the toolbar reads and calls.
 */

import { computed, useId } from "vue";

import type { NativeExamBodyParagraph, NativeExamItem } from "../../../api/examWorkspace";
import type { BodyMark } from "./examWorkspaceBodyMarks";
import ExamWorkspaceGapAnswerList from "./ExamWorkspaceGapAnswerList.vue";
import ExamWorkspaceGapAutomaticValues from "./ExamWorkspaceGapAutomaticValues.vue";
import ExamWorkspaceMarkToolbar from "./ExamWorkspaceMarkToolbar.vue";
import ExamWorkspaceRichTextEditor from "./ExamWorkspaceRichTextEditor.vue";
import { shortAnswerParts, withShortAnswerQuestion } from "./examWorkspaceShortAnswer";
import { useRichTextTargetRegistry } from "./examWorkspaceRichTextTarget";

type HeadingLevel = 1 | 2 | 3;

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
const parts = computed(() => shortAnswerParts(props.item));
const richTextTargets = useRichTextTargetRegistry();
const activeRichTextTarget = richTextTargets.active;
const activeMarks = computed(() => activeRichTextTarget.value?.marks.value ?? []);
const activeHeading = computed<HeadingLevel | null>(
  () => activeRichTextTarget.value?.headingLevel() ?? null,
);

function handleToggleMark(mark: BodyMark): void {
  activeRichTextTarget.value?.toggleMark(mark);
}

function handleToggleHeading(level: HeadingLevel): void {
  activeRichTextTarget.value?.toggleHeading(level);
}

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
        Fråga
      </div>
      <div class="xw-rich">
        <ExamWorkspaceMarkToolbar
          class="xw-rich__bar"
          :active-marks="activeMarks"
          :active-heading="activeHeading"
          :disabled="disabled"
          show-headings
          @toggle-mark="handleToggleMark"
          @toggle-heading="handleToggleHeading"
        />
        <div class="xw-rich__body grid gap-2">
          <ExamWorkspaceRichTextEditor
            :key="item.item_id"
            :body="parts.question"
            label="Fråga"
            test-id="exam-workspace-short-answer-question"
            variant="field"
            :disabled="disabled"
            :asset-urls="assetUrls"
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
        Svar
      </div>
      <ExamWorkspaceGapAnswerList
        :values="parts.gap.accepted_values"
        label="Svar"
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
