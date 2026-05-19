<script setup lang="ts">
/**
 * Authenticated Exam Converter host frame.
 *
 * Domain purpose:
 *   Provide the signed-in Exam Converter workspace, browser-local intake, and
 *   authenticated submit/readback bridge.
 *
 * Relationships:
 *   - Mounted by `curatedAppHostRegistry` for authenticated Conversion Hub.
 *   - Composes shell components and delegates transport to runtime composables.
 */

import { computed, onMounted, ref } from "vue";

import type { SirConvertTerminalResult } from "../../api/sirConvertGateway";
import { DIGIEXAM_COMPLETION_MODE_SUGGEST_MISSING_MACHINE_MARKED } from "../../api/sirConvertGateway/contractValues";
import ExamConverterWorkflowRailShell from "./exam-converter-authenticated/ExamConverterWorkflowRailShell.vue";
import ExamConverterWorkspaceShell from "./exam-converter-authenticated/ExamConverterWorkspaceShell.vue";
import type {
  ExamConverterInspectionMode,
  ExamConverterReviewFile,
  ExamConverterReviewProjection,
} from "./exam-converter-authenticated/digiexamIrReviewParser";
import { visibleMissingFieldsForQuestion } from "./exam-converter-authenticated/digiexamIrReviewParser";
import type { ExamConverterAiPrefillFocus } from "./exam-converter-authenticated/useExamConverterAiPrefillFocus";
import { isProviderOnlyAdvisoryFailureReport } from "./exam-converter-authenticated/digiexamAnswerKeyCompletionReport";
import { useExamConverterAuthenticatedRuntime } from "./exam-converter-authenticated/useExamConverterAuthenticatedRuntime";
import { useExamConverterConversionState } from "./exam-converter-authenticated/useExamConverterConversionState";
import { useExamConverterFileActions } from "./exam-converter-authenticated/useExamConverterFileActions";
import { useExamConverterReviewArtifacts } from "./exam-converter-authenticated/useExamConverterReviewArtifacts";
import { useExamConverterSourceFile } from "./exam-converter-authenticated/useExamConverterSourceFile";
import { useExamConverterUnifiedCorrections } from "./exam-converter-authenticated/useExamConverterUnifiedCorrections";
import type { ExamConverterRuntimeOutcome } from "./exam-converter-authenticated/useExamConverterConversionState";
const props = defineProps<{
  inspectionFixtureId?: string | null;
}>();

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
const {
  cancelRuntime,
  clearLastJobHandle,
  issueCorrectionSourceState,
  lastConversionHubJobId,
  lastCorrelationId,
  lastJobId,
  restoreLastJobHandle,
  submitAndPoll,
} =
  useExamConverterAuthenticatedRuntime();
const {
  loadReviewArtifacts,
  projection: reviewProjection,
  resetReviewArtifacts,
  setReviewArtifactsForInspection,
  status: reviewStatus,
} = useExamConverterReviewArtifacts();
const activeInspectionMode = ref<ExamConverterInspectionMode>("questions");
const acceptedCurrentState = ref(false);
const advisoryRetryAttempt = ref(0);
const aiSuggestionFocusKey = ref(0);
const focusedAiPrefill = ref<ExamConverterAiPrefillFocus>("questions");
const {
  downloadFile,
  fileActionStates,
  resetFileActions,
  saveFile,
} = useExamConverterFileActions();
const {
  applyItemTextPatch: handleApplyItemTextPatch,
  applyManualAnswerKey: handleApplyManualAnswerKey,
  applyPointCorrection: handleApplyPointCorrection,
  applyReviewDecision,
  correctionProjectionFreshness,
  isCorrectionApplying,
  refreshPersistedCorrections,
  resetCorrectionSessionState,
  savedCorrectionIntentCount,
} = useExamConverterUnifiedCorrections({
  acceptedCurrentState,
  activeInspectionMode,
  failConversion,
  finishConversion,
  isConversionRunning,
  lastConversionHubJobId,
  lastCorrelationId,
  lastJobId,
  resetFileActions,
  reviewProjection,
  runtime: {
    issueCorrectionSourceState,
  },
});

const isExamConverterBusy = computed(
  () => isConversionRunning.value || isCorrectionApplying.value,
);

const hasSelectedTargetFormat = computed(
  () => selectedTargetFormats.value.pdf || selectedTargetFormats.value.qti,
);

const canStartConversion = computed(
  () =>
    selectedSourceFile.value !== null &&
    hasSelectedTargetFormat.value &&
    !isExamConverterBusy.value,
);

const requiresReviewDecision = computed(() => {
  const projection = reviewProjection.value;
  return (
    projection !== null &&
    projection.acceptedStateOverlay !== null &&
    projection.report.aiSuggestionCount === 0 &&
    savedCorrectionIntentCount.value === 0 &&
    (visibleReviewIssueCount(projection) > 0 ||
      projection.report.blockedTargetFileCount > 0) &&
    !acceptedCurrentState.value
  );
});

function visibleReviewIssueCount(projection: ExamConverterReviewProjection): number {
  return projection.questions.filter(
    (question) => visibleMissingFieldsForQuestion(question).length > 0,
  ).length;
}

const canUseFiles = computed(() => {
  const freshness = correctionProjectionFreshness.value;
  return reviewProjection.value !== null && freshness !== "unavailable" && freshness !== "stale_source" && freshness !== "conflict";
});

const correctionSessionStatusLabel = computed(() => {
  if (correctionProjectionFreshness.value === "conflict") {
    return "Det gick inte att spara ändringen eftersom provet ändrades samtidigt. Läs in provet på nytt och försök igen.";
  }
  if (correctionProjectionFreshness.value === "stale_source") {
    return "Provet har ändrats sedan ändringarna sparades. Läs in provet på nytt innan du skapar filer.";
  }
  return null;
});

const fileActionNotice = computed(() => {
  if (correctionProjectionFreshness.value === "unavailable") {
    return "Det går inte att hämta filerna just nu.";
  }
  if (correctionProjectionFreshness.value === "stale_source") {
    return "Läs in provet på nytt innan du hämtar filer.";
  }
  if (correctionProjectionFreshness.value === "conflict") {
    return "Lös sparfelet innan du hämtar filer.";
  }
  return null;
});

const showAiPrefillPanel = computed(() => {
  return (
    (reviewProjection.value?.report.aiSuggestionCount ?? 0) > 0
  );
});

const canRetryAdvisoryFacitSuggestion = computed(() => {
  return (
    !isConversionRunning.value &&
    !isCorrectionApplying.value &&
    isProviderOnlyAdvisoryFailureReport(
      reviewProjection.value?.answerKeyCompletionReport ?? null,
    )
  );
});

function handleResetLocalChoices(): void {
  cancelRuntime();
  clearLastJobHandle();
  resetReviewArtifacts();
  resetCorrectionSessionState();
  resetFileActions();
  acceptedCurrentState.value = false;
  advisoryRetryAttempt.value = 0;
  focusedAiPrefill.value = "questions";
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
      visibleReviewIssueCount(projection) > 0 ||
      projection.report.blockedTargetFileCount > 0;
    activeInspectionMode.value = preferredMode ?? projection.defaultMode;
    finishConversion({
      ...runtimeOutcome,
      bundleStatus: requiresQuestionReview ? runtimeOutcome.bundleStatus : "complete",
      manualFollowUpRequired: requiresQuestionReview,
      manualFollowUpCount: visibleReviewIssueCount(projection),
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
  resetCorrectionSessionState();
  resetFileActions();
  acceptedCurrentState.value = false;
  advisoryRetryAttempt.value = 0;
  focusedAiPrefill.value = "questions";
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
      await refreshPersistedCorrections();
    }
  } catch {
    failConversion();
  }
}

async function handleRetryAdvisoryFacitSuggestion(): Promise<void> {
  const sourceSelection = selectedSourceFile.value;
  if (!sourceSelection || !canRetryAdvisoryFacitSuggestion.value) {
    return;
  }

  const nextRetryAttempt = advisoryRetryAttempt.value + 1;
  advisoryRetryAttempt.value = nextRetryAttempt;
  resetReviewArtifacts();
  resetFileActions();
  acceptedCurrentState.value = false;
  focusedAiPrefill.value = "questions";
  activeInspectionMode.value = "questions";
  startConversion();
  try {
    const result = await submitAndPoll({
      advisoryRetryAttempt: nextRetryAttempt,
      completionMode: DIGIEXAM_COMPLETION_MODE_SUGGEST_MISSING_MACHINE_MARKED,
      sourceFile: sourceSelection.file,
      supportingFile: selectedSupportingFile.value?.file ?? null,
      targetSelection: { ...selectedTargetFormats.value },
    });
    if (result) {
      await finishRuntimeResult(result, null, true);
      await refreshPersistedCorrections();
    }
  } catch {
    failConversion();
  }
}

function selectInspectionMode(mode: ExamConverterInspectionMode): void {
  activeInspectionMode.value = mode;
}

function handleOpenQuestions(): void {
  activeInspectionMode.value = "questions";
  aiSuggestionFocusKey.value += 1;
}

function focusAiPrefill(focus: ExamConverterAiPrefillFocus): void {
  focusedAiPrefill.value = focus;
}

async function handleAcceptCurrentState(): Promise<void> {
  const overlay = reviewProjection.value?.acceptedStateOverlay ?? null;
  if (!overlay || isExamConverterBusy.value) {
    return;
  }
  if (await applyReviewDecision()) {
    activeInspectionMode.value = "files";
  }
}

async function handleDownloadFile(file: ExamConverterReviewFile): Promise<void> {
  const correlationId = lastCorrelationId.value;
  const jobId = lastJobId.value;
  if (
    !correlationId ||
    !jobId ||
    !canUseFiles.value ||
    !file.exportEnabled ||
    !file.artifactActionReference
  ) {
    return;
  }
  await downloadFile({ correlationId, file, jobId });
}

async function handleSaveFile(file: ExamConverterReviewFile): Promise<void> {
  const correlationId = lastCorrelationId.value;
  const jobId = lastJobId.value;
  if (
    !correlationId ||
    !jobId ||
    !canUseFiles.value ||
    !file.exportEnabled ||
    !file.artifactActionReference
  ) {
    return;
  }
  await saveFile({ correlationId, file, jobId });
}

onMounted(async () => {
  if (!props.inspectionFixtureId) {
    const handle = restoreLastJobHandle();
    if (handle) {
      try {
        const projection = await loadReviewArtifacts({
          completionReportRequired: false,
          correlationId: handle.correlationId,
          jobId: handle.sirConvertJobId,
        });
        if (projection) {
          activeInspectionMode.value = projection.defaultMode;
          finishConversion({
            artifactCount: projection.files.length,
            bundleStatus:
              visibleReviewIssueCount(projection) > 0 ? "needs_review" : "complete",
            manualFollowUpCount: visibleReviewIssueCount(projection),
            manualFollowUpRequired: visibleReviewIssueCount(projection) > 0,
            warningCount: projection.report.warningCount,
          });
          await refreshPersistedCorrections();
        }
      } catch {
        clearLastJobHandle();
        failConversion();
      }
    }
    return;
  }
  if (!import.meta.env.DEV && import.meta.env.MODE !== "test") {
    failConversion();
    return;
  }
  const { getExamConverterUiInspectionFixture } = await import(
    "./exam-converter-authenticated/examConverterUiInspectionFixtures"
  );
  const fixture = getExamConverterUiInspectionFixture(props.inspectionFixtureId);
  if (!fixture) {
    failConversion();
    return;
  }
  selectSourceFile(fixture.sourceFile);
  resetFileActions();
  acceptedCurrentState.value = false;
  focusedAiPrefill.value = "questions";
  activeInspectionMode.value = fixture.activeInspectionMode;
  setReviewArtifactsForInspection(fixture.projection);
  finishConversion(fixture.runtimeOutcome);
});
</script>

<template>
  <main
    class="min-h-[calc(100vh-72px)] overflow-x-hidden bg-canvas px-3 py-4 text-navy md:px-5 lg:px-6"
    aria-labelledby="exam-converter-auth-title"
  >
    <section
      class="mx-auto grid min-h-[28rem] w-full min-w-0 max-w-[90rem] grid-cols-1 items-stretch border border-navy bg-panel shadow-brutal-sm xl:grid-cols-[minmax(14rem,17rem)_minmax(0,1fr)] 2xl:grid-cols-[minmax(15rem,18rem)_minmax(0,1fr)]"
      aria-label="Exam Converter"
      :data-inspection-fixture-id="inspectionFixtureId ?? undefined"
      data-test="exam-converter-host-frame"
    >
      <ExamConverterWorkflowRailShell
        :can-start-conversion="canStartConversion"
        :is-conversion-running="isExamConverterBusy"
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
      <div class="min-w-0">
        <p
          v-if="correctionSessionStatusLabel"
          class="border-b border-navy bg-saffron px-4 py-2 text-xs font-black uppercase tracking-normal"
          data-test="exam-converter-correction-session-status"
        >
          {{ correctionSessionStatusLabel }}
        </p>
        <ExamConverterWorkspaceShell
          :active-inspection-mode="activeInspectionMode"
          :accepted-current-state="acceptedCurrentState"
          :ai-suggestion-focus-key="aiSuggestionFocusKey"
          :can-retry-advisory-facit-suggestion="canRetryAdvisoryFacitSuggestion"
          :can-use-files="canUseFiles"
          :file-action-states="fileActionStates"
          :file-action-notice="fileActionNotice"
          :focused-ai-prefill="focusedAiPrefill"
          :is-correction-applying="isCorrectionApplying"
          :result-strip="resultStrip"
          :review-projection="reviewProjection"
          :requires-review-decision="requiresReviewDecision"
          :review-status="reviewStatus"
          :selected-source-file="selectedSourceFile"
          :show-ai-prefill-panel="showAiPrefillPanel"
          :source-file-error="sourceFileError"
          @accept-current-state="handleAcceptCurrentState"
          @apply-item-text-patch="handleApplyItemTextPatch"
          @apply-manual-answer-key="handleApplyManualAnswerKey"
          @apply-point-correction="handleApplyPointCorrection"
          @download-file="handleDownloadFile"
          @files-dropped="selectDroppedFiles"
          @inspection-mode-selected="selectInspectionMode"
          @open-questions="handleOpenQuestions"
          @ai-prefill-focused="focusAiPrefill"
          @retry-advisory-facit-suggestion="handleRetryAdvisoryFacitSuggestion"
          @save-file="handleSaveFile"
          @source-file-selected="selectSourceFile"
        />
      </div>
    </section>
  </main>
</template>
