/**
 * Transcript source-file and speaker-control state.
 *
 * Domain purpose:
 *   Own browser-local transcript intake choices before an authenticated
 *   Gateway submit starts.
 *
 * Relationships:
 *   - Used by `ConversionHubTranscriptHost`.
 *   - Emits Sir Convert speaker-control values consumed by the Gateway runtime.
 */

import { computed, ref } from "vue";

import type { TranscriptSpeakerControl } from "../../../api/sirConvertGateway";

export type TranscriptSourceFileSelection = {
  file: File;
  name: string;
  sizeLabel: string;
};

export type TranscriptSpeakerMode = TranscriptSpeakerControl["mode"];

const AUDIO_EXTENSIONS = new Set([
  ".wav",
  ".mp3",
  ".m4a",
  ".aac",
  ".flac",
  ".ogg",
  ".opus",
  ".webm",
  ".aiff",
  ".mp4",
  ".mov",
  ".mkv",
]);

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const kibibytes = bytes / 1024;
  if (kibibytes < 1024) {
    return `${kibibytes.toLocaleString("sv-SE", { maximumFractionDigits: 0 })} kB`;
  }
  return `${(kibibytes / 1024).toLocaleString("sv-SE", { maximumFractionDigits: 1 })} MB`;
}

function fileExtension(file: File): string {
  const filename = file.name.toLowerCase();
  return filename.includes(".") ? filename.slice(filename.lastIndexOf(".")) : "";
}

function toSelection(file: File): TranscriptSourceFileSelection {
  return {
    file,
    name: file.name,
    sizeLabel: formatFileSize(file.size),
  };
}

export function useTranscriptSourceFile() {
  const selectedTranscriptFile = ref<TranscriptSourceFileSelection | null>(null);
  const transcriptFileError = ref<string | null>(null);
  const speakerMode = ref<TranscriptSpeakerMode>("auto");
  const speakerCount = ref(2);
  const minSpeakers = ref(2);
  const maxSpeakers = ref(4);

  const speakerError = computed(() => {
    if (speakerMode.value === "known_speaker_count" && speakerCount.value < 1) {
      return "Ange minst en talare.";
    }
    if (speakerMode.value === "speaker_range") {
      if (minSpeakers.value < 1 || maxSpeakers.value < 1) return "Ange minst en talare.";
      if (maxSpeakers.value < minSpeakers.value) {
        return "Högsta antal talare måste vara minst lika högt som lägsta antal.";
      }
    }
    return null;
  });

  const speakerControl = computed<TranscriptSpeakerControl>(() => {
    if (speakerMode.value === "known_speaker_count") {
      return { mode: "known_speaker_count", speakerCount: speakerCount.value };
    }
    if (speakerMode.value === "speaker_range") {
      return {
        maxSpeakers: maxSpeakers.value,
        minSpeakers: minSpeakers.value,
        mode: "speaker_range",
      };
    }
    return { mode: "auto" };
  });

  function selectTranscriptFile(file: File): void {
    if (!AUDIO_EXTENSIONS.has(fileExtension(file))) {
      selectedTranscriptFile.value = null;
      transcriptFileError.value = "Välj en ljud- eller videofil med ljud.";
      return;
    }
    selectedTranscriptFile.value = toSelection(file);
    transcriptFileError.value = null;
  }

  function selectDroppedTranscriptFiles(files: File[]): void {
    const [file] = files;
    if (file) {
      selectTranscriptFile(file);
    }
  }

  function clearTranscriptFile(): void {
    selectedTranscriptFile.value = null;
    transcriptFileError.value = null;
  }

  function resetTranscriptChoices(): void {
    clearTranscriptFile();
    speakerMode.value = "auto";
    speakerCount.value = 2;
    minSpeakers.value = 2;
    maxSpeakers.value = 4;
  }

  return {
    clearTranscriptFile,
    maxSpeakers,
    minSpeakers,
    resetTranscriptChoices,
    selectDroppedTranscriptFiles,
    selectTranscriptFile,
    selectedTranscriptFile,
    speakerControl,
    speakerCount,
    speakerError,
    speakerMode,
    transcriptFileError,
  };
}
