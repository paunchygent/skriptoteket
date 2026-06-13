/**
 * Sir Convert transcript formatter replay parsers.
 *
 * Purpose:
 *   Validate overlay-aware replay result and artifact manifests before
 *   Skriptoteket records producer-owned TXT/Markdown/VTT/SRT refs.
 *
 * Relationships:
 *   - Used by `transcriptReplayClient.ts`.
 *   - Keeps replay parsing separate from audio transcript JSON parsing.
 */

import type {
  SirConvertTranscriptArtifactEntry,
  SirConvertTranscriptFormatterArtifactKey,
  SirConvertTranscriptFormatterOutputArtifact,
  SirConvertTranscriptFormatterReplayArtifactManifest,
  SirConvertTranscriptFormatterReplayTerminalResult,
  SirConvertTranscriptJob,
} from "./transcriptTypes";
import {
  SIR_CONVERT_TRANSCRIPT_ARTIFACT_CONTENT_TYPES,
  SIR_CONVERT_TRANSCRIPT_ARTIFACT_KEY_BY_OUTPUT_ARTIFACT,
} from "./transcriptTypes";

type JsonRecord = Record<string, unknown>;
type SirConvertTranscriptReplayArtifactEntry = Omit<
  SirConvertTranscriptArtifactEntry,
  "artifact_key"
> & {
  artifact_key: SirConvertTranscriptFormatterArtifactKey;
};

function isRecord(value: unknown): value is JsonRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function readRecord(value: unknown, fieldName: string): JsonRecord {
  if (isRecord(value)) return value;
  throw new Error(`Sir Convert replay field '${fieldName}' is not an object.`);
}

function readString(value: unknown, fieldName: string): string {
  if (typeof value === "string" && value.length > 0) return value;
  throw new Error(`Sir Convert replay field '${fieldName}' is missing.`);
}

function readNullableString(value: unknown, fieldName: string): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value === "string") return value;
  throw new Error(`Sir Convert replay field '${fieldName}' is not a string.`);
}

function readNumber(value: unknown, fieldName: string): number {
  if (typeof value === "number" && Number.isFinite(value) && value >= 0) return value;
  throw new Error(`Sir Convert replay field '${fieldName}' is not a non-negative number.`);
}

function readReplayStatus(value: unknown): SirConvertTranscriptJob["status"] {
  const status = readString(value, "status");
  switch (status) {
    case "submitted":
    case "queued":
    case "running":
    case "processing":
    case "succeeded":
    case "failed":
    case "canceled":
    case "cancelled":
      return status;
    default:
      throw new Error(`Unknown Sir Convert replay status '${status}'.`);
  }
}

function readReplayArtifactKey(value: unknown): SirConvertTranscriptFormatterArtifactKey {
  const artifactKey = readString(value, "artifact_key");
  switch (artifactKey) {
    case "transcript_txt":
    case "transcript_md":
    case "transcript_vtt":
    case "transcript_srt":
      return artifactKey;
    case "transcript_json":
      throw new Error("Sir Convert replay manifest must not include transcript_json.");
    default:
      throw new Error(`Unknown Sir Convert replay artifact key '${artifactKey}'.`);
  }
}

function readAvailability(value: unknown): SirConvertArtifactEntryAvailability {
  const availability = readString(value, "availability");
  switch (availability) {
    case "available":
    case "unavailable":
    case "failed":
    case "unrequested":
      return availability;
    default:
      throw new Error(`Unknown Sir Convert replay artifact availability '${availability}'.`);
  }
}

type SirConvertArtifactEntryAvailability = SirConvertTranscriptArtifactEntry["availability"];

function requestedKeys(
  requestedArtifacts: readonly SirConvertTranscriptFormatterOutputArtifact[],
): SirConvertTranscriptFormatterArtifactKey[] {
  return requestedArtifacts.map((artifact) => {
    switch (artifact) {
      case "txt":
        return SIR_CONVERT_TRANSCRIPT_ARTIFACT_KEY_BY_OUTPUT_ARTIFACT.txt;
      case "md":
        return SIR_CONVERT_TRANSCRIPT_ARTIFACT_KEY_BY_OUTPUT_ARTIFACT.md;
      case "vtt":
        return SIR_CONVERT_TRANSCRIPT_ARTIFACT_KEY_BY_OUTPUT_ARTIFACT.vtt;
      case "srt":
        return SIR_CONVERT_TRANSCRIPT_ARTIFACT_KEY_BY_OUTPUT_ARTIFACT.srt;
    }
  });
}

function emptyFormatterArtifacts(): Record<
  SirConvertTranscriptFormatterArtifactKey,
  SirConvertTranscriptReplayArtifactEntry | undefined
> {
  return {
    transcript_txt: undefined,
    transcript_md: undefined,
    transcript_vtt: undefined,
    transcript_srt: undefined,
  };
}

function parseReplayArtifactEntry(payload: unknown): SirConvertTranscriptReplayArtifactEntry {
  const entry = readRecord(payload, "artifact");
  const artifactKey = readReplayArtifactKey(entry.artifact_key);
  const availability = readAvailability(entry.availability);
  const unavailableCode =
    typeof entry.unavailable_code === "string" && entry.unavailable_code.length > 0
      ? entry.unavailable_code
      : undefined;
  if (unavailableCode === "not_implemented") {
    throw new Error(`Sir Convert replay artifact '${artifactKey}' is not implemented.`);
  }
  if (availability !== "available") {
    return {
      artifact_key: artifactKey,
      availability,
      ...(unavailableCode ? { unavailable_code: unavailableCode } : {}),
    };
  }
  const contentType = readString(entry.content_type, "content_type");
  const expectedContentType = SIR_CONVERT_TRANSCRIPT_ARTIFACT_CONTENT_TYPES[artifactKey];
  if (contentType !== expectedContentType) {
    throw new Error(
      `Sir Convert replay artifact '${artifactKey}' has content type '${contentType}' instead of '${expectedContentType}'.`,
    );
  }
  return {
    artifact_key: artifactKey,
    availability,
    content_type: contentType,
    filename: readString(entry.filename, "filename"),
    retrieval_path: readString(entry.retrieval_path, "retrieval_path"),
    sha256: readNullableString(entry.sha256, "sha256"),
    size_bytes: readNumber(entry.size_bytes, "size_bytes"),
  };
}

export function parseTranscriptFormatterReplayJob(payload: unknown): SirConvertTranscriptJob {
  const root = readRecord(payload, "payload");
  const job = isRecord(root.job) ? root.job : root;
  const status = readReplayStatus(job.status);
  return {
    jobId: readString(job.job_id, "job.job_id"),
    progress: {
      currentChunkIndex: null,
      currentPhaseStartedAt: null,
      lastHeartbeatAt: null,
      percentComplete: null,
      phase: null,
      phaseTimingsMs: {},
      processedMediaSeconds: null,
      status,
      totalChunks: null,
      totalMediaSeconds: null,
    },
    status,
  };
}

export function parseTranscriptFormatterReplayResult(
  payload: unknown,
): SirConvertTranscriptFormatterReplayTerminalResult {
  const root = readRecord(payload, "payload");
  const result = readRecord(root.result, "result");
  const artifact = readRecord(result.artifact, "result.artifact");
  const metadata = readRecord(result.conversion_metadata, "result.conversion_metadata");
  const pipelineUsed = readString(metadata.pipeline_used, "conversion_metadata.pipeline_used");
  if (pipelineUsed !== "transcript_json_to_transcript_bundle_replay_v2") {
    throw new Error(`Unknown Sir Convert replay pipeline '${pipelineUsed}'.`);
  }
  const backendUsed = metadata.backend_used ?? null;
  const accelerationUsed = metadata.acceleration_used ?? null;
  if (backendUsed !== null || accelerationUsed !== null) {
    throw new Error("Sir Convert replay metadata must not include runtime provider details.");
  }
  const filename = readString(artifact.filename, "result.artifact.filename");
  if (filename !== "transcript_replay_bundle_manifest.json") {
    throw new Error(`Unknown Sir Convert replay artifact '${filename}'.`);
  }
  const format = readString(artifact.format, "result.artifact.format");
  if (format !== "transcript_bundle") {
    throw new Error(`Unknown Sir Convert replay result format '${format}'.`);
  }
  const contentType = readString(artifact.content_type, "result.artifact.content_type");
  if (contentType !== "application/json") {
    throw new Error(`Unknown Sir Convert replay result content type '${contentType}'.`);
  }
  return {
    artifact: {
      content_type: "application/json",
      filename,
      format: "transcript_bundle",
      sha256: readString(artifact.sha256, "result.artifact.sha256"),
      size_bytes: readNumber(artifact.size_bytes, "result.artifact.size_bytes"),
    },
    conversion_metadata: {
      acceleration_used: null,
      backend_used: null,
      options_fingerprint: readString(
        metadata.options_fingerprint,
        "conversion_metadata.options_fingerprint",
      ),
      pipeline_used: "transcript_json_to_transcript_bundle_replay_v2",
    },
    rawResult: root,
  };
}

export function parseTranscriptFormatterReplayArtifactManifest(
  payload: unknown,
  requestedArtifacts: readonly SirConvertTranscriptFormatterOutputArtifact[],
): SirConvertTranscriptFormatterReplayArtifactManifest {
  const root = readRecord(payload, "manifest");
  const outputFormat = readString(root.output_format, "output_format");
  if (outputFormat !== "transcript_bundle") {
    throw new Error(`Unknown Sir Convert replay output format '${outputFormat}'.`);
  }
  if (!Array.isArray(root.artifacts)) {
    throw new Error("Sir Convert replay manifest is missing artifacts.");
  }
  const artifacts = root.artifacts.map((entry) => parseReplayArtifactEntry(entry));
  const seen = new Set<SirConvertTranscriptFormatterArtifactKey>();
  const formatterArtifacts = emptyFormatterArtifacts();
  for (const artifact of artifacts) {
    if (seen.has(artifact.artifact_key)) {
      throw new Error(`Duplicate Sir Convert replay artifact key '${artifact.artifact_key}'.`);
    }
    seen.add(artifact.artifact_key);
    formatterArtifacts[artifact.artifact_key] = artifact;
  }
  for (const requestedKey of requestedKeys(requestedArtifacts)) {
    const artifact = formatterArtifacts[requestedKey];
    if (!artifact || artifact.availability !== "available") {
      throw new Error(`Sir Convert replay is missing requested artifact '${requestedKey}'.`);
    }
  }
  return {
    api_version: "v2",
    artifacts,
    formatterArtifacts,
    job_id: readString(root.job_id, "job_id"),
    output_format: "transcript_bundle",
    rawManifest: root,
  };
}
