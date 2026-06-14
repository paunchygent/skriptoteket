/**
 * Transcript progress parser specs.
 *
 * Domain purpose:
 *   Prove Sir Convert transcript progress snapshots stay contract-strict while
 *   accepting Task-364 pipeline estimates used by Skriptoteket progress UI.
 *
 * Relationships:
 *   - Exercises `transcriptProgressParsers.ts` through `parseTranscriptJob`.
 *   - Complements transcript Gateway transport coverage in `transcriptClient.spec.ts`.
 */

import { describe, expect, it } from "vitest";

import { parseTranscriptJob } from "./transcriptParsers";

describe("transcript progress parsers", () => {
  it("rejects malformed transcript progress snapshots instead of accepting loose fields", () => {
    expect(() =>
      parseTranscriptJob({
        job: {
          job_id: "job_transcript_1",
          status: "running",
          progress: {
            stage: "transcribing",
            last_heartbeat_at: "2026-06-13T08:15:30Z",
            audio_processed_media_seconds: 180,
            audio_total_media_seconds: 120,
            audio_percent_complete: 140,
            audio_current_chunk_index: 4,
            audio_total_chunks: 3,
          },
        },
      }),
    ).toThrow("Transcript processed media seconds exceed total media seconds.");
  });

  it("parses Task-364 pipeline progress estimates alongside observed chunk facts", () => {
    expect(
      parseTranscriptJob({
        job: {
          job_id: "job_transcript_1",
          status: "running",
          progress: {
            stage: "diarizing",
            last_heartbeat_at: "2026-06-14T08:15:30Z",
            current_phase_started_at: "2026-06-14T08:14:00Z",
            audio_total_media_seconds: 600,
            audio_processed_media_seconds: 0,
            audio_percent_complete: 0,
            audio_current_chunk_index: 0,
            audio_total_chunks: 2,
            audio_pipeline_percent_complete: 18.5,
            audio_pipeline_eta_seconds: 130,
            phase_timings_ms: {
              audio_probe_normalize_ms: 1400,
              audio_diarization_ms: 0,
            },
          },
        },
      }),
    ).toMatchObject({
      progress: {
        audioPipelineEtaSeconds: 130,
        audioPipelinePercentComplete: 18.5,
        currentChunkIndex: 0,
        percentComplete: 0,
        phase: "diarizing",
        phaseTimingsMs: {
          audio_probe_normalize_ms: 1400,
          audio_diarization_ms: 0,
        },
        processedMediaSeconds: 0,
        totalChunks: 2,
        totalMediaSeconds: 600,
      },
    });
  });
});
