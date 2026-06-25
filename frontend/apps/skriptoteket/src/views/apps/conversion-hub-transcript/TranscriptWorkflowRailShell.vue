<script setup lang="ts">
/**
 * Transcript workflow rail shell.
 *
 * Domain purpose:
 *   Present transcript file intake, speaker controls, submit, cancel, and reset
 *   actions for the authenticated Conversion Hub transcript lane.
 *
 * Relationships:
 *   - Rendered by `ConversionHubTranscriptHost`.
 *   - Receives local intake state from `useTranscriptSourceFile`.
 */

import { Check, FileAudio, Play, Upload, X } from "lucide-vue-next";

import { TRANSCRIPT_COMMAND_BUTTON_CLASS } from "./transcriptCommandButtonClasses";
import type {
  TranscriptSourceFileSelection,
  TranscriptSpeakerMode,
} from "./useTranscriptSourceFile";
import type { TranscriptAbortState } from "./useTranscriptGatewayRuntime";

defineProps<{
  abortState: TranscriptAbortState;
  canStartTranscript: boolean;
  isRunning: boolean;
  maxSpeakers: number;
  minSpeakers: number;
  selectedTranscriptFile: TranscriptSourceFileSelection | null;
  speakerCount: number;
  speakerError: string | null;
  speakerMode: TranscriptSpeakerMode;
  transcriptFileError: string | null;
}>();

const emit = defineEmits<{
  cancelTranscript: [];
  clearTranscriptFile: [];
  maxSpeakersChanged: [value: number];
  minSpeakersChanged: [value: number];
  resetTranscriptChoices: [];
  speakerCountChanged: [value: number];
  speakerModeChanged: [mode: TranscriptSpeakerMode];
  startTranscript: [];
  transcriptFileSelected: [file: File];
}>();

function firstFile(fileList: FileList | null): File | null {
  const [file] = Array.from(fileList ?? []);
  return file ?? null;
}

function handleFileInput(event: Event): void {
  const input = event.target as HTMLInputElement;
  const file = firstFile(input.files);
  if (file) {
    emit("transcriptFileSelected", file);
  }
  input.value = "";
}

function numericInputValue(event: Event): number {
  return Number((event.target as HTMLInputElement).value);
}
</script>

<template>
  <aside
    class="border-b border-navy/20 bg-panel p-4 min-[821px]:border-b-0 min-[821px]:border-r"
    aria-labelledby="transcript-workflow-title"
    data-test="transcript-workflow-rail-shell"
  >
    <h1
      id="transcript-workflow-title"
      class="text-base font-semibold leading-tight text-navy"
    >
      Transkribera samtal
    </h1>

    <div class="mt-5 grid gap-6">
      <section class="grid gap-2">
        <h2 class="text-sm font-semibold leading-tight text-navy">
          1. Ljud eller video
        </h2>
        <div
          v-if="selectedTranscriptFile"
          class="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 border border-navy/25 bg-panel px-3 py-3"
          data-test="transcript-selected-source-file"
        >
          <FileAudio
            class="h-5 w-5 text-navy"
            aria-hidden="true"
          />
          <span class="min-w-0">
            <span class="block truncate text-sm font-medium leading-snug text-navy">
              {{ selectedTranscriptFile.name }}
            </span>
            <span class="mt-0.5 block text-xs leading-none text-navy/65">
              {{ selectedTranscriptFile.sizeLabel }}
            </span>
          </span>
          <button
            type="button"
            class="grid h-7 w-7 place-items-center border border-navy/25 bg-panel-muted text-navy hover:bg-canvas"
            aria-label="Ta bort transkriptionsfil"
            :disabled="isRunning"
            @click="emit('clearTranscriptFile')"
          >
            <X
              class="h-4 w-4"
              aria-hidden="true"
            />
          </button>
        </div>
        <label
          v-else
          class="grid cursor-pointer grid-cols-[auto_minmax(0,1fr)] items-center gap-3 border border-navy/25 bg-panel px-3 py-3 hover:bg-canvas"
          :class="isRunning ? 'cursor-not-allowed opacity-60' : undefined"
        >
          <input
            class="sr-only"
            type="file"
            accept=".wav,.mp3,.m4a,.aac,.flac,.ogg,.opus,.webm,.aiff,.mp4,.mov,.mkv"
            data-test="transcript-source-file-input"
            :disabled="isRunning"
            @change="handleFileInput"
          >
          <Upload
            class="h-5 w-5 text-action"
            aria-hidden="true"
          />
          <span class="min-w-0 text-sm font-medium leading-snug text-navy">
            Välj inspelning
          </span>
        </label>
        <p
          v-if="transcriptFileError"
          class="text-xs leading-snug text-error"
        >
          {{ transcriptFileError }}
        </p>
        <p
          v-else-if="selectedTranscriptFile"
          class="flex items-center gap-2 text-xs leading-snug text-success"
        >
          <Check
            class="h-3 w-3"
            aria-hidden="true"
          />
          Filen är vald
        </p>
        <p
          v-else
          class="text-xs leading-snug text-navy/65"
        >
          Ljudfiler och video med ljud kan användas.
        </p>
      </section>

      <section
        class="grid gap-2"
        data-test="transcript-speaker-controls"
      >
        <h2 class="text-sm font-semibold leading-tight text-navy">
          2. Talare
        </h2>
        <div class="grid gap-2">
          <button
            type="button"
            class="border px-3 py-2 text-left text-sm font-medium"
            :class="speakerMode === 'auto' ? 'border-navy bg-panel' : 'border-navy/20 bg-panel-muted'"
            data-test="transcript-speaker-mode-auto"
            :aria-pressed="speakerMode === 'auto'"
            :disabled="isRunning"
            @click="emit('speakerModeChanged', 'auto')"
          >
            Automatisk
          </button>
          <button
            type="button"
            class="border px-3 py-2 text-left text-sm font-medium"
            :class="speakerMode === 'known_speaker_count' ? 'border-navy bg-panel' : 'border-navy/20 bg-panel-muted'"
            data-test="transcript-speaker-mode-known"
            :aria-pressed="speakerMode === 'known_speaker_count'"
            :disabled="isRunning"
            @click="emit('speakerModeChanged', 'known_speaker_count')"
          >
            Exakt antal
          </button>
          <label
            v-if="speakerMode === 'known_speaker_count'"
            class="grid gap-1 text-xs font-semibold uppercase text-navy/70"
          >
            Antal talare
            <input
              class="border border-navy/30 bg-panel px-2 py-2 text-sm font-medium text-navy"
              type="number"
              min="1"
              :value="speakerCount"
              data-test="transcript-speaker-count"
              :disabled="isRunning"
              @input="emit('speakerCountChanged', numericInputValue($event))"
            >
          </label>
          <button
            type="button"
            class="border px-3 py-2 text-left text-sm font-medium"
            :class="speakerMode === 'speaker_range' ? 'border-navy bg-panel' : 'border-navy/20 bg-panel-muted'"
            data-test="transcript-speaker-mode-range"
            :aria-pressed="speakerMode === 'speaker_range'"
            :disabled="isRunning"
            @click="emit('speakerModeChanged', 'speaker_range')"
          >
            Intervall
          </button>
          <div
            v-if="speakerMode === 'speaker_range'"
            class="grid grid-cols-2 gap-2"
          >
            <label class="grid gap-1 text-xs font-semibold uppercase text-navy/70">
              Min
              <input
                class="border border-navy/30 bg-panel px-2 py-2 text-sm font-medium text-navy"
                type="number"
                min="1"
                :value="minSpeakers"
                data-test="transcript-min-speakers"
                :disabled="isRunning"
                @input="emit('minSpeakersChanged', numericInputValue($event))"
              >
            </label>
            <label class="grid gap-1 text-xs font-semibold uppercase text-navy/70">
              Max
              <input
                class="border border-navy/30 bg-panel px-2 py-2 text-sm font-medium text-navy"
                type="number"
                min="1"
                :value="maxSpeakers"
                data-test="transcript-max-speakers"
                :disabled="isRunning"
                @input="emit('maxSpeakersChanged', numericInputValue($event))"
              >
            </label>
          </div>
        </div>
        <p
          v-if="speakerError"
          class="text-xs leading-snug text-error"
        >
          {{ speakerError }}
        </p>
      </section>

      <section class="grid gap-3">
        <h2 class="text-sm font-semibold leading-tight text-navy">
          3. Starta
        </h2>
        <button
          type="button"
          :class="[
            TRANSCRIPT_COMMAND_BUTTON_CLASS,
            isRunning ? undefined : 'invisible pointer-events-none',
          ]"
          data-test="transcript-cancel"
          :aria-hidden="isRunning ? undefined : 'true'"
          :disabled="!isRunning || abortState.status === 'pending'"
          :tabindex="isRunning ? 0 : -1"
          @click="emit('cancelTranscript')"
        >
          {{ abortState.status === "pending" ? "Avbryter" : "Avbryt" }}
        </button>
        <button
          type="button"
          :class="TRANSCRIPT_COMMAND_BUTTON_CLASS"
          data-test="transcript-start"
          :disabled="!canStartTranscript || isRunning"
          @click="emit('startTranscript')"
        >
          <Play
            class="h-4 w-4"
            aria-hidden="true"
          />
          Starta transkribering
        </button>
        <button
          type="button"
          :class="TRANSCRIPT_COMMAND_BUTTON_CLASS"
          data-test="transcript-reset"
          @click="emit('resetTranscriptChoices')"
        >
          Rensa val
        </button>
      </section>
    </div>
  </aside>
</template>
