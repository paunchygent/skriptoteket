<script setup lang="ts">
/**
 * Transcript formatter export panel.
 *
 * Domain purpose:
 *   Render a single selected-format export control for saved transcript
 *   formatter artifacts without letting the browser own producer work.
 *
 * Relationships:
 *   - Used by `TranscriptCompletedWorkspace` after a transcript is autosaved.
 *   - Emits selected format intent to `ConversionHubTranscriptHost`.
 */

import { computed, ref } from "vue";
import { Download, FolderInput } from "lucide-vue-next";

import type {
  ConversionHubTranscriptFormatterArtifactRef,
  ConversionHubTranscriptFormatterExportStatus,
} from "../../../api/conversionHubTranscriptFormatterExports";
import {
  formatterArtifactActionState,
  type FormatterArtifactActionStates,
} from "./transcriptFormatterArtifactActions";
import { TRANSCRIPT_COMMAND_BUTTON_CLASS } from "./transcriptCommandButtonClasses";

type TranscriptFormatterRequestedArtifact =
  ConversionHubTranscriptFormatterArtifactRef["requested_artifact"];

const FORMAT_OPTIONS: readonly TranscriptFormatterRequestedArtifact[] = [
  "txt",
  "md",
  "vtt",
  "srt",
];

const props = defineProps<{
  actionStates: FormatterArtifactActionStates;
  artifacts: readonly ConversionHubTranscriptFormatterArtifactRef[];
  canRequest: boolean;
  errorMessage: string | null;
  status: ConversionHubTranscriptFormatterExportStatus;
}>();

const emit = defineEmits<{
  downloadFormatterArtifact: [requestedArtifact: TranscriptFormatterRequestedArtifact];
  saveFormatterArtifact: [requestedArtifact: TranscriptFormatterRequestedArtifact];
}>();

const selectedFormat = ref<TranscriptFormatterRequestedArtifact>("txt");

const selectedArtifact = computed(() =>
  props.artifacts.find((artifact) => artifact.requested_artifact === selectedFormat.value) ?? null,
);
const selectedActionState = computed(() =>
  selectedArtifact.value
    ? formatterArtifactActionState(props.actionStates, selectedArtifact.value.artifact_key)
    : null,
);
const selectedActionRunning = computed(
  () =>
    selectedActionState.value?.download === "running" ||
    selectedActionState.value?.save === "running",
);
const selectedActionEnabled = computed(
  () => !selectedActionRunning.value && (props.canRequest || selectedArtifact.value !== null),
);

function formatLabel(format: TranscriptFormatterRequestedArtifact): string {
  switch (format) {
    case "txt":
      return "TXT";
    case "md":
      return "MD";
    case "vtt":
      return "VTT";
    case "srt":
      return "SRT";
  }
}

function stateMessage(): string {
  if (selectedActionState.value?.download === "running") return "Hämtar filen.";
  if (selectedActionState.value?.save === "running") return "Sparar i Mina filer.";
  if (selectedActionState.value?.download === "failed") return "Det gick inte att hämta filen.";
  if (selectedActionState.value?.save === "failed") return "Det gick inte att spara filen.";
  if (selectedActionState.value?.save === "succeeded") {
    return selectedActionState.value.savedFilename
      ? `Sparad i Mina filer: ${selectedActionState.value.savedFilename}.`
      : "Sparad i Mina filer.";
  }
  if (selectedActionState.value?.download === "succeeded") return "Fil hämtad.";
  if (props.status === "running") return "Filer skapas.";
  if (props.status === "pending") return "Filerna är köade. Försök igen om en stund.";
  if (props.status === "succeeded") return "Filer är klara.";
  if (props.status === "failed") {
    return props.errorMessage ?? "Filerna kunde inte skapas. Försök igen.";
  }
  if (props.canRequest) return "Välj format och använd en av åtgärderna.";
  return "Fyll i namn för alla talare innan filer kan skapas.";
}
</script>

<template>
  <section
    class="grid min-w-0 gap-3 border-t border-navy/15 pt-4"
    aria-label="Exportera transkript"
  >
    <div
      class="grid min-w-0 grid-cols-4 border border-navy/25"
      aria-label="Välj format"
      data-test="transcript-format-selector"
    >
      <button
        v-for="format in FORMAT_OPTIONS"
        :key="format"
        type="button"
        class="h-9 border-r border-navy/25 text-xs font-black transition last:border-r-0 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-3px] focus-visible:outline-action"
        :class="
          selectedFormat === format
            ? 'bg-navy text-canvas hover:bg-navy'
            : 'bg-panel text-navy hover:bg-action/10'
        "
        :aria-pressed="selectedFormat === format"
        :data-test="`transcript-format-option-${format}`"
        @click="selectedFormat = format"
      >
        {{ formatLabel(format) }}
      </button>
    </div>

    <div class="grid min-w-0 grid-cols-[minmax(0,1fr)_minmax(0,1fr)] gap-2">
      <button
        type="button"
        :class="TRANSCRIPT_COMMAND_BUTTON_CLASS"
        :disabled="!selectedActionEnabled"
        data-test="transcript-download-selected-format"
        @click="emit('downloadFormatterArtifact', selectedFormat)"
      >
        <Download
          class="h-4 w-4"
          aria-hidden="true"
        />
        <span class="truncate">Ladda ner</span>
      </button>
      <button
        type="button"
        :class="TRANSCRIPT_COMMAND_BUTTON_CLASS"
        :disabled="!selectedActionEnabled"
        data-test="transcript-save-selected-format"
        @click="emit('saveFormatterArtifact', selectedFormat)"
      >
        <FolderInput
          class="h-4 w-4"
          aria-hidden="true"
        />
        <span class="truncate">Mina filer</span>
      </button>
    </div>

    <p
      class="min-h-[2rem] text-xs font-medium leading-snug text-navy/65"
      data-test="transcript-formatter-export-state"
      aria-live="polite"
    >
      {{ stateMessage() }}
    </p>
  </section>
</template>
