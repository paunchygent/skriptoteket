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

import { FileAudio, Save, Upload } from "lucide-vue-next";

import type { ConversionHubTranscriptFormatterArtifactRef } from "../../../api/conversionHubTranscriptFormatterReplay";
import type { ConversionHubTranscriptSpeakerOverlayEntry } from "../../../api/conversionHubTranscriptSaves";
import type { SirConvertTranscriptJob, TranscriptJson } from "../../../api/sirConvertGateway";
import type {
  TranscriptAbortState,
  TranscriptRuntimeStatus,
} from "./useTranscriptGatewayRuntime";
import type { TranscriptSourceFileSelection } from "./useTranscriptSourceFile";
import TranscriptFormatterReplayPanel from "./TranscriptFormatterReplayPanel.vue";
import type { FormatterArtifactActionStates } from "./transcriptFormatterArtifactActions";

withDefaults(defineProps<{
  abortState: TranscriptAbortState;
  canSaveTranscript: boolean;
  currentJob: SirConvertTranscriptJob | null;
  errorMessage: string | null;
  runtimeStatus: TranscriptRuntimeStatus;
  saveErrorMessage: string | null;
  saveStatus: "idle" | "saving" | "saved" | "failed";
  selectedTranscriptFile: TranscriptSourceFileSelection | null;
  canEditSpeakerOverlays: boolean;
  canRequestFormatterReplay?: boolean;
  formatterArtifactActionStates?: FormatterArtifactActionStates;
  formatterReplayArtifacts?: readonly ConversionHubTranscriptFormatterArtifactRef[];
  formatterReplayErrorMessage?: string | null;
  formatterReplayStatus?: "idle" | "running" | "succeeded" | "failed";
  speakerOverlayEntries: readonly ConversionHubTranscriptSpeakerOverlayEntry[];
  speakerOverlayErrorMessage: string | null;
  speakerOverlayStatus: "idle" | "loading" | "saving" | "saved" | "failed";
  transcript: TranscriptJson | null;
  transcriptFileError: string | null;
}>(), {
  canRequestFormatterReplay: false,
  formatterArtifactActionStates: () => ({}),
  formatterReplayArtifacts: () => [],
  formatterReplayErrorMessage: null,
  formatterReplayStatus: "idle",
});

const emit = defineEmits<{
  downloadFormatterArtifact: [artifact: ConversionHubTranscriptFormatterArtifactRef];
  filesDropped: [files: File[]];
  requestFormatterReplay: [];
  saveFormatterArtifact: [artifact: ConversionHubTranscriptFormatterArtifactRef];
  saveTranscript: [];
  saveSpeakerOverlays: [];
  speakerOverlayChanged: [label: string, displayName: string];
  transcriptFileSelected: [file: File];
}>();

function transcriptProgressLabel(job: SirConvertTranscriptJob | null): string {
  if (!job) return "Förbereder ljudet.";
  if (job.status === "submitted" || job.status === "queued" || !job.progress.phase) {
    return "Väntar på att starta.";
  }
  const phase = job.progress.phase;
  if (phase === "starting" || phase === "normalizing_audio") {
    return "Förbereder ljudet.";
  }
  if (phase === "probing_media") {
    return "Kontrollerar inspelningen.";
  }
  if (phase === "transcribing") {
    return "Skriver ut talet.";
  }
  if (phase === "diarizing") {
    return "Identifierar talare.";
  }
  if (phase === "aligning_segments") {
    return "Kontrollerar talare och text.";
  }
  if (phase === "packaging") {
    return "Förbereder transkriptet.";
  }
  return "Bearbetar inspelningen.";
}

function progressPercent(job: SirConvertTranscriptJob | null): string | null {
  const percent = job?.progress.percentComplete;
  if (percent === null || percent === undefined) return null;
  return `${Math.round(percent)} %`;
}

function formatDuration(seconds: number): string {
  const rounded = Math.max(0, Math.round(seconds));
  const minutes = Math.floor(rounded / 60);
  const remainingSeconds = String(rounded % 60).padStart(2, "0");
  return `${minutes}:${remainingSeconds}`;
}

function progressDuration(job: SirConvertTranscriptJob | null): string | null {
  const processed = job?.progress.processedMediaSeconds;
  const total = job?.progress.totalMediaSeconds;
  if (processed === null || processed === undefined || total === null || total === undefined) {
    return null;
  }
  return `${formatDuration(processed)} av ${formatDuration(total)}`;
}

function progressChunks(job: SirConvertTranscriptJob | null): string | null {
  const currentChunkIndex = job?.progress.currentChunkIndex;
  const totalChunks = job?.progress.totalChunks;
  if (
    currentChunkIndex === null ||
    currentChunkIndex === undefined ||
    totalChunks === null ||
    totalChunks === undefined
  ) {
    return null;
  }
  return `Del ${currentChunkIndex + 1} av ${totalChunks}`;
}

function progressHeartbeat(job: SirConvertTranscriptJob | null): string | null {
  const heartbeat = job?.progress.lastHeartbeatAt;
  if (!heartbeat) return null;
  const parsed = new Date(heartbeat);
  if (!Number.isFinite(parsed.getTime())) return null;
  return parsed.toLocaleTimeString("sv-SE", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function firstFile(fileList: FileList | null): File | null {
  const [file] = Array.from(fileList ?? []);
  return file ?? null;
}

function speakerLabels(transcript: TranscriptJson | null): string[] {
  const labels: string[] = [];
  const seen = new Set<string>();
  for (const segment of transcript?.segments ?? []) {
    if (!seen.has(segment.speakerLabel)) {
      seen.add(segment.speakerLabel);
      labels.push(segment.speakerLabel);
    }
  }
  return labels;
}

function speakerOverlayValue(
  entries: readonly ConversionHubTranscriptSpeakerOverlayEntry[],
  label: string,
): string {
  return (
    entries.find((entry) => entry.canonical_speaker_label === label)?.display_name ?? ""
  );
}

function speakerDisplayName(
  entries: readonly ConversionHubTranscriptSpeakerOverlayEntry[],
  label: string,
): string {
  return speakerOverlayValue(entries, label).trim() || label;
}

function handleSpeakerOverlayInput(label: string, event: Event): void {
  const input = event.target as HTMLInputElement;
  emit("speakerOverlayChanged", label, input.value);
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
          <span v-if="saveStatus === 'saved'">Transkriptet är sparat.</span>
          <span v-else>Transkriptet är klart men inte sparat.</span>
        </template>
        <template v-else-if="runtimeStatus === 'running'">
          Sidan uppdateras när nästa steg är klart.
        </template>
        <template v-else-if="runtimeStatus === 'canceled'">
          {{ abortState.message ?? "Transkriberingen är avbruten." }}
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
        <div class="grid max-w-sm gap-3">
          <p class="text-base font-medium leading-tight text-navy">
            Transkriberar inspelningen.
          </p>
          <p
            class="text-sm leading-snug text-navy/70"
            data-test="transcript-progress-phase"
          >
            {{ transcriptProgressLabel(currentJob) }}
          </p>
          <p
            v-if="progressPercent(currentJob)"
            class="text-xs font-semibold uppercase text-navy/65"
            data-test="transcript-progress-percent"
          >
            {{ progressPercent(currentJob) }}
          </p>
          <p
            v-if="progressDuration(currentJob)"
            class="text-xs leading-snug text-navy/65"
            data-test="transcript-progress-duration"
          >
            Bearbetat {{ progressDuration(currentJob) }}
          </p>
          <p
            v-if="progressChunks(currentJob)"
            class="text-xs leading-snug text-navy/65"
            data-test="transcript-progress-chunks"
          >
            {{ progressChunks(currentJob) }}
          </p>
          <p
            v-if="progressHeartbeat(currentJob)"
            class="text-xs leading-snug text-navy/65"
            data-test="transcript-progress-heartbeat"
          >
            Senast uppdaterad {{ progressHeartbeat(currentJob) }}
          </p>
          <p
            v-if="abortState.message"
            class="border border-warning/40 bg-warning/10 px-3 py-2 text-xs font-medium leading-snug text-navy"
            data-test="transcript-abort-state"
          >
            {{ abortState.message }}
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
        v-else-if="runtimeStatus === 'canceled'"
        class="grid min-h-0 w-full flex-1 place-items-center border border-dashed border-navy/35 bg-canvas px-6 py-6 text-center"
        data-test="transcript-canceled-surface"
      >
        <p class="text-sm font-medium leading-snug text-navy">
          {{ abortState.message ?? "Transkriberingen är avbruten." }}
        </p>
      </div>

      <div
        v-else-if="transcript"
        class="flex min-h-0 w-full flex-1 flex-col overflow-hidden border border-navy/20 bg-canvas"
        data-test="transcript-result-surface"
      >
        <div class="flex shrink-0 items-center justify-between gap-3 border-b border-navy/15 px-4 py-3">
          <p
            class="min-w-0 text-xs font-semibold uppercase leading-tight text-navy/65"
            data-test="transcript-save-state"
          >
            <template v-if="saveStatus === 'saved'">Sparat</template>
            <template v-else-if="saveStatus === 'saving'">Sparar</template>
            <template v-else-if="saveStatus === 'failed'">{{ saveErrorMessage }}</template>
            <template v-else>Tillfälligt transkript</template>
          </p>
          <button
            type="button"
            class="inline-flex h-9 shrink-0 items-center gap-2 border border-action bg-action px-3 text-sm font-semibold leading-none text-white transition hover:bg-action/90 disabled:cursor-not-allowed disabled:border-navy/20 disabled:bg-navy/10 disabled:text-navy/45"
            :disabled="!canSaveTranscript"
            data-test="transcript-save-button"
            @click="emit('saveTranscript')"
          >
            <Save
              class="h-4 w-4"
              aria-hidden="true"
            />
            <span>{{ saveStatus === "saving" ? "Sparar" : "Spara" }}</span>
          </button>
        </div>
        <div
          v-if="canEditSpeakerOverlays && speakerLabels(transcript).length > 0"
          class="grid shrink-0 gap-3 border-b border-navy/15 px-4 py-3"
          data-test="transcript-speaker-overlays"
        >
          <div class="grid gap-2 sm:grid-cols-2">
            <label
              v-for="label in speakerLabels(transcript)"
              :key="label"
              class="grid gap-1"
            >
              <span class="text-[0.7rem] font-black uppercase leading-none text-navy/60">
                {{ label }}
              </span>
              <input
                class="h-9 border border-navy/25 bg-panel px-3 text-sm font-medium text-navy outline-none transition focus:border-action"
                type="text"
                maxlength="120"
                :value="speakerOverlayValue(speakerOverlayEntries, label)"
                :placeholder="label"
                :data-test="`transcript-speaker-name-${label}`"
                @input="handleSpeakerOverlayInput(label, $event)"
              >
            </label>
          </div>
          <div class="flex flex-wrap items-center justify-between gap-3">
            <p
              class="text-xs font-medium leading-snug text-navy/65"
              data-test="transcript-speaker-overlay-state"
            >
              <template v-if="speakerOverlayStatus === 'loading'">Hämtar talarnamn.</template>
              <template v-else-if="speakerOverlayStatus === 'saving'">Sparar talarnamn.</template>
              <template v-else-if="speakerOverlayStatus === 'saved'">Talarnamn sparade.</template>
              <template v-else-if="speakerOverlayStatus === 'failed'">
                {{ speakerOverlayErrorMessage }}
              </template>
              <template v-else>Talarnamn kan sparas.</template>
            </p>
            <button
              type="button"
              class="inline-flex h-9 shrink-0 items-center gap-2 border border-navy/25 bg-panel px-3 text-sm font-semibold leading-none text-navy transition hover:border-action disabled:cursor-not-allowed disabled:text-navy/45"
              :disabled="speakerOverlayStatus === 'saving' || speakerOverlayStatus === 'loading'"
              data-test="transcript-speaker-overlays-save"
              @click="emit('saveSpeakerOverlays')"
            >
              <Save
                class="h-4 w-4"
                aria-hidden="true"
              />
              <span>{{ speakerOverlayStatus === "saving" ? "Sparar" : "Spara namn" }}</span>
            </button>
          </div>
          <TranscriptFormatterReplayPanel
            v-if="saveStatus === 'saved'"
            :action-states="formatterArtifactActionStates"
            :artifacts="formatterReplayArtifacts"
            :can-request="canRequestFormatterReplay"
            :error-message="formatterReplayErrorMessage"
            :status="formatterReplayStatus"
            @download-formatter-artifact="emit('downloadFormatterArtifact', $event)"
            @request-formatter-replay="emit('requestFormatterReplay')"
            @save-formatter-artifact="emit('saveFormatterArtifact', $event)"
          />
        </div>
        <ol class="grid min-h-0 flex-1 gap-0 overflow-auto divide-y divide-navy/15">
          <li
            v-for="segment in transcript.segments"
            :key="segment.id"
            class="grid gap-1 px-4 py-3"
          >
            <p class="text-xs font-black uppercase leading-none text-action">
              {{ speakerDisplayName(speakerOverlayEntries, segment.speakerLabel) }}
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
