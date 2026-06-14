<script setup lang="ts">
/**
 * Transcript UI inspection fixture view.
 *
 * Domain purpose:
 *   Render the completed Conversion Hub transcript workspace in dev/test so
 *   remediation work can be verified visually without submitting another STT job.
 *
 * Relationships:
 *   - Mounted only by the dev/test transcript UI-inspection route.
 *   - Reuses the production transcript rail and workspace shell components.
 */

import { computed, ref } from "vue";

import type {
  ConversionHubTranscriptFormatterArtifactRef,
  ConversionHubTranscriptFormatterOutputArtifact,
  ConversionHubTranscriptFormatterExportStatus,
} from "../../../api/conversionHubTranscriptFormatterExports";
import type { TranscriptFormatterArtifactKey } from "../../../api/conversionHubTranscriptFormatterArtifactActions";
import type { ConversionHubTranscriptSpeakerOverlayEntry } from "../../../api/conversionHubTranscriptSaves";
import type { TranscriptJson } from "../../../api/sirConvertGateway";
import ConversionHubModeTabs from "../ConversionHubModeTabs.vue";
import TranscriptWorkflowRailShell from "./TranscriptWorkflowRailShell.vue";
import TranscriptWorkspaceShell from "./TranscriptWorkspaceShell.vue";
import {
  formatterArtifactActionState,
  type FormatterArtifactActionStates,
} from "./transcriptFormatterArtifactActions";
import type { TranscriptSourceFileSelection } from "./useTranscriptSourceFile";

defineProps<{
  fixtureId?: string | null;
}>();

const selectedTranscriptFile: TranscriptSourceFileSelection = {
  file: new File(["audio fixture"], "Ny inspelning 4333.mp3", { type: "audio/mpeg" }),
  name: "Ny inspelning 4333.mp3",
  sizeLabel: "24,7 MB",
};

const transcript: TranscriptJson = {
  schemaVersion: "transcript_json_v1",
  transcriptText:
    "Vi vill ju ändå förbereda våra elever för framtiden. Känner du att du har det du behöver? Jag kan sammanfatta nästa steg.",
  segments: [
    {
      endSeconds: 52,
      id: "fixture-segment-1",
      speakerLabel: "O",
      startSeconds: 1,
      text: "Vi vill ju ändå förbereda våra elever för framtiden. Vi kanske ska ta det.",
    },
    {
      endSeconds: 318,
      id: "fixture-segment-2",
      speakerLabel: "P",
      startSeconds: 300,
      text: "Känner du att du har det du behöver? Har aldrig jag innan pratat med er.",
    },
    {
      endSeconds: 402,
      id: "fixture-segment-3",
      speakerLabel: "H",
      startSeconds: 389,
      text: "Jag kan sammanfatta nästa steg och lägga det i materialet.",
    },
  ],
};

const formatterArtifacts: readonly ConversionHubTranscriptFormatterArtifactRef[] = [
  {
    artifact_key: "transcript_txt",
    content_type: "text/plain; charset=utf-8",
    filename: "transkript-fixture.txt",
    requested_artifact: "txt",
    size_bytes: 8192,
  },
  {
    artifact_key: "transcript_md",
    content_type: "text/markdown; charset=utf-8",
    filename: "transkript-fixture.md",
    requested_artifact: "md",
    size_bytes: 9216,
  },
  {
    artifact_key: "transcript_vtt",
    content_type: "text/vtt; charset=utf-8",
    filename: "transkript-fixture.vtt",
    requested_artifact: "vtt",
    size_bytes: 7168,
  },
  {
    artifact_key: "transcript_srt",
    content_type: "application/x-subrip",
    filename: "transkript-fixture.srt",
    requested_artifact: "srt",
    size_bytes: 7680,
  },
];

const artifactKeyByRequested: Record<
  ConversionHubTranscriptFormatterOutputArtifact,
  TranscriptFormatterArtifactKey
> = {
  md: "transcript_md",
  srt: "transcript_srt",
  txt: "transcript_txt",
  vtt: "transcript_vtt",
};

const speakerOverlayEntries = ref<ConversionHubTranscriptSpeakerOverlayEntry[]>([
  { canonical_speaker_label: "O", display_name: "Olof" },
  { canonical_speaker_label: "P", display_name: "Petter" },
  { canonical_speaker_label: "H", display_name: "Hanna" },
]);
const speakerOverlayStatus = ref<"idle" | "loading" | "saving" | "saved" | "failed">("saved");
const formatterArtifactActionStates = ref<FormatterArtifactActionStates>({});
const canExport = computed(() => speakerOverlayStatus.value === "saved");
const visibleFormatterArtifacts = computed(() => (canExport.value ? formatterArtifacts : []));
const formatterExportStatus = computed<ConversionHubTranscriptFormatterExportStatus>(() =>
  canExport.value ? "succeeded" : "not_requested",
);

function handleSpeakerOverlayChanged(label: string, displayName: string): void {
  speakerOverlayEntries.value = [
    ...speakerOverlayEntries.value.filter((entry) => entry.canonical_speaker_label !== label),
    { canonical_speaker_label: label, display_name: displayName },
  ];
  speakerOverlayStatus.value = "saved";
  formatterArtifactActionStates.value = {};
}

function markArtifactAction(
  requestedArtifact: ConversionHubTranscriptFormatterOutputArtifact,
  action: "download" | "save",
): void {
  const artifactKey = artifactKeyByRequested[requestedArtifact];
  const current = formatterArtifactActionState(formatterArtifactActionStates.value, artifactKey);
  formatterArtifactActionStates.value = {
    ...formatterArtifactActionStates.value,
    [artifactKey]: {
      ...current,
      [action]: "succeeded",
      savedFilename: action === "save" ? `transkript-fixture.${requestedArtifact}` : current.savedFilename,
    },
  };
}
</script>

<template>
  <main
    class="min-h-[calc(100vh-72px)] overflow-x-hidden bg-canvas px-3 py-4 text-navy md:px-5 lg:px-6"
    aria-labelledby="transcript-inspection-title"
  >
    <h1
      id="transcript-inspection-title"
      class="sr-only"
    >
      Transcript UI inspection
    </h1>
    <ConversionHubModeTabs
      active-mode="transcript"
      @mode-selected="() => undefined"
    />
    <section
      class="mx-auto grid min-h-[28rem] w-full min-w-0 max-w-[90rem] grid-cols-1 items-stretch border border-navy bg-panel shadow-brutal-sm min-[821px]:grid-cols-[minmax(14rem,17rem)_minmax(0,1fr)] min-[1181px]:grid-cols-[minmax(15rem,18rem)_minmax(0,1fr)]"
      aria-label="Conversion Hub"
      :data-inspection-fixture-id="fixtureId ?? undefined"
      data-test="transcript-ui-inspection-host-frame"
    >
      <TranscriptWorkflowRailShell
        :abort-state="{ status: 'idle', message: null }"
        :can-start-transcript="false"
        :is-running="false"
        :max-speakers="3"
        :min-speakers="1"
        :selected-transcript-file="selectedTranscriptFile"
        :speaker-count="3"
        :speaker-error="null"
        speaker-mode="auto"
        :transcript-file-error="null"
        @cancel-transcript="() => undefined"
        @clear-transcript-file="() => undefined"
        @max-speakers-changed="() => undefined"
        @min-speakers-changed="() => undefined"
        @reset-transcript-choices="() => undefined"
        @speaker-count-changed="() => undefined"
        @speaker-mode-changed="() => undefined"
        @start-transcript="() => undefined"
        @transcript-file-selected="() => undefined"
      />
      <div
        class="col-span-full grid min-h-0 min-w-0 grid-cols-1 items-stretch min-[821px]:col-span-1"
        data-test="transcript-host-layout"
      >
        <TranscriptWorkspaceShell
          :abort-state="{ status: 'idle', message: null }"
          :can-edit-speaker-overlays="true"
          :can-request-formatter-export="canExport"
          :can-save-transcript="false"
          :current-job="null"
          :error-message="null"
          :formatter-artifact-action-states="formatterArtifactActionStates"
          :formatter-export-artifacts="visibleFormatterArtifacts"
          :formatter-export-error-message="null"
          :formatter-export-status="formatterExportStatus"
          runtime-status="succeeded"
          :save-error-message="null"
          save-status="saved"
          :selected-transcript-file="selectedTranscriptFile"
          :speaker-overlay-entries="speakerOverlayEntries"
          :speaker-overlay-error-message="null"
          :speaker-overlay-status="speakerOverlayStatus"
          :transcript="transcript"
          :transcript-file-error="null"
          @download-formatter-artifact="markArtifactAction($event, 'download')"
          @files-dropped="() => undefined"
          @save-formatter-artifact="markArtifactAction($event, 'save')"
          @save-transcript="() => undefined"
          @speaker-overlay-changed="handleSpeakerOverlayChanged"
          @transcript-file-selected="() => undefined"
        />
      </div>
    </section>
  </main>
</template>
