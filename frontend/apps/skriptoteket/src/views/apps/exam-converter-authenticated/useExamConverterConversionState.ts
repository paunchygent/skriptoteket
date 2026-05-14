/**
 * Exam Converter conversion state scaffold.
 *
 * Domain purpose:
 *   Own the authenticated Exam Converter's teacher-visible conversion phase
 *   and terminal result-strip mapping after runtime polling completes.
 *
 * Relationships:
 *   - Used by `ExamConverterAuthenticatedView`.
 *   - Feeds `ExamConverterResultStrip` with approved teacher-facing copy.
 *   - Stays independent of Gateway clients, Sir Convert DTOs, and save flows.
 */

import { computed, onBeforeUnmount, ref } from "vue";

export type ExamConverterConversionStatus =
  | "idle"
  | "running"
  | "success"
  | "partial"
  | "failed";

export type ExamConverterResultTone = "info" | "success" | "warning" | "error";

export type ExamConverterRunningProgress = {
  elapsedSeconds: number;
  isLongRunning: boolean;
  percent: number;
  stageLabel: string;
};

export type ExamConverterRuntimeOutcome = {
  artifactCount: number;
  bundleStatus: "complete" | "partial" | "blocked";
  manualFollowUpCount: number | null;
  manualFollowUpRequired: boolean;
  warningCount: number;
};

export type ExamConverterResultStripState = {
  actionLabel: string | null;
  detail: string | null;
  nextAction: string | null;
  progress: ExamConverterRunningProgress | null;
  status: Exclude<ExamConverterConversionStatus, "idle">;
  title: string;
  tone: ExamConverterResultTone;
};

type StaticResultStripState = Omit<ExamConverterResultStripState, "progress">;

const LONG_RUNNING_SECONDS = 10;
const RESULT_STRIP_BY_STATUS: Record<
  Exclude<ExamConverterConversionStatus, "idle" | "running">,
  StaticResultStripState
> = {
  success: {
    actionLabel: "Öppna frågor",
    detail: null,
    nextAction: "Kontrollera frågorna innan du sparar eller hämtar filer.",
    status: "success",
    title: "Provet är konverterat",
    tone: "success",
  },
  partial: {
    actionLabel: "Öppna frågor",
    detail: "Några frågor behöver ses över innan provet är klart.",
    nextAction: "Kontrollera frågorna som behöver ses över.",
    status: "partial",
    title: "Konverteringen av provet lyckades delvis",
    tone: "warning",
  },
  failed: {
    actionLabel: null,
    detail: null,
    nextAction: "Kontrollera provfilen och försök igen.",
    status: "failed",
    title: "Konverteringen av provet misslyckades",
    tone: "error",
  },
};

const RUNNING_STAGES = [
  { label: "Förbereder konverteringen", maxPercent: 22 },
  { label: "Läser provfilen", maxPercent: 44 },
  { label: "Skapar målformat", maxPercent: 68 },
  { label: "Kontrollerar resultatet", maxPercent: 100 },
] as const;

function progressPercentForElapsed(elapsedSeconds: number): number {
  if (elapsedSeconds <= 0) {
    return 8;
  }
  if (elapsedSeconds < LONG_RUNNING_SECONDS) {
    return Math.min(72, 8 + elapsedSeconds * 7);
  }
  return Math.min(92, 72 + (elapsedSeconds - LONG_RUNNING_SECONDS) * 2);
}

function stageLabelForPercent(percent: number): string {
  return RUNNING_STAGES.find((stage) => percent <= stage.maxPercent)?.label ?? "Arbetar vidare";
}

function buildRunningProgress(elapsedSeconds: number): ExamConverterRunningProgress {
  const percent = progressPercentForElapsed(elapsedSeconds);
  return {
    elapsedSeconds,
    isLongRunning: elapsedSeconds >= LONG_RUNNING_SECONDS,
    percent,
    stageLabel: stageLabelForPercent(percent),
  };
}

function statusForRuntimeOutcome(
  outcome: ExamConverterRuntimeOutcome,
): Exclude<ExamConverterConversionStatus, "idle" | "running"> {
  if (outcome.bundleStatus === "blocked") {
    return "failed";
  }
  if (
    outcome.bundleStatus === "partial" ||
    outcome.manualFollowUpRequired ||
    outcome.warningCount > 0
  ) {
    return "partial";
  }
  return "success";
}

function buildPartialDetail(outcome: ExamConverterRuntimeOutcome | null): string {
  if (outcome?.manualFollowUpCount && outcome.manualFollowUpCount > 0) {
    return `${outcome.manualFollowUpCount.toLocaleString("sv-SE")} frågor behöver ses över innan provet är klart.`;
  }
  return "Några frågor behöver ses över innan provet är klart.";
}

function buildResultStripState(params: {
  status: ExamConverterConversionStatus;
  progress: ExamConverterRunningProgress;
  runtimeOutcome: ExamConverterRuntimeOutcome | null;
}): ExamConverterResultStripState | null {
  const { progress, runtimeOutcome, status } = params;
  if (status === "idle") {
    return null;
  }
  if (status === "running") {
    return {
      actionLabel: null,
      detail: null,
      nextAction: null,
      progress,
      status: "running",
      title: "Konverterar provet...",
      tone: "info",
    };
  }
  if (status === "partial") {
    return {
      ...RESULT_STRIP_BY_STATUS.partial,
      detail: buildPartialDetail(runtimeOutcome),
      progress: null,
    };
  }
  return { ...RESULT_STRIP_BY_STATUS[status], progress: null };
}

export function useExamConverterConversionState() {
  const conversionStatus = ref<ExamConverterConversionStatus>("idle");
  const runningElapsedSeconds = ref(0);
  const runtimeOutcome = ref<ExamConverterRuntimeOutcome | null>(null);
  let runningTimer: ReturnType<typeof window.setInterval> | null = null;

  const isConversionRunning = computed(() => conversionStatus.value === "running");
  const runningProgress = computed(() =>
    buildRunningProgress(runningElapsedSeconds.value),
  );
  const resultStrip = computed(() =>
    buildResultStripState({
      progress: runningProgress.value,
      runtimeOutcome: runtimeOutcome.value,
      status: conversionStatus.value,
    }),
  );

  function stopRunningTimer(): void {
    if (runningTimer) {
      window.clearInterval(runningTimer);
      runningTimer = null;
    }
  }

  function resetConversion(): void {
    stopRunningTimer();
    runningElapsedSeconds.value = 0;
    runtimeOutcome.value = null;
    conversionStatus.value = "idle";
  }

  function startConversion(): void {
    stopRunningTimer();
    runningElapsedSeconds.value = 0;
    runtimeOutcome.value = null;
    conversionStatus.value = "running";
    runningTimer = window.setInterval(() => {
      runningElapsedSeconds.value += 1;
    }, 1_000);
  }

  function finishConversion(outcome: ExamConverterRuntimeOutcome): void {
    stopRunningTimer();
    runningElapsedSeconds.value = 0;
    runtimeOutcome.value = outcome;
    conversionStatus.value = statusForRuntimeOutcome(outcome);
  }

  function failConversion(): void {
    stopRunningTimer();
    runningElapsedSeconds.value = 0;
    runtimeOutcome.value = null;
    conversionStatus.value = "failed";
  }

  onBeforeUnmount(stopRunningTimer);

  return {
    conversionStatus,
    failConversion,
    finishConversion,
    isConversionRunning,
    resetConversion,
    resultStrip,
    startConversion,
  };
}
