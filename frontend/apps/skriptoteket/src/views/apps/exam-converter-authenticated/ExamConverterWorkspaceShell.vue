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

import { FileText, Upload } from "lucide-vue-next";

import ExamConverterAdvisoryRetryPanel from "./ExamConverterAdvisoryRetryPanel.vue";
import ExamConverterAiReviewActionPanel from "./ExamConverterAiReviewActionPanel.vue";
import ExamConverterFilesReadinessList from "./ExamConverterFilesReadinessList.vue";
import ExamConverterInspectionTabs from "./ExamConverterInspectionTabs.vue";
import ExamConverterQuestionReviewShell from "./ExamConverterQuestionReviewShell.vue";
import ExamConverterReportSummary from "./ExamConverterReportSummary.vue";
import ExamConverterReviewDecisionGate from "./ExamConverterReviewDecisionGate.vue";
import ExamConverterResultStrip from "./ExamConverterResultStrip.vue";
import type {
  ExamConverterInspectionMode,
  ExamConverterReviewFile,
  ExamConverterReviewProjection,
} from "./digiexamIrReviewParser";
import type {
  ExamConverterAiFacitReviewAction,
  ExamConverterReviewedSuggestionDecision,
} from "./useExamConverterAiFacitReview";
import type { ExamConverterManualAnswerKeyCorrection } from "./digiexamTeacherCorrectionOverlay";
import type { ExamConverterFileActionStates } from "./useExamConverterFileActions";
import type { ExamConverterResultStripState } from "./useExamConverterConversionState";
import type { ExamConverterReviewArtifactsStatus } from "./useExamConverterReviewArtifacts";
import type { ExamConverterSourceFileSelection } from "./useExamConverterSourceFile";

defineProps<{
  activeInspectionMode: ExamConverterInspectionMode;
  acceptedCurrentState: boolean;
  acceptedAiSuggestionCount: number;
  aiFacitDecisions: Record<string, ExamConverterReviewedSuggestionDecision>;
  canApplyReviewedSuggestions: boolean;
  canRetryAdvisoryFacitSuggestion: boolean;
  canUseFiles: boolean;
  fileActionStates: ExamConverterFileActionStates;
  focusedAiReviewAction: ExamConverterAiFacitReviewAction;
  resultStrip: ExamConverterResultStripState | null;
  reviewProjection: ExamConverterReviewProjection | null;
  requiresReviewDecision: boolean;
  reviewStatus: ExamConverterReviewArtifactsStatus;
  selectedSourceFile: ExamConverterSourceFileSelection | null;
  showAiReviewPanel: boolean;
  sourceFileError: string | null;
}>();

const emit = defineEmits<{
  acceptCurrentState: [];
  acceptAllAiSuggestions: [];
  acceptEditedChoiceSuggestion: [
    question: ExamConverterReviewProjection["questions"][number],
    correctIds: number[],
  ];
  acceptSuggestion: [question: ExamConverterReviewProjection["questions"][number]];
  applyManualAnswerKey: [
    question: ExamConverterReviewProjection["questions"][number],
    answerKey: ExamConverterManualAnswerKeyCorrection,
  ];
  applyPointCorrection: [
    question: ExamConverterReviewProjection["questions"][number],
    maxScore: number,
  ];
  applyReviewedSuggestions: [];
  downloadFile: [file: ExamConverterReviewFile];
  filesDropped: [files: File[]];
  openQuestions: [];
  inspectionModeSelected: [mode: ExamConverterInspectionMode];
  retryAdvisoryFacitSuggestion: [];
  reviewActionFocused: [action: ExamConverterAiFacitReviewAction];
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
</script>

<template>
  <section
    class="flex h-full min-h-[26rem] min-w-0 flex-col bg-panel"
    :aria-label="resultStrip ? 'Exam Converter' : undefined"
    :aria-labelledby="resultStrip ? undefined : 'exam-converter-auth-title'"
    data-test="exam-converter-workspace-shell"
  >
    <header class="px-4 py-4">
      <template v-if="resultStrip">
        <ExamConverterAiReviewActionPanel
          v-if="showAiReviewPanel && reviewProjection && resultStrip.status !== 'running'"
          :accepted-count="acceptedAiSuggestionCount"
          :action="focusedAiReviewAction"
          :can-apply-reviewed-suggestions="canApplyReviewedSuggestions"
          :suggestion-count="reviewProjection.report.aiSuggestionCount"
          @accept-all-suggestions="emit('acceptAllAiSuggestions')"
          @apply-reviewed-suggestions="emit('applyReviewedSuggestions')"
          @open-questions="emit('openQuestions')"
        />
        <ExamConverterResultStrip
          v-else
          :result="resultStrip"
          @open-questions="emit('openQuestions')"
        />
        <ExamConverterReviewDecisionGate
          v-if="reviewProjection && requiresReviewDecision && !showAiReviewPanel"
          :accepted="acceptedCurrentState"
          :blocked-file-count="reviewProjection.report.blockedTargetFileCount"
          :missing-count="reviewProjection.report.attentionQuestionCount"
          @accept-current-state="emit('acceptCurrentState')"
          @review-questions="emit('openQuestions')"
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
          {{ selectedSourceFile ? "Nästa steg är att starta konverteringen." : "Dra hit .dxe-filen. Om du har ett rättat prov som PDF kan du dra in båda samtidigt." }}
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
            :attention-count="showAiReviewPanel ? 0 : reviewProjection.report.attentionQuestionCount"
            :file-count="reviewProjection.files.length"
            :question-count="reviewProjection.questions.length"
            @mode-selected="emit('inspectionModeSelected', $event)"
          />
          <ExamConverterQuestionReviewShell
            v-if="activeInspectionMode === 'questions'"
            :ai-facit-decisions="aiFacitDecisions"
            :projection="reviewProjection"
            @accept-edited-choice-suggestion="(question, correctIds) => emit('acceptEditedChoiceSuggestion', question, correctIds)"
            @accept-suggestion="emit('acceptSuggestion', $event)"
            @apply-manual-answer-key="(question, answerKey) => emit('applyManualAnswerKey', question, answerKey)"
            @apply-point-correction="(question, maxScore) => emit('applyPointCorrection', question, maxScore)"
            @review-action-focused="emit('reviewActionFocused', $event)"
          />
          <ExamConverterFilesReadinessList
            v-else-if="activeInspectionMode === 'files'"
            :action-states="fileActionStates"
            :actions-enabled="canUseFiles"
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
              .dxe och rättat prov som PDF kan dras in samtidigt.
            </p>
          </div>
        </div>
      </label>
    </div>
  </section>
</template>
