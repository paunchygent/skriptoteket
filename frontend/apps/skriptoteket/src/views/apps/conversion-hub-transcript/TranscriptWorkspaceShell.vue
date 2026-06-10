<script setup lang="ts">
/**
 * Transcript workspace shell.
 *
 * Domain purpose:
 *   Render the transcript lane's dominant work surface: idle drop zone,
 *   progress, recoverable failure, cancel state, and parsed JSON preview.
 *
 * Relationships:
 *   - Rendered by `ConversionHubTranscriptHost`.
 *   - Receives runtime state from `useTranscriptGatewayRuntime`.
 */

import { FileAudio, Upload } from "lucide-vue-next";

import type { SirConvertTranscriptJob, TranscriptJson } from "../../../api/sirConvertGateway";
import type { TranscriptRuntimeStatus } from "./useTranscriptGatewayRuntime";
import type { TranscriptSourceFileSelection } from "./useTranscriptSourceFile";

defineProps<{
  currentJob: SirConvertTranscriptJob | null;
  errorMessage: string | null;
  runtimeStatus: TranscriptRuntimeStatus;
  selectedTranscriptFile: TranscriptSourceFileSelection | null;
  transcript: TranscriptJson | null;
  transcriptFileError: string | null;
}>();

const emit = defineEmits<{
  filesDropped: [files: File[]];
  transcriptFileSelected: [file: File];
}>();

function transcriptProgressLabel(job: SirConvertTranscriptJob | null): string {
  if (!job) return "Förbereder ljudet.";
  if (job.status === "submitted" || job.status === "queued") {
    return "Väntar på att starta.";
  }
  const stage = job.stage;
  if (stage === "starting" || stage === "normalizing_audio") {
    return "Förbereder ljudet.";
  }
  if (stage === "probing_media") {
    return "Kontrollerar inspelningen.";
  }
  if (stage === "transcribing") {
    return "Skriver ut talet.";
  }
  if (stage === "diarizing") {
    return "Identifierar talare.";
  }
  if (stage === "aligning_segments") {
    return "Kontrollerar talare och text.";
  }
  if (stage === "packaging") {
    return "Förbereder transkriptet.";
  }
  return "Bearbetar inspelningen.";
}

function firstFile(fileList: FileList | null): File | null {
  const [file] = Array.from(fileList ?? []);
  return file ?? null;
}

function handleFileInput(event: Event): void {
  const input = event.target as HTMLInputElement;
  const file = firstFile(input.files);
  if (file) emit("transcriptFileSelected", file);
  input.value = "";
}

function handleDrop(event: DragEvent): void {
  event.preventDefault();
  const files = Array.from(event.dataTransfer?.files ?? []);
  if (files.length > 0) emit("filesDropped", files);
}
</script>

<template>
  <section
    class="flex h-full min-h-[26rem] min-w-0 flex-col bg-panel"
    aria-labelledby="transcript-workspace-title"
    data-test="transcript-workspace-shell"
  >
    <header class="px-4 py-4">
      <h2
        id="transcript-workspace-title"
        class="text-lg font-semibold leading-tight text-navy"
      >
        <template v-if="runtimeStatus === 'succeeded'">Transkriptet är klart</template>
        <template v-else-if="runtimeStatus === 'running'">Transkribering pågår</template>
        <template v-else-if="runtimeStatus === 'canceled'">Transkriberingen avbröts</template>
        <template v-else-if="selectedTranscriptFile">Inspelningen är vald</template>
        <template v-else>Välj inspelning för att börja</template>
      </h2>
      <p class="mt-1 text-sm leading-snug text-navy/70">
        <template v-if="runtimeStatus === 'succeeded'">
          Granska talare och text innan du sparar transkriptet i ett senare steg.
        </template>
        <template v-else-if="runtimeStatus === 'running'">
          Sidan uppdateras när nästa steg är klart.
        </template>
        <template v-else>
          Ladda upp en ljudfil eller en video där ljudspåret ska skrivas ut.
        </template>
      </p>
    </header>

    <div class="flex min-h-0 flex-1 px-4 pb-4">
      <div
        v-if="runtimeStatus === 'running'"
        class="grid min-h-0 w-full flex-1 place-items-center border border-dashed border-navy/45 bg-canvas px-6 py-6 text-center"
        data-test="transcript-running-surface"
      >
        <div class="grid gap-2">
          <p class="text-base font-medium leading-tight text-navy">
            Transkriberar inspelningen.
          </p>
          <p class="text-sm leading-snug text-navy/70">
            {{ transcriptProgressLabel(currentJob) }}
          </p>
          <p
            v-if="currentJob?.audioProgress.percentComplete != null"
            class="text-xs font-semibold uppercase text-navy/65"
          >
            {{ currentJob.audioProgress.percentComplete }} %
          </p>
        </div>
      </div>

      <div
        v-else-if="runtimeStatus === 'failed'"
        class="grid min-h-0 w-full flex-1 place-items-center border border-dashed border-error/45 bg-error/5 px-6 py-6 text-center"
        data-test="transcript-failed-surface"
      >
        <p class="text-sm font-medium leading-snug text-navy">
          {{ errorMessage ?? "Det gick inte att skapa transkriptet. Försök igen." }}
        </p>
      </div>

      <div
        v-else-if="transcript"
        class="min-h-0 w-full flex-1 overflow-auto border border-navy/20 bg-canvas"
        data-test="transcript-result-surface"
      >
        <ol class="grid gap-0 divide-y divide-navy/15">
          <li
            v-for="segment in transcript.segments"
            :key="segment.id"
            class="grid gap-1 px-4 py-3"
          >
            <p class="text-xs font-black uppercase leading-none text-action">
              {{ segment.speakerLabel }}
            </p>
            <p class="text-sm leading-snug text-navy">
              {{ segment.text }}
            </p>
          </li>
        </ol>
      </div>

      <label
        v-else
        class="grid min-h-0 w-full flex-1 border border-dashed border-navy/45 bg-canvas px-6 py-6"
        :class="transcriptFileError ? 'border-error bg-error/5' : undefined"
        data-test="transcript-source-drop-zone"
        @dragover.prevent
        @drop="handleDrop"
      >
        <input
          class="sr-only"
          type="file"
          accept=".wav,.mp3,.m4a,.aac,.flac,.ogg,.opus,.webm,.aiff,.mp4,.mov,.mkv"
          data-test="transcript-workspace-file-input"
          @change="handleFileInput"
        >
        <div class="flex h-full min-w-0 items-center justify-center gap-4">
          <span
            class="grid h-12 w-12 shrink-0 place-items-center border border-navy/25 bg-panel"
            aria-hidden="true"
          >
            <FileAudio
              v-if="selectedTranscriptFile"
              class="h-6 w-6 text-navy"
            />
            <Upload
              v-else
              class="h-6 w-6 text-action"
            />
          </span>
          <div class="min-w-0">
            <p class="text-base font-medium leading-tight text-navy">
              {{ selectedTranscriptFile?.name ?? "Välj inspelning" }}
            </p>
            <p
              v-if="selectedTranscriptFile"
              class="mt-2 text-sm leading-snug text-navy/70"
            >
              {{ selectedTranscriptFile.sizeLabel }}
            </p>
            <p
              v-else-if="transcriptFileError"
              class="mt-2 text-sm leading-snug text-error"
            >
              {{ transcriptFileError }}
            </p>
            <p
              v-else
              class="mt-2 text-sm leading-snug text-navy/70"
            >
              Ljud eller video med ljud kan dras hit.
            </p>
          </div>
        </div>
      </label>
    </div>
  </section>
</template>
