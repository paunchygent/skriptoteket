/**
 * Revision-aware transcript speaker overlays.
 *
 * Owns overlay readback, debounced persistence, reset, and unmount cleanup.
 * Notifies the host's formatter-export owner when edits or resets invalidate exports.
 */

import { computed, onBeforeUnmount, ref, type Ref } from "vue";

import {
  getConversionHubTranscriptSpeakerOverlays,
  updateConversionHubTranscriptSpeakerOverlays,
  type ConversionHubTranscriptSpeakerOverlayEntry,
} from "../../../api/conversionHubTranscriptSaves";
import type { TranscriptJson } from "../../../api/sirConvertGateway";
import { speakerOverlayEntriesCoverTranscript } from "./transcriptSpeakerOverlayCoverage";

type SpeakerOverlayStatus = "idle" | "loading" | "saving" | "saved" | "failed";
type TranscriptSpeakerOverlayOptions = {
  savedTranscriptId: Ref<string | null>;
  transcript: Readonly<Ref<TranscriptJson | null>>;
  resetFormatterExport: () => void;
};

const SPEAKER_OVERLAY_AUTOSAVE_DELAY_MS = 500;

export function useTranscriptSpeakerOverlays({
  savedTranscriptId,
  transcript,
  resetFormatterExport,
}: TranscriptSpeakerOverlayOptions) {
  const speakerOverlayEntries = ref<ConversionHubTranscriptSpeakerOverlayEntry[]>([]);
  const speakerOverlayStatus = ref<SpeakerOverlayStatus>("idle");
  const speakerOverlayErrorMessage = ref<string | null>(null);
  const speakerOverlayRevision = ref(0);
  let speakerOverlayAutosaveTimer: ReturnType<typeof window.setTimeout> | null = null;
  let speakerOverlayGeneration = 0;
  let speakerOverlaySaveInFlight = false;
  let speakerOverlaySaveQueued = false;
  const speakerOverlayCoverageComplete = computed(() =>
    speakerOverlayEntriesCoverTranscript(
      transcript.value?.segments ?? [],
      speakerOverlayEntries.value,
    ),
  );

  function clearSpeakerOverlayAutosave(): void {
    if (speakerOverlayAutosaveTimer === null) return;
    window.clearTimeout(speakerOverlayAutosaveTimer);
    speakerOverlayAutosaveTimer = null;
  }

  function resetSpeakerOverlayState(): void {
    clearSpeakerOverlayAutosave();
    speakerOverlayGeneration += 1;
    speakerOverlaySaveInFlight = false;
    speakerOverlaySaveQueued = false;
    speakerOverlayRevision.value = 0;
    savedTranscriptId.value = null;
    speakerOverlayEntries.value = [];
    speakerOverlayStatus.value = "idle";
    speakerOverlayErrorMessage.value = null;
    resetFormatterExport();
  }

  onBeforeUnmount(() => {
    clearSpeakerOverlayAutosave();
    speakerOverlayGeneration += 1;
  });

  async function loadSpeakerOverlays(transcriptId: string): Promise<void> {
    speakerOverlayStatus.value = "loading";
    speakerOverlayErrorMessage.value = null;
    try {
      const response = await getConversionHubTranscriptSpeakerOverlays({ transcriptId });
      speakerOverlayEntries.value = response.overlays;
      speakerOverlayRevision.value = 0;
      speakerOverlayStatus.value = speakerOverlayEntriesCoverTranscript(
        transcript.value?.segments ?? [],
        response.overlays,
      )
        ? "saved"
        : "idle";
    } catch {
      speakerOverlayStatus.value = "failed";
      speakerOverlayErrorMessage.value = "Namnen kunde inte hämtas.";
    }
  }

  function handleSpeakerOverlayChanged(label: string, displayName: string): void {
    const nextEntries = speakerOverlayEntries.value.filter(
      (entry) => entry.canonical_speaker_label !== label,
    );
    if (displayName.length > 0) {
      nextEntries.push({ canonical_speaker_label: label, display_name: displayName });
    }
    speakerOverlayEntries.value = nextEntries;
    speakerOverlayRevision.value += 1;
    speakerOverlayStatus.value = "idle";
    speakerOverlayErrorMessage.value = null;
    resetFormatterExport();
    scheduleSpeakerOverlayAutosave();
  }

  function scheduleSpeakerOverlayAutosave(): void {
    const transcriptId = savedTranscriptId.value;
    if (!transcriptId) return;
    clearSpeakerOverlayAutosave();
    speakerOverlayAutosaveTimer = window.setTimeout(() => {
      speakerOverlayAutosaveTimer = null;
      void persistSpeakerOverlays();
    }, SPEAKER_OVERLAY_AUTOSAVE_DELAY_MS);
  }

  async function persistSpeakerOverlays(): Promise<void> {
    const transcriptId = savedTranscriptId.value;
    if (!transcriptId) return;
    if (speakerOverlaySaveInFlight) {
      speakerOverlaySaveQueued = true;
      return;
    }
    const generationAtStart = speakerOverlayGeneration;
    const revisionAtStart = speakerOverlayRevision.value;
    const overlays = speakerOverlayEntries.value
      .map((entry) => ({
        canonical_speaker_label: entry.canonical_speaker_label,
        display_name: entry.display_name.trim(),
      }))
      .filter((entry) => entry.display_name.length > 0);
    speakerOverlaySaveInFlight = true;
    speakerOverlayStatus.value = "saving";
    speakerOverlayErrorMessage.value = null;
    try {
      const response = await updateConversionHubTranscriptSpeakerOverlays({
        transcriptId,
        request: { overlays },
      });
      if (
        generationAtStart === speakerOverlayGeneration &&
        revisionAtStart === speakerOverlayRevision.value
      ) {
        speakerOverlayEntries.value = response.overlays;
        speakerOverlayStatus.value = speakerOverlayEntriesCoverTranscript(
          transcript.value?.segments ?? [],
          response.overlays,
        )
          ? "saved"
          : "idle";
      }
    } catch {
      if (
        generationAtStart === speakerOverlayGeneration &&
        revisionAtStart === speakerOverlayRevision.value
      ) {
        speakerOverlayStatus.value = "failed";
        speakerOverlayErrorMessage.value = "Namnen kunde inte sparas.";
      }
    } finally {
      const changedDuringSave = revisionAtStart !== speakerOverlayRevision.value;
      speakerOverlaySaveInFlight = false;
      if (
        generationAtStart === speakerOverlayGeneration &&
        (speakerOverlaySaveQueued || changedDuringSave)
      ) {
        speakerOverlaySaveQueued = false;
        scheduleSpeakerOverlayAutosave();
      }
    }
  }

  return {
    handleSpeakerOverlayChanged,
    loadSpeakerOverlays,
    resetSpeakerOverlayState,
    speakerOverlayCoverageComplete,
    speakerOverlayEntries,
    speakerOverlayErrorMessage,
    speakerOverlayStatus,
  };
}
