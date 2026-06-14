<script setup lang="ts">
/**
 * Transcript completed workspace.
 *
 * Domain purpose:
 *   Render the autosaved transcript reading surface plus speaker/export
 *   inspector after canonical transcript JSON exists.
 *
 * Relationships:
 *   - Used by `TranscriptWorkspaceShell` for the successful transcript state.
 *   - Delegates selected-format export actions to `TranscriptFormatterExportPanel`.
 */

import { Check, Save } from "lucide-vue-next";

import type {
  ConversionHubTranscriptFormatterArtifactRef,
  ConversionHubTranscriptFormatterExportStatus,
} from "../../../api/conversionHubTranscriptFormatterExports";
import type { ConversionHubTranscriptSpeakerOverlayEntry } from "../../../api/conversionHubTranscriptSaves";
import type { TranscriptJson } from "../../../api/sirConvertGateway";
import TranscriptFormatterExportPanel from "./TranscriptFormatterExportPanel.vue";
import type { FormatterArtifactActionStates } from "./transcriptFormatterArtifactActions";

type TranscriptFormatterRequestedArtifact =
  ConversionHubTranscriptFormatterArtifactRef["requested_artifact"];

defineProps<{
  canEditSpeakerOverlays: boolean;
  canRequestFormatterExport: boolean;
  canRetryTranscriptSave: boolean;
  formatterArtifactActionStates: FormatterArtifactActionStates;
  formatterExportArtifacts: readonly ConversionHubTranscriptFormatterArtifactRef[];
  formatterExportErrorMessage: string | null;
  formatterExportStatus: ConversionHubTranscriptFormatterExportStatus;
  saveErrorMessage: string | null;
  saveStatus: "idle" | "saving" | "saved" | "failed";
  speakerOverlayEntries: readonly ConversionHubTranscriptSpeakerOverlayEntry[];
  speakerOverlayErrorMessage: string | null;
  speakerOverlayStatus: "idle" | "loading" | "saving" | "saved" | "failed";
  transcript: TranscriptJson;
}>();

const emit = defineEmits<{
  downloadFormatterArtifact: [requestedArtifact: TranscriptFormatterRequestedArtifact];
  retryTranscriptSave: [];
  saveFormatterArtifact: [requestedArtifact: TranscriptFormatterRequestedArtifact];
  saveSpeakerOverlays: [];
  speakerOverlayChanged: [label: string, displayName: string];
}>();

function speakerLabels(transcript: TranscriptJson): string[] {
  const labels: string[] = [];
  const seen = new Set<string>();
  for (const segment of transcript.segments) {
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

function speakerInitial(
  entries: readonly ConversionHubTranscriptSpeakerOverlayEntry[],
  label: string,
): string {
  const displayName = speakerDisplayName(entries, label).trim();
  return (displayName[0] ?? label[0] ?? "?").toLocaleUpperCase("sv-SE");
}

function formatTimestamp(seconds: number): string {
  const rounded = Math.max(0, Math.floor(seconds));
  const minutes = Math.floor(rounded / 60);
  const remainingSeconds = String(rounded % 60).padStart(2, "0");
  return `${minutes}:${remainingSeconds}`;
}

function handleSpeakerOverlayInput(label: string, event: Event): void {
  const input = event.target as HTMLInputElement;
  emit("speakerOverlayChanged", label, input.value);
}
</script>

<template>
  <div
    class="grid min-h-0 w-full flex-1 gap-0 overflow-hidden bg-canvas 2xl:grid-cols-[minmax(34rem,1fr)_minmax(18rem,21rem)]"
    data-test="transcript-result-surface"
  >
    <section
      class="flex min-h-0 min-w-0 flex-col border border-navy/20 bg-panel"
      data-test="transcript-complete-workspace"
      aria-labelledby="transcript-complete-title"
    >
      <header class="shrink-0 border-b border-navy/15 px-4 py-4">
        <p
          class="inline-flex min-h-6 items-center gap-2 text-sm font-semibold leading-tight text-success"
          data-test="transcript-save-state"
          aria-live="polite"
        >
          <Check
            v-if="saveStatus === 'saved'"
            class="h-4 w-4"
            aria-hidden="true"
          />
          <template v-if="saveStatus === 'saved'">Sparat automatiskt</template>
          <template v-else-if="saveStatus === 'saving'">Sparar automatiskt</template>
          <template v-else-if="saveStatus === 'failed'">
            {{ saveErrorMessage ?? "Transkriptet kunde inte sparas. Försök igen." }}
          </template>
          <template v-else>Sparar automatiskt</template>
        </p>
        <button
          v-if="saveStatus === 'failed'"
          type="button"
          class="mt-3 inline-flex h-9 items-center gap-2 border border-navy/25 bg-panel px-3 text-sm font-semibold leading-none text-navy transition hover:border-action disabled:cursor-not-allowed disabled:text-navy/45"
          :disabled="!canRetryTranscriptSave"
          data-test="transcript-save-retry"
          @click="emit('retryTranscriptSave')"
        >
          Försök igen
        </button>
        <h3
          id="transcript-complete-title"
          class="mt-3 text-xl font-semibold leading-tight text-navy"
        >
          Transkript
        </h3>
      </header>

      <ol class="grid min-h-0 flex-1 gap-0 overflow-auto divide-y divide-navy/15">
        <li
          v-for="segment in transcript.segments"
          :key="segment.id"
          class="grid grid-cols-[2rem_minmax(0,1fr)] gap-3 px-4 py-4"
        >
          <span
            class="grid h-7 w-7 place-items-center bg-action text-xs font-black text-canvas"
            aria-hidden="true"
          >
            {{ speakerInitial(speakerOverlayEntries, segment.speakerLabel) }}
          </span>
          <span class="min-w-0">
            <span class="mb-2 flex flex-wrap items-baseline gap-2">
              <span class="text-sm font-black leading-tight text-navy">
                {{ speakerDisplayName(speakerOverlayEntries, segment.speakerLabel) }}
              </span>
              <span class="text-xs font-semibold leading-tight text-navy/55">
                {{ formatTimestamp(segment.startSeconds) }}
              </span>
            </span>
            <span class="block text-[0.95rem] leading-relaxed text-navy">
              {{ segment.text }}
            </span>
          </span>
        </li>
      </ol>
    </section>

    <aside
      class="grid min-h-0 content-start gap-5 border-x border-b border-navy/20 bg-panel-muted px-4 py-4 2xl:border-l-0 2xl:border-t"
      data-test="transcript-inspector"
      aria-label="Talare och export"
    >
      <h3 class="text-lg font-semibold leading-tight text-navy">
        Talare och export
      </h3>

      <section
        v-if="canEditSpeakerOverlays && speakerLabels(transcript).length > 0"
        class="grid gap-3 border-t border-navy/15 pt-4"
        data-test="transcript-speaker-overlays"
      >
        <div class="grid gap-2">
          <label
            v-for="label in speakerLabels(transcript)"
            :key="label"
            class="grid grid-cols-[2rem_minmax(0,1fr)] items-center gap-2"
          >
            <span
              class="grid h-7 w-7 place-items-center bg-action text-xs font-black text-canvas"
              aria-hidden="true"
            >
              {{ speakerInitial(speakerOverlayEntries, label) }}
            </span>
            <input
              class="h-9 min-w-0 border border-navy/25 bg-panel px-3 text-sm font-medium text-navy outline-none transition focus:border-action"
              type="text"
              maxlength="120"
              :aria-label="`Namn för ${label}`"
              :value="speakerOverlayValue(speakerOverlayEntries, label)"
              :placeholder="label"
              :data-test="`transcript-speaker-name-${label}`"
              @input="handleSpeakerOverlayInput(label, $event)"
            >
          </label>
        </div>
        <div class="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3">
          <p
            class="min-h-[2rem] text-xs font-medium leading-snug text-navy/65"
            data-test="transcript-speaker-overlay-state"
            aria-live="polite"
          >
            <template v-if="speakerOverlayStatus === 'loading'">Hämtar namn.</template>
            <template v-else-if="speakerOverlayStatus === 'saving'">Sparar namn.</template>
            <template v-else-if="speakerOverlayStatus === 'saved'">Namnen är sparade.</template>
            <template v-else-if="speakerOverlayStatus === 'failed'">
              {{ speakerOverlayErrorMessage }}
            </template>
            <template v-else>Namnen kan sparas.</template>
          </p>
          <button
            type="button"
            class="grid h-9 w-9 place-items-center border border-navy/25 bg-panel text-navy transition hover:border-action disabled:cursor-not-allowed disabled:text-navy/45"
            :disabled="speakerOverlayStatus === 'saving' || speakerOverlayStatus === 'loading'"
            data-test="transcript-speaker-overlays-save"
            aria-label="Spara namn"
            title="Spara namn"
            @click="emit('saveSpeakerOverlays')"
          >
            <Save
              class="h-4 w-4"
              aria-hidden="true"
            />
          </button>
        </div>
      </section>

      <TranscriptFormatterExportPanel
        v-if="saveStatus === 'saved'"
        :action-states="formatterArtifactActionStates"
        :artifacts="formatterExportArtifacts"
        :can-request="canRequestFormatterExport"
        :error-message="formatterExportErrorMessage"
        :status="formatterExportStatus"
        @download-formatter-artifact="emit('downloadFormatterArtifact', $event)"
        @save-formatter-artifact="emit('saveFormatterArtifact', $event)"
      />
    </aside>
  </div>
</template>
