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

import { computed } from "vue";

import type { SirConvertTerminalResult } from "../../api/sirConvertGateway";
import ExamConverterWorkflowRailShell from "./exam-converter-authenticated/ExamConverterWorkflowRailShell.vue";
import ExamConverterWorkspaceShell from "./exam-converter-authenticated/ExamConverterWorkspaceShell.vue";
import { useExamConverterAuthenticatedRuntime } from "./exam-converter-authenticated/useExamConverterAuthenticatedRuntime";
import { useExamConverterConversionState } from "./exam-converter-authenticated/useExamConverterConversionState";
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
const { cancelRuntime, submitAndPoll } = useExamConverterAuthenticatedRuntime();

const hasSelectedTargetFormat = computed(
  () => selectedTargetFormats.value.pdf || selectedTargetFormats.value.qti,
);

const canStartConversion = computed(
  () =>
    selectedSourceFile.value !== null &&
    hasSelectedTargetFormat.value &&
    !isConversionRunning.value,
);

function handleResetLocalChoices(): void {
  cancelRuntime();
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

async function handleStartConversion(): Promise<void> {
  const sourceSelection = selectedSourceFile.value;
  if (!canStartConversion.value || !sourceSelection) {
    return;
  }

  startConversion();
  try {
    const result = await submitAndPoll({
      sourceFile: sourceSelection.file,
      supportingFile: selectedSupportingFile.value?.file ?? null,
      targetSelection: { ...selectedTargetFormats.value },
    });
    if (result) {
      finishConversion(toRuntimeOutcome(result));
    }
  } catch {
    failConversion();
  }
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
        :result-strip="resultStrip"
        :selected-source-file="selectedSourceFile"
        :source-file-error="sourceFileError"
        @files-dropped="selectDroppedFiles"
        @source-file-selected="selectSourceFile"
      />
    </section>
  </main>
</template>
