<script setup lang="ts">
/**
 * Transcript formatter replay panel.
 *
 * Domain purpose:
 *   Render the saved-transcript command that asks Sir Convert to replay
 *   overlay-aware TXT/Markdown/VTT/SRT formatter artifacts.
 *
 * Relationships:
 *   - Used by `TranscriptWorkspaceShell` after a transcript is saved.
 *   - Receives producer artifact refs from `ConversionHubTranscriptHost`.
 */

import { Download, FileText, Save } from "lucide-vue-next";

import type {
  ConversionHubTranscriptFormatterArtifactRef,
} from "../../../api/conversionHubTranscriptFormatterReplay";
import {
  formatterArtifactActionState,
  type FormatterArtifactActionStates,
} from "./transcriptFormatterArtifactActions";

const props = defineProps<{
  actionStates: FormatterArtifactActionStates;
  artifacts: readonly ConversionHubTranscriptFormatterArtifactRef[];
  canRequest: boolean;
  errorMessage: string | null;
  status: "idle" | "running" | "succeeded" | "failed";
}>();

const emit = defineEmits<{
  downloadFormatterArtifact: [artifact: ConversionHubTranscriptFormatterArtifactRef];
  requestFormatterReplay: [];
  saveFormatterArtifact: [artifact: ConversionHubTranscriptFormatterArtifactRef];
}>();

function artifactLabel(artifact: ConversionHubTranscriptFormatterArtifactRef): string {
  switch (artifact.requested_artifact) {
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

function downloadLabel(artifact: ConversionHubTranscriptFormatterArtifactRef): string {
  const state = formatterArtifactActionState(props.actionStates, artifact.artifact_key);
  if (state.download === "running") return "Hämtar";
  if (state.download === "failed") return "Försök igen";
  if (state.download === "succeeded") return "Hämta igen";
  return "Hämta";
}

function saveLabel(artifact: ConversionHubTranscriptFormatterArtifactRef): string {
  const state = formatterArtifactActionState(props.actionStates, artifact.artifact_key);
  if (state.save === "running") return "Sparar";
  if (state.save === "failed") return "Försök igen";
  if (state.save === "succeeded") return "Sparad";
  return "Spara";
}

function actionMessage(artifact: ConversionHubTranscriptFormatterArtifactRef): string | null {
  const state = formatterArtifactActionState(props.actionStates, artifact.artifact_key);
  if (state.download === "failed") return "Det gick inte att hämta filen.";
  if (state.save === "failed") return "Det gick inte att spara filen.";
  if (state.save === "succeeded") {
    return state.savedFilename
      ? `Sparad i Mina filer: ${state.savedFilename}.`
      : "Sparad i Mina filer.";
  }
  if (state.download === "succeeded") return "Fil hämtad.";
  return null;
}

function isDownloadDisabled(artifact: ConversionHubTranscriptFormatterArtifactRef): boolean {
  return (
    formatterArtifactActionState(props.actionStates, artifact.artifact_key).download ===
    "running"
  );
}

function isSaveDisabled(artifact: ConversionHubTranscriptFormatterArtifactRef): boolean {
  return formatterArtifactActionState(props.actionStates, artifact.artifact_key).save === "running";
}
</script>

<template>
  <div class="grid gap-3 border-t border-navy/10 pt-3">
    <div class="min-w-0">
      <p
        class="text-xs font-medium leading-snug text-navy/65"
        data-test="transcript-formatter-replay-state"
      >
        <template v-if="status === 'running'">Skapar exportfiler.</template>
        <template v-else-if="status === 'succeeded'">Exportfiler är klara.</template>
        <template v-else-if="status === 'failed'">
          {{ errorMessage ?? "Exportfiler kunde inte skapas." }}
        </template>
        <template v-else>Exportfiler kan skapas.</template>
      </p>
    </div>
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div
        v-if="artifacts.length > 0"
        class="grid flex-1 gap-2"
      >
        <div
          v-for="artifact in artifacts"
          :key="artifact.artifact_key"
          class="flex flex-wrap items-center gap-2"
        >
          <span class="border border-action/30 bg-action/10 px-2 py-1 text-[0.68rem] font-black uppercase leading-none text-action">
            {{ artifactLabel(artifact) }}
          </span>
          <button
            type="button"
            class="inline-flex h-8 items-center gap-1.5 border border-navy/25 bg-panel px-2 text-xs font-semibold leading-none text-navy transition hover:border-action disabled:cursor-not-allowed disabled:text-navy/45"
            :disabled="isDownloadDisabled(artifact)"
            :data-test="`transcript-download-artifact-${artifact.artifact_key}`"
            @click="emit('downloadFormatterArtifact', artifact)"
          >
            <Download
              class="h-3.5 w-3.5"
              aria-hidden="true"
            />
            <span>{{ downloadLabel(artifact) }}</span>
          </button>
          <button
            type="button"
            class="inline-flex h-8 items-center gap-1.5 border border-navy/25 bg-panel px-2 text-xs font-semibold leading-none text-navy transition hover:border-action disabled:cursor-not-allowed disabled:text-navy/45"
            :disabled="isSaveDisabled(artifact)"
            :data-test="`transcript-save-artifact-${artifact.artifact_key}`"
            @click="emit('saveFormatterArtifact', artifact)"
          >
            <Save
              class="h-3.5 w-3.5"
              aria-hidden="true"
            />
            <span>{{ saveLabel(artifact) }}</span>
          </button>
          <p
            v-if="actionMessage(artifact)"
            class="basis-full text-xs font-medium leading-snug text-navy/65"
            :data-test="`transcript-artifact-action-state-${artifact.artifact_key}`"
          >
            {{ actionMessage(artifact) }}
          </p>
        </div>
      </div>
      <button
        type="button"
        class="inline-flex h-9 shrink-0 items-center gap-2 border border-navy/25 bg-panel px-3 text-sm font-semibold leading-none text-navy transition hover:border-action disabled:cursor-not-allowed disabled:text-navy/45"
        :disabled="!canRequest || status === 'running'"
        data-test="transcript-formatter-replay-button"
        @click="emit('requestFormatterReplay')"
      >
        <FileText
          class="h-4 w-4"
          aria-hidden="true"
        />
        <span>{{ status === "running" ? "Skapar" : "Skapa exportfiler" }}</span>
      </button>
    </div>
  </div>
</template>
