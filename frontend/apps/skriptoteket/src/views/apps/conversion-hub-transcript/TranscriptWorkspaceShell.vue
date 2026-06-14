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

import type {
  ConversionHubTranscriptFormatterArtifactRef,
  ConversionHubTranscriptFormatterExportStatus,
} from "../../../api/conversionHubTranscriptFormatterExports";
import type { ConversionHubTranscriptSpeakerOverlayEntry } from "../../../api/conversionHubTranscriptSaves";
import type { SirConvertTranscriptJob, TranscriptJson } from "../../../api/sirConvertGateway";
import type {
  TranscriptAbortState,
  TranscriptRuntimeStatus,
  TranscriptUploadState,
} from "./useTranscriptGatewayRuntime";
import type { TranscriptSourceFileSelection } from "./useTranscriptSourceFile";
import TranscriptCompletedWorkspace from "./TranscriptCompletedWorkspace.vue";
import TranscriptProgressPanel from "./TranscriptProgressPanel.vue";
import type { FormatterArtifactActionStates } from "./transcriptFormatterArtifactActions";

type TranscriptFormatterRequestedArtifact =
  ConversionHubTranscriptFormatterArtifactRef["requested_artifact"];

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
  canRequestFormatterExport?: boolean;
  formatterArtifactActionStates?: FormatterArtifactActionStates;
  formatterExportArtifacts?: readonly ConversionHubTranscriptFormatterArtifactRef[];
  formatterExportErrorMessage?: string | null;
  formatterExportStatus?: ConversionHubTranscriptFormatterExportStatus;
  speakerOverlayEntries: readonly ConversionHubTranscriptSpeakerOverlayEntry[];
  speakerOverlayErrorMessage: string | null;
  speakerOverlayStatus: "idle" | "loading" | "saving" | "saved" | "failed";
  transcript: TranscriptJson | null;
  transcriptFileError: string | null;
  uploadState?: TranscriptUploadState;
}>(), {
  canRequestFormatterExport: false,
  formatterArtifactActionStates: () => ({}),
  formatterExportArtifacts: () => [],
  formatterExportErrorMessage: null,
  formatterExportStatus: "not_requested",
  uploadState: () => ({
    loadedBytes: 0,
    percentComplete: null,
    status: "idle",
    totalBytes: null,
  }),
});

const emit = defineEmits<{
  downloadFormatterArtifact: [requestedArtifact: TranscriptFormatterRequestedArtifact];
  filesDropped: [files: File[]];
  saveFormatterArtifact: [requestedArtifact: TranscriptFormatterRequestedArtifact];
  saveTranscript: [];
  saveSpeakerOverlays: [];
  speakerOverlayChanged: [label: string, displayName: string];
  transcriptFileSelected: [file: File];
}>();

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
          Transkriptet sparas automatiskt och kan användas direkt.
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
      <TranscriptProgressPanel
        v-if="runtimeStatus === 'running'"
        :abort-state="abortState"
        :current-job="currentJob"
        :upload-state="uploadState"
      />

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

      <TranscriptCompletedWorkspace
        v-else-if="runtimeStatus === 'succeeded' && transcript"
        :can-edit-speaker-overlays="canEditSpeakerOverlays"
        :can-request-formatter-export="canRequestFormatterExport"
        :can-retry-transcript-save="canSaveTranscript"
        :formatter-artifact-action-states="formatterArtifactActionStates"
        :formatter-export-artifacts="formatterExportArtifacts"
        :formatter-export-error-message="formatterExportErrorMessage"
        :formatter-export-status="formatterExportStatus"
        :save-error-message="saveErrorMessage"
        :save-status="saveStatus"
        :speaker-overlay-entries="speakerOverlayEntries"
        :speaker-overlay-error-message="speakerOverlayErrorMessage"
        :speaker-overlay-status="speakerOverlayStatus"
        :transcript="transcript"
        @download-formatter-artifact="emit('downloadFormatterArtifact', $event)"
        @retry-transcript-save="emit('saveTranscript')"
        @save-formatter-artifact="emit('saveFormatterArtifact', $event)"
        @save-speaker-overlays="emit('saveSpeakerOverlays')"
        @speaker-overlay-changed="
          (label, displayName) => emit('speakerOverlayChanged', label, displayName)
        "
      />

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
