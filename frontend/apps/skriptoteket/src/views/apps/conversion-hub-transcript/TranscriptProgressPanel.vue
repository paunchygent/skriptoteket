<script setup lang="ts">
/**
 * Transcript progress panel.
 *
 * Domain purpose:
 *   Render truthful transcript conversion progress before transcript content
 *   exists, using Sir Convert's observed chunk facts and Task-364 pipeline
 *   estimates without exposing producer jargon.
 *
 * Relationships:
 *   - Used by `TranscriptWorkspaceShell` for the running transcript state.
 *   - Reads display helpers from `transcriptProgressDisplay`.
 */

import { computed } from "vue";
import { Info } from "lucide-vue-next";

import type { SirConvertTranscriptJob } from "../../../api/sirConvertGateway";
import type { TranscriptAbortState, TranscriptUploadState } from "./useTranscriptGatewayRuntime";
import {
  isUploading,
  transcriptProgressLabel,
  uploadProgressBytes,
  uploadProgressLabel,
} from "./transcriptProgressDisplay";

const props = defineProps<{
  abortState: TranscriptAbortState;
  currentJob: SirConvertTranscriptJob | null;
  uploadState: TranscriptUploadState;
}>();

type ProgressStep = "speakers" | "transcription" | "finalizing";

const uploadPercentValue = computed(() => {
  if (props.currentJob || !isUploading(props.uploadState)) return null;
  const percent = props.uploadState.percentComplete;
  if (percent === null || percent === undefined || percent <= 0) return null;
  return Math.max(0, Math.min(100, percent));
});
const uploadPercentLabel = computed(() =>
  uploadPercentValue.value === null ? null : `${Math.round(uploadPercentValue.value)} %`,
);
const phaseLabel = computed(() =>
  !props.currentJob && isUploading(props.uploadState)
    ? uploadProgressLabel(props.uploadState)
    : transcriptProgressLabel(props.currentJob),
);
const uploadProgressBarStyle = computed(() => ({
  width: `${uploadPercentValue.value ?? 0}%`,
}));
const shouldShowAbortState = computed(() => props.abortState.message !== null);

function activeStep(job: SirConvertTranscriptJob | null): ProgressStep {
  const phase = job?.progress.phase;
  if (phase === "transcribing") return "transcription";
  if (phase === "aligning_segments" || phase === "packaging") return "finalizing";
  return "speakers";
}

function stepState(step: ProgressStep): "done" | "active" | "todo" {
  if (!props.currentJob) return "todo";
  const active = activeStep(props.currentJob);
  const order: readonly ProgressStep[] = ["speakers", "transcription", "finalizing"];
  const stepIndex = order.indexOf(step);
  const activeIndex = order.indexOf(active);
  if (stepIndex < activeIndex) return "done";
  if (stepIndex === activeIndex) return "active";
  return "todo";
}

function stepClasses(step: ProgressStep): string {
  const state = stepState(step);
  if (state === "todo") return "border-navy/35 bg-panel text-navy";
  return "border-navy bg-navy text-canvas";
}
</script>

<template>
  <div
    class="grid min-h-0 w-full flex-1 place-items-center bg-canvas px-4 py-6 text-center"
    data-test="transcript-running-surface"
  >
    <div class="grid w-full max-w-[39rem] gap-6 border border-navy/25 bg-panel px-5 py-6 shadow-brutal-sm sm:px-8">
      <div>
        <h3
          class="text-2xl font-semibold leading-tight text-navy"
          data-test="transcript-progress-title"
        >
          Vi skapar ditt transkript
        </h3>
        <p class="mt-2 text-sm leading-snug text-navy/70">
          Transkriptet visas här när arbetet är klart.
        </p>
      </div>

      <div
        v-if="currentJob"
        class="grid grid-cols-3 gap-2"
        aria-label="Aktuellt arbete"
        data-test="transcript-progress-steps"
      >
        <div class="grid justify-items-center gap-2 text-xs font-semibold leading-tight text-navy">
          <span>Hittar talare</span>
          <span
            class="grid h-8 w-8 place-items-center border text-xs font-black"
            :class="stepClasses('speakers')"
          >1</span>
        </div>
        <div class="grid justify-items-center gap-2 text-xs font-semibold leading-tight text-navy">
          <span>Skriver ut samtalet</span>
          <span
            class="grid h-8 w-8 place-items-center border text-xs font-black"
            :class="stepClasses('transcription')"
          >2</span>
        </div>
        <div class="grid justify-items-center gap-2 text-xs font-semibold leading-tight text-navy">
          <span>Gör texten klar</span>
          <span
            class="grid h-8 w-8 place-items-center border text-xs font-black"
            :class="stepClasses('finalizing')"
          >3</span>
        </div>
      </div>

      <div class="grid gap-3">
        <p
          class="text-base font-semibold leading-tight text-navy"
          data-test="transcript-progress-phase"
        >
          {{ phaseLabel }}
        </p>
        <p
          v-if="uploadPercentLabel"
          class="text-4xl font-black leading-none text-navy"
          data-test="transcript-progress-percent"
        >
          {{ uploadPercentLabel }}
        </p>
        <div
          v-if="uploadPercentValue !== null"
          class="h-4 border-2 border-navy bg-canvas"
          aria-label="Uppladdningsprogress"
          :aria-valuenow="uploadPercentValue"
          aria-valuemin="0"
          aria-valuemax="100"
          role="progressbar"
        >
          <div
            class="h-full bg-navy transition-[width]"
            :style="uploadProgressBarStyle"
          />
        </div>
      </div>

      <dl
        v-if="!currentJob && uploadProgressBytes(uploadState)"
        class="grid min-h-[2rem] grid-cols-1 gap-2 text-left text-xs font-semibold leading-snug text-navy/75"
      >
        <div
          data-test="transcript-upload-bytes"
        >
          <dt>Uppladdning</dt>
          <dd>{{ uploadProgressBytes(uploadState) }}</dd>
        </div>
      </dl>

      <div
        class="grid min-h-[4.25rem] grid-cols-[auto_minmax(0,1fr)] items-center gap-3 border border-navy/15 bg-canvas px-4 py-3 text-left"
        data-test="transcript-progress-current-step"
      >
        <Info
          class="h-5 w-5 text-navy"
          aria-hidden="true"
        />
        <div>
          <p class="text-sm font-semibold leading-tight text-navy">
            Vi arbetar med ljudet.
          </p>
          <p class="mt-1 text-xs leading-snug text-navy/65">
            Transkriptet visas automatiskt när det är klart.
          </p>
        </div>
      </div>

      <p
        class="min-h-[2.5rem] border px-3 py-2 text-xs font-medium leading-snug"
        :class="
          shouldShowAbortState
            ? 'border-warning/35 bg-warning/10 text-navy'
            : 'invisible border-transparent bg-transparent text-transparent'
        "
        data-test="transcript-abort-state"
        :aria-hidden="shouldShowAbortState ? undefined : true"
        :aria-live="shouldShowAbortState ? 'polite' : 'off'"
      >
        {{ abortState.message ?? "" }}
      </p>
    </div>
  </div>
</template>
