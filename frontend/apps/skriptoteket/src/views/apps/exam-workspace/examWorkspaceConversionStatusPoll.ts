/**
 * Exam workspace conversion status polling.
 *
 * Domain purpose:
 *   Follow one DOCX/DigiExam conversion from its import status until the
 *   open copy holds the final revision. Each status names exactly the
 *   placeholders its revision holds, so the open copy's lock follows the
 *   response it stands on. The door's daily limit is terminal for the page
 *   session: the status message already says so, and the Word import disables
 *   on the flag with no toast.
 *
 * Relationships:
 *   - Used by `useExamWorkspaceConversion` through the shared conversion
 *     runtime; revision application is injected so this module never merges.
 *   - Delegates transport to the exam workspace store's teacher services.
 */

import { computed } from "vue";

import type { ExamWorkspaceConversionStatus } from "../../../api/examWorkspace";
import {
  aiLimitFromError,
  aiTryAgainFromError,
  aiLimitFromStatus,
  aiLimitNote,
  markAiDailyLimit,
} from "../../../composables/aiDailyLimit";
import type { ExamWorkspaceConversionRuntime } from "./examWorkspaceConversionShared";
import {
  finishConversion,
  holdsConversionRevision,
  IMPORT_FAILURE_COPY,
  isFinishedStatus,
  scheduleConversionPoll,
  stopConversionPolling,
} from "./examWorkspaceConversionShared";

export const STATUS_FAILURE_COPY =
  "Det gick inte att hämta konverteringen eller öppna provet. Försöker igen …";

export function createConversionStatusPoll(
  runtime: ExamWorkspaceConversionRuntime,
  applyRevision: (
    status: ExamWorkspaceConversionStatus,
    pollGeneration: number,
    duringSave?: boolean,
  ) => Promise<boolean>,
) {
  const { binding } = runtime;

  const conversionProgress = computed(() => {
    const status = runtime.conversionStatus.value;
    if (!runtime.isConverting.value || !status || status.questions_total === 0) return null;
    return { done: status.questions_done, total: status.questions_total };
  });

  const conversionMessage = computed(() => {
    const progress = conversionProgress.value;
    if (progress) {
      return `Konverterar provet: ${progress.done} av ${progress.total} frågor klara.`;
    }
    if (runtime.isConverting.value) return "Konverterar provet …";
    if (runtime.conversionStatus.value?.state === "failed") {
      return runtime.conversionStatus.value.error_message ?? IMPORT_FAILURE_COPY;
    }
    return runtime.conversionError.value;
  });

  /** The open document is the followed import's, so the teacher may edit it while batches arrive. */
  const isEditingConversion = computed(
    () =>
      runtime.shownUnits.value !== null &&
      binding.summary.value?.lineage_id === runtime.conversionStatus.value?.lineage_id,
  );

  /**
   * Placeholders of the revision the open copy stands on. A newer status can
   * arrive while its revision waits for an in-flight save, so a placeholder
   * stays locked until its batch is merged into the open copy.
   */
  const convertingItemIds = computed<ReadonlySet<string>>(() => {
    if (!isEditingConversion.value) return new Set();
    return new Set(
      (runtime.shownUnits.value ?? [])
        .filter((unit) => unit.state === "converting")
        .flatMap((unit) => unit.item_ids),
    );
  });

  /**
   * Take the conversion state of a server response the open copy now stands
   * on. Its units name exactly the placeholders that revision holds, so they
   * become the lock. An unfinished conversion is followed; a finished one
   * means the response holds every result, so following ends.
   */
  function adoptConversion(
    response: { conversion: ExamWorkspaceConversionStatus | null },
  ): void {
    const conversion = response.conversion;
    const following =
      runtime.isConverting.value &&
      conversion !== null &&
      runtime.conversionStatus.value?.job_id === conversion.job_id;
    if (conversion !== null && !isFinishedStatus(conversion)) {
      runtime.shownUnits.value = conversion.units;
      // While following, the poll owns the status: a save response can carry an older one.
      if (!following) {
        runtime.conversionStatus.value = conversion;
        runtime.poll.generation += 1;
        runtime.isConverting.value = true;
        runtime.conversionError.value = null;
        runtime.poll.failures = 0;
        scheduleConversionPoll(runtime, runtime.poll.generation, (gen) => {
          void refreshConversion(gen);
        });
      }
      return;
    }
    if (following) {
      finishConversion(runtime, conversion);
      return;
    }
    if (runtime.isConverting.value) {
      // The teacher opened another exam: its conversion is followed again when reopened.
      runtime.poll.generation += 1;
      runtime.isConverting.value = false;
      stopConversionPolling(runtime);
    }
    runtime.shownUnits.value = null;
    runtime.conversionStatus.value = null;
    runtime.conversionError.value = null;
  }

  async function applyConversionStatus(
    status: ExamWorkspaceConversionStatus,
    pollGeneration: number,
  ): Promise<void> {
    if (pollGeneration !== runtime.poll.generation) return;
    runtime.conversionStatus.value = status;
    // The door's daily limit is terminal for the page session: the status
    // message already says so, and the Word import disables on the flag.
    const limit = aiLimitFromStatus(status);
    if (limit !== null) {
      markAiDailyLimit(limit);
    }
    const deferred = await applyRevision(status, pollGeneration);
    // Adopting the fetched revision may already have ended or replaced this poll chain.
    if (pollGeneration !== runtime.poll.generation || !runtime.isConverting.value) return;
    if (deferred || !holdsConversionRevision(binding.summary.value, status)) {
      scheduleConversionPoll(runtime, pollGeneration, (gen) => {
        void refreshConversion(gen);
      });
    } else if (isFinishedStatus(status)) {
      finishConversion(runtime, status);
    } else {
      runtime.poll.failures = 0;
      scheduleConversionPoll(runtime, pollGeneration, (gen) => {
        void refreshConversion(gen);
      });
    }
  }

  async function runStatusRequest(
    status: ExamWorkspaceConversionStatus,
    pollGeneration: number,
  ): Promise<void> {
    const teacher = binding.store.teacher;
    if (!teacher) return;
    try {
      const next = isFinishedStatus(status)
        ? status
        : await teacher.getExamWorkspaceConversionStatus(status.job_id);
      await applyConversionStatus(next, pollGeneration);
      if (pollGeneration === runtime.poll.generation) {
        runtime.poll.failures = 0;
        runtime.conversionError.value = null;
      }
    } catch (error) {
      if (pollGeneration !== runtime.poll.generation) return;
      // No toast for the door's limit: the Öppna drawer names it inline.
      const limit = aiLimitFromError(error);
      if (limit !== null) {
        markAiDailyLimit(limit);
        runtime.conversionError.value = aiLimitNote(limit);
      } else {
        runtime.conversionError.value = aiTryAgainFromError(error) ?? STATUS_FAILURE_COPY;
      }
      runtime.poll.failures += 1;
      scheduleConversionPoll(runtime, pollGeneration, (gen) => {
        void refreshConversion(gen);
      });
    }
  }

  async function refreshConversion(pollGeneration: number): Promise<void> {
    const status = runtime.conversionStatus.value;
    if (!status || runtime.poll.request || !runtime.isConverting.value) return;
    const request = runStatusRequest(status, pollGeneration).finally(() => {
      runtime.poll.request = null;
    });
    runtime.poll.request = request;
    await request;
  }

  function retryConversionStatus(): void {
    stopConversionPolling(runtime);
    void refreshConversion(runtime.poll.generation);
  }

  return {
    adoptConversion,
    conversionMessage,
    conversionProgress,
    convertingItemIds,
    isEditingConversion,
    refreshConversion,
    retryConversionStatus,
  };
}
