/**
 * Transcript progress display helpers.
 *
 * Domain purpose:
 *   Convert Sir Convert transcript lifecycle and browser upload progress into
 *   compact teacher-facing labels for the Conversion Hub transcript workspace.
 *
 * Relationships:
 *   - Used by `TranscriptWorkspaceShell.vue`.
 *   - Keeps display formatting separate from Gateway runtime orchestration.
 */

import type { SirConvertTranscriptJob } from "../../../api/sirConvertGateway";
import type { TranscriptUploadState } from "./useTranscriptGatewayRuntime";

export function isUploading(uploadState: TranscriptUploadState): boolean {
  return uploadState.status !== "idle";
}

export function uploadProgressLabel(uploadState: TranscriptUploadState): string {
  if (uploadState.status === "finalizing") {
    return "Skapar transkriberingsjobb.";
  }
  return "Laddar upp inspelningen.";
}

export function transcriptProgressLabel(job: SirConvertTranscriptJob | null): string {
  if (!job) return "Förbereder ljudet";
  if (job.status === "submitted" || job.status === "queued" || !job.progress.phase) {
    return "Väntar";
  }
  const phase = job.progress.phase;
  if (phase === "starting" || phase === "normalizing_audio") {
    return "Förbereder ljudet";
  }
  if (phase === "probing_media") {
    return "Läser in ljud";
  }
  if (phase === "transcribing") {
    return "Skriver ut samtalet";
  }
  if (phase === "diarizing") {
    return "Hittar talare";
  }
  if (phase === "aligning_segments") {
    return "Gör texten klar";
  }
  if (phase === "packaging") {
    return "Gör texten klar";
  }
  return "Bearbetar inspelningen";
}

export function progressPercentValue(
  job: SirConvertTranscriptJob | null,
  uploadState: TranscriptUploadState,
): number | null {
  if (!job && isUploading(uploadState)) return uploadState.percentComplete;
  const pipelinePercent = job?.progress.audioPipelinePercentComplete;
  if (pipelinePercent !== null && pipelinePercent !== undefined) return pipelinePercent;
  return job?.progress.percentComplete ?? null;
}

export function progressPercent(
  job: SirConvertTranscriptJob | null,
  uploadState: TranscriptUploadState,
): string | null {
  const percent = progressPercentValue(job, uploadState);
  if (percent === null || percent <= 0) return null;
  return `${Math.round(percent)} %`;
}

function formatDuration(seconds: number): string {
  const rounded = Math.max(0, Math.round(seconds));
  const minutes = Math.floor(rounded / 60);
  const remainingSeconds = String(rounded % 60).padStart(2, "0");
  return `${minutes}:${remainingSeconds}`;
}

export function progressDuration(job: SirConvertTranscriptJob | null): string | null {
  const processed = job?.progress.processedMediaSeconds;
  const total = job?.progress.totalMediaSeconds;
  if (processed === null || processed === undefined || total === null || total === undefined) {
    return null;
  }
  return `${formatDuration(processed)} av ${formatDuration(total)}`;
}

function parseTimestamp(value: string | null | undefined): number | null {
  if (!value) return null;
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function completedPhaseTimingsMs(job: SirConvertTranscriptJob | null): number {
  return Object.values(job?.progress.phaseTimingsMs ?? {}).reduce(
    (sum, timing) => sum + Math.max(0, timing ?? 0),
    0,
  );
}

export function progressElapsed(job: SirConvertTranscriptJob | null): string | null {
  const phaseStart = parseTimestamp(job?.progress.currentPhaseStartedAt);
  const heartbeat = parseTimestamp(job?.progress.lastHeartbeatAt);
  const activePhaseMs =
    phaseStart !== null && heartbeat !== null && heartbeat >= phaseStart
      ? heartbeat - phaseStart
      : 0;
  const elapsedMs = completedPhaseTimingsMs(job) + activePhaseMs;
  if (elapsedMs <= 0) return null;
  return formatDuration(elapsedMs / 1000);
}

export function progressEta(job: SirConvertTranscriptJob | null): string | null {
  const etaSeconds = job?.progress.audioPipelineEtaSeconds;
  if (etaSeconds === null || etaSeconds === undefined) return null;
  return formatDuration(etaSeconds);
}

export function progressChunks(job: SirConvertTranscriptJob | null): string | null {
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

export function progressHeartbeat(job: SirConvertTranscriptJob | null): string | null {
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

function formatBytes(bytes: number): string {
  if (bytes >= 1024 * 1024) {
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }
  if (bytes >= 1024) {
    return `${Math.round(bytes / 1024)} kB`;
  }
  return `${bytes} B`;
}

export function uploadProgressBytes(uploadState: TranscriptUploadState): string | null {
  if (!isUploading(uploadState)) return null;
  if (uploadState.totalBytes !== null) {
    return `${formatBytes(uploadState.loadedBytes)} av ${formatBytes(uploadState.totalBytes)}`;
  }
  return formatBytes(uploadState.loadedBytes);
}
