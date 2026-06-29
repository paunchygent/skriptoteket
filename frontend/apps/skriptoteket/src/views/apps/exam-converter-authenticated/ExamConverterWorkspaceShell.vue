<script setup lang="ts">
/**
 * Exam Converter workspace shell.
 *
 * Domain purpose:
 *   Reserve the dominant right-side workspace for approved Exam Converter
 *   intake, result, inspection, and review slices while keeping the host frame
 *   free of transport or conversion behavior.
 *
 * Relationships:
 *   - Rendered by `ExamConverterAuthenticatedView`.
 *   - Owns the idle source-file drop zone before later slices replace it with
 *     result strip, inspection modes, and focused review surfaces.
 */

import { computed } from "vue";
import { FileText, Upload } from "lucide-vue-next";

import ExamConverterAdvisoryRetryPanel from "./ExamConverterAdvisoryRetryPanel.vue";
import ExamConverterAiPrefillPanel from "./ExamConverterAiPrefillPanel.vue";
import ExamConverterFilesReadinessList from "./ExamConverterFilesReadinessList.vue";
import ExamConverterInspectionTabs from "./ExamConverterInspectionTabs.vue";
import ExamConverterQuestionReviewShell from "./ExamConverterQuestionReviewShell.vue";
import ExamConverterReportSummary from "./ExamConverterReportSummary.vue";
import ExamConverterResultStrip from "./ExamConverterResultStrip.vue";
import type {
  ExamConverterInspectionMode,
  ExamConverterReviewFile,
  ExamConverterReviewProjection,
} from "./digiexamIrReviewParser";
import type { ExamConverterAiPrefillFocus } from "./useExamConverterAiPrefillFocus";
import type {
  ExamConverterItemTextPatchCorrection,
  ExamConverterManualAnswerKeyCorrection,
} from "./digiexamTeacherCorrectionOverlay";
import type { ExamConverterFileActionStates } from "./useExamConverterFileActions";
import type { ExamConverterResultStripState } from "./useExamConverterConversionState";
import type { ExamConverterReviewArtifactsStatus } from "./useExamConverterReviewArtifacts";
import type { ExamConverterSourceFileSelection } from "./useExamConverterSourceFile";

const props = defineProps<{
  activeInspectionMode: ExamConverterInspectionMode;
  aiSuggestionFocusKey: number;
  canRetryAdvisoryFacitSuggestion: boolean;
  canUseFiles: boolean;
  fileActionNotice: string | null;
  fileActionStates: ExamConverterFileActionStates;
  focusedAiPrefill: ExamConverterAiPrefillFocus;
  isCorrectionApplying: boolean;
  resultStrip: ExamConverterResultStripState | null;
  reviewProjection: ExamConverterReviewProjection | null;
  reviewStatus: ExamConverterReviewArtifactsStatus;
  selectedSourceFile: ExamConverterSourceFileSelection | null;
  showAiPrefillPanel: boolean;
  sourceFileError: string | null;
}>();

const emit = defineEmits<{
  applyManualAnswerKey: [
    question: ExamConverterReviewProjection["questions"][number],
    answerKey: ExamConverterManualAnswerKeyCorrection,
  ];
  applyItemTextPatch: [
    question: ExamConverterReviewProjection["questions"][number],
    patch: ExamConverterItemTextPatchCorrection,
  ];
  applyPointCorrection: [
    question: ExamConverterReviewProjection["questions"][number],
    maxScore: number,
  ];
  downloadFile: [file: ExamConverterReviewFile];
  filesDropped: [files: File[]];
  openQuestions: [];
  inspectionModeSelected: [mode: ExamConverterInspectionMode];
  retryAdvisoryFacitSuggestion: [];
  aiPrefillFocused: [focus: ExamConverterAiPrefillFocus];
  saveFile: [file: ExamConverterReviewFile];
  sourceFileSelected: [file: File];
}>();

function selectFirstFile(fileList: FileList | null): void {
  const [file] = Array.from(fileList ?? []);
  if (file) {
    emit("sourceFileSelected", file);
  }
}

function handleFileInput(event: Event): void {
  const input = event.target as HTMLInputElement;
  selectFirstFile(input.files);
  input.value = "";
}

function handleDrop(event: DragEvent): void {
  event.preventDefault();
  const files = Array.from(event.dataTransfer?.files ?? []);
  if (files.length > 0) {
    emit("filesDropped", files);
  }
}

const projectionBackedResultStrip = computed<ExamConverterResultStripState | null>(() => {
  if (!props.resultStrip) return null;
  if (props.resultStrip.status === "running" || !props.reviewProjection) {
    return props.resultStrip;
  }
  const count = props.reviewProjection.report.attentionQuestionCount;
  if (count <= 0) {
    return props.resultStrip;
  }
  return {
    ...props.resultStrip,
    actionLabel: "Granska",
    detail: `${count.toLocaleString("sv-SE")} att granska`,
    nextAction: "Granska frågorna som saknar rätt svar eller facitsvar.",
    status: "partial",
    title: "Kontrollera facit",
    tone: "warning",
  };
});
</script>

<template>
  <section
    class="flex h-full min-h-[26rem] min-w-0 flex-col bg-panel"
    :aria-label="resultStrip ? 'Exam Converter' : undefined"
    :aria-labelledby="resultStrip ? undefined : 'exam-converter-auth-title'"
    data-test="exam-converter-workspace-shell"
  >
    <header class="px-4 py-4">
      <template v-if="projectionBackedResultStrip">
        <ExamConverterAiPrefillPanel
          v-if="showAiPrefillPanel && reviewProjection && projectionBackedResultStrip.status !== 'running'"
          :focus="focusedAiPrefill"
          :review-count="reviewProjection.report.attentionQuestionCount"
          @open-questions="emit('openQuestions')"
        />
        <ExamConverterResultStrip
          v-else
          :result="projectionBackedResultStrip"
          @open-questions="emit('openQuestions')"
        />
        <ExamConverterAdvisoryRetryPanel
          v-if="canRetryAdvisoryFacitSuggestion"
          :disabled="false"
          @retry="emit('retryAdvisoryFacitSuggestion')"
        />
      </template>
      <div
        v-else
        class="min-w-0"
      >
        <h2
          id="exam-converter-auth-title"
          class="text-lg font-semibold leading-tight text-navy"
        >
          {{ selectedSourceFile ? "Provfilen är vald" : "Välj provfil för att börja" }}
        </h2>
        <p class="mt-1 text-sm leading-snug text-navy/70">
          {{ selectedSourceFile ? "Nästa steg är att starta konverteringen." : "Dra hit .dxe-filen eller välj provfilen här." }}
        </p>
      </div>
    </header>

    <div class="flex min-h-0 flex-1 px-4 pb-4">
      <div
        v-if="resultStrip?.status === 'running'"
        class="grid min-h-0 w-full flex-1 place-items-center border border-dashed border-navy/45 bg-canvas px-6 py-6"
        data-test="exam-converter-running-surface"
      >
        <p class="text-base font-medium leading-tight text-navy">
          Vänta medan provet konverteras.
        </p>
      </div>
      <div
        v-else-if="resultStrip"
        class="min-h-0 min-w-0 w-full flex-1 overflow-hidden bg-panel"
        data-test="exam-converter-inspection-surface"
      >
        <div
          v-if="reviewStatus === 'loading'"
          class="grid min-h-[18rem] place-items-center border border-dashed border-navy/35 bg-canvas px-6 py-8 text-center"
          data-test="exam-converter-review-loading"
        >
          <p class="text-sm font-medium leading-snug text-navy">
            Läser frågorna.
          </p>
        </div>
        <div
          v-else-if="reviewStatus === 'failed' || !reviewProjection"
          class="grid min-h-[18rem] place-items-center border border-dashed border-error/45 bg-error/5 px-6 py-8 text-center"
          data-test="exam-converter-review-failed"
        >
          <p class="text-sm font-medium leading-snug text-navy">
            Det gick inte att läsa frågorna. Försök igen.
          </p>
        </div>
        <div
          v-else
          class="flex min-h-0 min-w-0 flex-1 flex-col"
        >
          <ExamConverterInspectionTabs
            :active-mode="activeInspectionMode"
            :attention-count="showAiPrefillPanel ? 0 : reviewProjection.report.attentionQuestionCount"
            :file-count="reviewProjection.files.length"
            :question-count="reviewProjection.questions.length"
            @mode-selected="emit('inspectionModeSelected', $event)"
          />
          <ExamConverterQuestionReviewShell
            v-if="activeInspectionMode === 'questions'"
            :ai-suggestion-focus-key="aiSuggestionFocusKey"
            :is-correction-applying="isCorrectionApplying"
            :projection="reviewProjection"
            @apply-item-text-patch="(question, patch) => emit('applyItemTextPatch', question, patch)"
            @apply-manual-answer-key="(question, answerKey) => emit('applyManualAnswerKey', question, answerKey)"
            @apply-point-correction="(question, maxScore) => emit('applyPointCorrection', question, maxScore)"
            @ai-prefill-focused="emit('aiPrefillFocused', $event)"
          />
          <ExamConverterFilesReadinessList
            v-else-if="activeInspectionMode === 'files'"
            :action-states="fileActionStates"
            :actions-enabled="canUseFiles"
            :action-notice="fileActionNotice"
            :files="reviewProjection.files"
            @download-file="emit('downloadFile', $event)"
            @save-file="emit('saveFile', $event)"
          />
          <ExamConverterReportSummary
            v-else
            :report="reviewProjection.report"
            @open-questions="emit('inspectionModeSelected', 'questions')"
          />
        </div>
      </div>
      <label
        v-else
        class="grid min-h-0 w-full flex-1 border border-dashed border-navy/45 bg-canvas px-6 py-6"
        :class="sourceFileError ? 'border-error bg-error/5' : undefined"
        data-test="exam-converter-source-drop-zone"
        @dragover.prevent
        @drop="handleDrop"
      >
        <input
          class="sr-only"
          type="file"
          accept=".dxe"
          data-test="exam-converter-source-file-input"
          @change="handleFileInput"
        >
        <div class="flex h-full min-w-0 items-center justify-center gap-4">
          <span
            class="grid h-12 w-12 shrink-0 place-items-center border border-navy/25 bg-panel"
            aria-hidden="true"
          >
            <FileText
              v-if="selectedSourceFile"
              class="h-6 w-6 text-navy"
            />
            <Upload
              v-else
              class="h-6 w-6 text-action"
            />
          </span>
          <div class="min-w-0">
            <p class="text-base font-medium leading-tight text-navy">
              {{ selectedSourceFile?.name ?? "Välj provfil" }}
            </p>
            <p
              v-if="selectedSourceFile"
              class="mt-2 text-sm leading-snug text-navy/70"
            >
              {{ selectedSourceFile.sizeLabel }}
            </p>
            <p
              v-else-if="sourceFileError"
              class="mt-2 text-sm leading-snug text-error"
            >
              {{ sourceFileError }}
            </p>
            <p
              v-else
              class="mt-2 text-sm leading-snug text-navy/70"
            >
              Endast en .dxe-fil kan användas här.
            </p>
          </div>
        </div>
      </label>
    </div>
  </section>
</template>
