<script setup lang="ts">
/**
 * Authenticated Exam Converter host frame.
 *
 * Domain purpose:
 *   Provide the stable signed-in Exam Converter workspace frame, browser-local
 *   intake, and the first authenticated submit/poll/result-strip bridge.
 *
 * Relationships:
 *   - Mounted by `curatedAppHostRegistry` for authenticated Conversion Hub.
 *   - Composes shell components and delegates runtime transport to the
 *     authenticated Exam Converter runtime bridge.
 */

import { computed, ref } from "vue";

import type { SirConvertTerminalResult } from "../../api/sirConvertGateway";
import {
  DIGIEXAM_COMPLETION_MODE_SUGGEST_MISSING_MACHINE_MARKED,
} from "../../api/sirConvertGateway/contractValues";
import ExamConverterWorkflowRailShell from "./exam-converter-authenticated/ExamConverterWorkflowRailShell.vue";
import ExamConverterWorkspaceShell from "./exam-converter-authenticated/ExamConverterWorkspaceShell.vue";
import type {
  ExamConverterInspectionMode,
  ExamConverterReviewFile,
} from "./exam-converter-authenticated/digiexamIrReviewParser";
import {
  ACCEPT_CURRENT_STATE_COMPLETION_MODE,
  REVIEWED_COMPLETION_MODE,
  useExamConverterAiFacitReview,
} from "./exam-converter-authenticated/useExamConverterAiFacitReview";
import { useExamConverterAuthenticatedRuntime } from "./exam-converter-authenticated/useExamConverterAuthenticatedRuntime";
import { useExamConverterConversionState } from "./exam-converter-authenticated/useExamConverterConversionState";
import { useExamConverterFileActions } from "./exam-converter-authenticated/useExamConverterFileActions";
import { useExamConverterReviewArtifacts } from "./exam-converter-authenticated/useExamConverterReviewArtifacts";
import { useExamConverterSourceFile } from "./exam-converter-authenticated/useExamConverterSourceFile";
import type { ExamConverterRuntimeOutcome } from "./exam-converter-authenticated/useExamConverterConversionState";

const {
  clearSupportingFile,
  clearSourceFile,
  resetLocalChoices,
  selectDroppedFiles,
  selectSupportingFile,
  selectSourceFile,
  selectedSupportingFile,
  selectedSourceFile,
  selectedTargetFormats,
  supportingFileError,
  sourceFileError,
  toggleTargetFormat,
} = useExamConverterSourceFile();

const {
  failConversion,
  finishConversion,
  isConversionRunning,
  resetConversion,
  resultStrip,
  startConversion,
} = useExamConverterConversionState();
const { cancelRuntime, lastCorrelationId, lastJobId, submitAndPoll } =
  useExamConverterAuthenticatedRuntime();
const {
  loadReviewArtifacts,
  projection: reviewProjection,
  resetReviewArtifacts,
  status: reviewStatus,
} = useExamConverterReviewArtifacts();
const activeInspectionMode = ref<ExamConverterInspectionMode>("questions");
const acceptedCurrentState = ref(false);
const reviewedCompletionApplied = ref(false);
const {
  acceptAllSuggestions,
  acceptEditedChoiceSuggestion,
  acceptedSuggestionCount,
  acceptSuggestion,
  decisions: aiFacitDecisions,
  focusReviewAction,
  focusedReviewAction,
  leaveSuggestion,
  resetAiFacitReview,
  reviewedCompletionOverlay,
} = useExamConverterAiFacitReview();
const {
  downloadFile,
  fileActionStates,
  resetFileActions,
  saveFile,
} = useExamConverterFileActions();

const hasSelectedTargetFormat = computed(
  () => selectedTargetFormats.value.pdf || selectedTargetFormats.value.qti,
);

const canStartConversion = computed(
  () =>
    selectedSourceFile.value !== null &&
    hasSelectedTargetFormat.value &&
    !isConversionRunning.value,
);

const requiresReviewDecision = computed(() => {
  return (
    (reviewProjection.value?.report.attentionQuestionCount ?? 0) > 0 &&
    !acceptedCurrentState.value
  );
});

const canUseFiles = computed(() => {
  return reviewProjection.value !== null;
});

const canApplyReviewedSuggestions = computed(() => {
  return (
    reviewedCompletionOverlay.value(reviewProjection.value) !== null &&
    !isConversionRunning.value
  );
});

const showAiReviewPanel = computed(() => {
  return (
    !reviewedCompletionApplied.value &&
    (reviewProjection.value?.report.aiSuggestionCount ?? 0) > 0
  );
});

function handleResetLocalChoices(): void {
  cancelRuntime();
  resetReviewArtifacts();
  resetAiFacitReview();
  resetFileActions();
  acceptedCurrentState.value = false;
  reviewedCompletionApplied.value = false;
  activeInspectionMode.value = "questions";
  resetLocalChoices();
  resetConversion();
}

function toRuntimeOutcome(result: SirConvertTerminalResult): ExamConverterRuntimeOutcome {
  return {
    artifactCount: result.conversion_metadata.artifact_count,
    bundleStatus: result.conversion_metadata.bundle_status,
    manualFollowUpCount: null,
    manualFollowUpRequired: result.conversion_metadata.manual_follow_up_required,
    warningCount: result.conversion_metadata.warning_count,
  };
}

async function finishRuntimeResult(
  result: SirConvertTerminalResult,
  preferredMode: ExamConverterInspectionMode | null = null,
  completionReportRequired = false,
): Promise<void> {
  const runtimeOutcome = toRuntimeOutcome(result);
  const correlationId = lastCorrelationId.value;
  const jobId = lastJobId.value ?? result.job.jobId;
  const projection = correlationId
    ? await loadReviewArtifacts({
        completionReportRequired,
        correlationId,
        jobId,
      })
    : null;
  if (projection) {
    const projectedWarningCount = Math.max(
      runtimeOutcome.warningCount,
      projection.report.warningCount,
    );
    const requiresQuestionReview =
      projection.report.attentionQuestionCount > 0 || projectedWarningCount > 0;
    activeInspectionMode.value = preferredMode ?? projection.defaultMode;
    finishConversion({
      ...runtimeOutcome,
      bundleStatus: requiresQuestionReview ? runtimeOutcome.bundleStatus : "complete",
      manualFollowUpRequired: requiresQuestionReview,
      manualFollowUpCount: projection.report.attentionQuestionCount,
      warningCount: projectedWarningCount,
    });
    return;
  }
  finishConversion(runtimeOutcome);
}

async function handleStartConversion(): Promise<void> {
  const sourceSelection = selectedSourceFile.value;
  if (!canStartConversion.value || !sourceSelection) {
    return;
  }

  resetReviewArtifacts();
  resetAiFacitReview();
  resetFileActions();
  acceptedCurrentState.value = false;
  reviewedCompletionApplied.value = false;
  activeInspectionMode.value = "questions";
  startConversion();
  try {
    const result = await submitAndPoll({
      completionMode: DIGIEXAM_COMPLETION_MODE_SUGGEST_MISSING_MACHINE_MARKED,
      sourceFile: sourceSelection.file,
      supportingFile: selectedSupportingFile.value?.file ?? null,
      targetSelection: { ...selectedTargetFormats.value },
    });
    if (result) {
      await finishRuntimeResult(result, null, true);
    }
  } catch {
    failConversion();
  }
}

function selectInspectionMode(mode: ExamConverterInspectionMode): void {
  activeInspectionMode.value = mode;
}

async function handleAcceptCurrentState(): Promise<void> {
  const sourceSelection = selectedSourceFile.value;
  const overlay = reviewProjection.value?.acceptedStateOverlay ?? null;
  if (!sourceSelection || !overlay || isConversionRunning.value) {
    return;
  }
  resetFileActions();
  startConversion();
  try {
    const result = await submitAndPoll({
      sourceFile: sourceSelection.file,
      supportingFile: selectedSupportingFile.value?.file ?? null,
      targetSelection: { ...selectedTargetFormats.value },
      completionMode: ACCEPT_CURRENT_STATE_COMPLETION_MODE,
      ingestionOverlay: overlay,
    });
    if (result) {
      acceptedCurrentState.value = true;
      await finishRuntimeResult(result, "files");
    }
  } catch {
    acceptedCurrentState.value = false;
    failConversion();
  }
}

async function handleApplyReviewedSuggestions(): Promise<void> {
  const sourceSelection = selectedSourceFile.value;
  const overlay = reviewedCompletionOverlay.value(reviewProjection.value);
  if (!sourceSelection || !overlay || isConversionRunning.value) {
    return;
  }
  resetFileActions();
  startConversion();
  try {
    const result = await submitAndPoll({
      completionMode: REVIEWED_COMPLETION_MODE,
      ingestionOverlay: overlay,
      sourceFile: sourceSelection.file,
      supportingFile: selectedSupportingFile.value?.file ?? null,
      targetSelection: { ...selectedTargetFormats.value },
    });
    if (result) {
      acceptedCurrentState.value = false;
      reviewedCompletionApplied.value = true;
      await finishRuntimeResult(result, "files", false);
    }
  } catch {
    failConversion();
  }
}

async function handleDownloadFile(file: ExamConverterReviewFile): Promise<void> {
  const correlationId = lastCorrelationId.value;
  const jobId = lastJobId.value;
  if (!correlationId || !jobId || !canUseFiles.value || !file.exportEnabled) {
    return;
  }
  await downloadFile({ correlationId, file, jobId });
}

async function handleSaveFile(file: ExamConverterReviewFile): Promise<void> {
  const correlationId = lastCorrelationId.value;
  const jobId = lastJobId.value;
  if (!correlationId || !jobId || !canUseFiles.value || !file.exportEnabled) {
    return;
  }
  await saveFile({ correlationId, file, jobId });
}
</script>

<template>
  <main
    class="min-h-[calc(100vh-72px)] overflow-x-auto bg-canvas px-4 py-5 text-navy md:px-6 lg:px-8"
    aria-labelledby="exam-converter-auth-title"
  >
    <section
      class="mx-auto grid min-h-[28rem] min-w-[62rem] max-w-[90rem] grid-cols-[18rem_minmax(0,1fr)] items-stretch border border-navy bg-panel shadow-brutal-sm xl:grid-cols-[19rem_minmax(0,1fr)]"
      aria-label="Exam Converter"
      data-test="exam-converter-host-frame"
    >
      <ExamConverterWorkflowRailShell
        :can-start-conversion="canStartConversion"
        :is-conversion-running="isConversionRunning"
        :selected-supporting-file="selectedSupportingFile"
        :selected-source-file="selectedSourceFile"
        :selected-target-formats="selectedTargetFormats"
        :supporting-file-error="supportingFileError"
        @clear-supporting-file="clearSupportingFile"
        @clear-source-file="clearSourceFile"
        @reset-local-choices="handleResetLocalChoices"
        @start-conversion="handleStartConversion"
        @source-file-selected="selectSourceFile"
        @supporting-file-selected="selectSupportingFile"
        @toggle-target-format="toggleTargetFormat"
      />
      <ExamConverterWorkspaceShell
        :active-inspection-mode="activeInspectionMode"
        :accepted-current-state="acceptedCurrentState"
        :accepted-ai-suggestion-count="acceptedSuggestionCount"
        :ai-facit-decisions="aiFacitDecisions"
        :can-apply-reviewed-suggestions="canApplyReviewedSuggestions"
        :can-use-files="canUseFiles"
        :file-action-states="fileActionStates"
        :focused-ai-review-action="focusedReviewAction"
        :result-strip="resultStrip"
        :review-projection="reviewProjection"
        :requires-review-decision="requiresReviewDecision"
        :review-status="reviewStatus"
        :selected-source-file="selectedSourceFile"
        :show-ai-review-panel="showAiReviewPanel"
        :source-file-error="sourceFileError"
        @accept-current-state="handleAcceptCurrentState"
        @accept-all-ai-suggestions="acceptAllSuggestions(reviewProjection)"
        @accept-edited-choice-suggestion="acceptEditedChoiceSuggestion"
        @accept-suggestion="acceptSuggestion"
        @apply-reviewed-suggestions="handleApplyReviewedSuggestions"
        @download-file="handleDownloadFile"
        @files-dropped="selectDroppedFiles"
        @inspection-mode-selected="selectInspectionMode"
        @leave-suggestion="leaveSuggestion"
        @open-questions="selectInspectionMode('questions')"
        @review-action-focused="focusReviewAction"
        @save-file="handleSaveFile"
        @source-file-selected="selectSourceFile"
      />
    </section>
  </main>
</template>
