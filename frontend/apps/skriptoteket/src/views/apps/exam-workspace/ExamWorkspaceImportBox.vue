<script setup lang="ts">
/**
 * Exam workspace Import box.
 *
 * Domain purpose:
 *   The question as the exam file had it, opened with the question's Import
 *   button: its wording, the answer key the file printed, why the conversion
 *   wants it reviewed, and numbered lines naming what the conversion decided.
 *   While the question needs review and the server kept its source,
 *   "Konvertera igen" converts it again as the type the teacher picks.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceQuestionEditor` under the question header.
 */

import { computed, ref, useId, watch } from "vue";

import type { NativeExamDocument, NativeExamItem, NativeExamItemKind } from "../../../api/examWorkspace";
import { UiGlyph } from "../../../components/ui";
import { AI_ADMIN_ONLY_NOTE } from "../../../composables/useAiAccess";
import { examWorkspaceImportSteps } from "./examWorkspaceImportSteps";
import { GUEST_AI_SIGN_IN } from "./examWorkspaceGuestCopy";
import { useExamWorkspaceSignIn } from "./examWorkspaceSignIn";
import { EXAM_WORKSPACE_TYPE_LABELS, examWorkspaceReviewReasonLabel } from "./examWorkspaceRows";
import { useExamWorkspaceAiMode } from "./useExamWorkspaceAiMode";

/** The five types the converter produces, in the order the retry selector offers them. */
const RETRY_KINDS: readonly NativeExamItemKind[] = [
  "free_text",
  "single_choice",
  "multiple_response",
  "gap_fill",
  "matching",
];

const props = defineProps<{
  item: NativeExamItem;
  origin: NativeExamDocument["origin"]["kind"];
  open: boolean;
  disabled: boolean;
}>();

const emit = defineEmits<{ retry: [kind: NativeExamItemKind] }>();

const requestSignIn = useExamWorkspaceSignIn();
const aiNoteId = useId();
/** Guest controls stay enabled and ask for sign-in; signed-in controls follow the admin gate. */
const aiMode = useExamWorkspaceAiMode();
const isGuest = computed(() => aiMode.value === "guest");
const adminOnly = computed(() => aiMode.value === "admin_only");

function handleRetry(): void {
  if (isGuest.value) {
    requestSignIn(GUEST_AI_SIGN_IN);
    return;
  }
  emit("retry", selectedKind.value);
}

/** Null until the teacher picks, so the type the file was read as shows first. */
const retryKind = ref<NativeExamItemKind | null>(null);
watch(
  () => props.item.item_id,
  () => {
    retryKind.value = null;
  },
);

const record = computed(() => props.item.import_record);
const sourceName = computed(() => (props.origin === "digiexam_import" ? "DigiExam" : "Word"));
const steps = computed(() => (record.value ? examWorkspaceImportSteps(record.value) : []));
const issues = computed(() =>
  props.item.review.state === "review_required"
    ? [...new Set(props.item.review.reasons.map(examWorkspaceReviewReasonLabel))]
    : [],
);
const selectedKind = computed<NativeExamItemKind>(() => {
  const preferred = retryKind.value ?? props.item.retry_source?.label_kind ?? props.item.kind;
  return RETRY_KINDS.includes(preferred) ? preferred : "free_text";
});

function chooseKind(event: Event): void {
  retryKind.value = (event.target as HTMLSelectElement).value as NativeExamItemKind;
}
</script>

<template>
  <div
    v-if="record"
    class="imp-wrap"
    :class="{ 'imp-wrap--open': open }"
    :inert="!open"
    data-test="exam-workspace-import-box"
  >
    <div>
      <div class="imp">
        <h3>I provfilen <span class="imp__src">· {{ sourceName }}</span></h3>
        <div class="imp__orig">
          {{ record.original_wording.question_text }}
        </div>
        <template v-if="record.original_wording.answer_key_text">
          <h3 class="imp__gap">
            Facit i provfilen
          </h3>
          <div class="imp__orig">
            {{ record.original_wording.answer_key_text }}
          </div>
        </template>
        <p
          v-for="issue in issues"
          :key="issue"
          class="imp__issue"
        >
          <UiGlyph
            meaning="status-warning"
            :size="16"
          />{{ issue }}
        </p>
        <ol
          v-if="steps.length > 0"
          class="imp__steps"
        >
          <li
            v-for="(step, index) in steps"
            :key="index"
          >
            {{ step }}
          </li>
        </ol>
        <div
          v-if="item.retry_source && item.review.state === 'review_required'"
          class="imp__retry"
        >
          <label
            class="xw-muted imp__retry-label"
            :for="`retry-${item.item_id}`"
          >Konvertera frågan igen som</label>
          <select
            :id="`retry-${item.item_id}`"
            :value="selectedKind"
            :disabled="disabled || adminOnly"
            data-test="exam-workspace-retry-kind"
            @change="chooseKind"
          >
            <option
              v-for="kind in RETRY_KINDS"
              :key="kind"
              :value="kind"
            >
              {{ EXAM_WORKSPACE_TYPE_LABELS[kind] }}
            </option>
          </select>
          <button
            type="button"
            class="xw-btn xw-btn--compact"
            :disabled="disabled || adminOnly"
            :title="adminOnly ? AI_ADMIN_ONLY_NOTE : undefined"
            :aria-describedby="adminOnly ? aiNoteId : undefined"
            data-test="exam-workspace-retry"
            @click="handleRetry"
          >
            <UiGlyph
              meaning="retry"
              :size="16"
            />Konvertera igen
          </button>
          <p
            v-if="adminOnly"
            :id="aiNoteId"
            class="xw-hint imp__retry-note"
          >
            {{ AI_ADMIN_ONLY_NOTE }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.imp-wrap { display: grid; grid-template-rows: 0fr; opacity: 0; transition: grid-template-rows 220ms ease-out, opacity 220ms ease-out; }
.imp-wrap--open { grid-template-rows: 1fr; opacity: 1; }
.imp-wrap > div { min-height: 0; overflow: hidden; }
@media (prefers-reduced-motion: reduce) { .imp-wrap { transition: none; } }
.imp {
  background: var(--huleedu-navy-02); border: 1px solid var(--huleedu-panel-border); border-radius: var(--huleedu-radius-lg);
  padding: var(--huleedu-space-3) var(--huleedu-space-4); margin-bottom: var(--huleedu-space-3);
}
.imp h3 {
  margin: 0 0 var(--huleedu-space-1-5); display: flex; align-items: center; gap: var(--huleedu-space-2);
  font-size: var(--huleedu-text-xs); font-weight: var(--huleedu-font-semibold); color: var(--huleedu-navy-70);
}
.imp .imp__gap { margin-top: var(--huleedu-space-2-5); }
.imp__src { font-weight: var(--huleedu-font-normal); color: var(--huleedu-navy-60); }
.imp__orig { font-size: var(--huleedu-text-sm); line-height: 1.55; font-family: var(--huleedu-font-serif); white-space: pre-line; }
.imp__issue {
  display: flex; gap: var(--huleedu-space-1-5); align-items: center; margin: var(--huleedu-space-2) 0 0;
  color: var(--huleedu-warning); font-size: var(--huleedu-text-sm);
}
.imp__steps { margin: var(--huleedu-space-3) 0 0; padding: 0; list-style: none; display: grid; gap: 2px; counter-reset: step; }
.imp__steps li { display: flex; gap: var(--huleedu-space-2); font-size: var(--huleedu-text-xs); color: var(--huleedu-navy-70); }
.imp__steps li::before {
  counter-increment: step; content: counter(step); flex: none; display: inline-flex; align-items: center; justify-content: center;
  width: 16px; height: 16px; border-radius: 50%; background: var(--huleedu-navy-10, rgba(8, 43, 76, 0.1));
  font-size: 10px; font-weight: var(--huleedu-font-semibold);
}
.imp__retry {
  display: flex; flex-wrap: wrap; align-items: center; gap: var(--huleedu-space-2);
  margin-top: var(--huleedu-space-3); padding-top: var(--huleedu-space-3); border-top: 1px solid var(--huleedu-surface-divider);
}
.imp__retry-label { font-size: var(--huleedu-text-xs); }
.imp__retry-note { flex-basis: 100%; margin: 0; }
.imp__retry select {
  height: 28px; padding: 0 var(--huleedu-space-2); font: inherit; font-size: var(--huleedu-text-xs);
  border: 1px solid var(--huleedu-panel-border); border-radius: var(--huleedu-workbench-control-radius);
  background: var(--huleedu-surface-content);
}
</style>
