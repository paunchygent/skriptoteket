/**
 * Conversion Hub transcript formatter export API specs.
 *
 * Domain purpose:
 *   Prove the browser records export intent and observes product-owned
 *   formatter export state through Skriptoteket transcript routes.
 *
 * Relationships:
 *   - Exercises `conversionHubTranscriptFormatterExports.ts`.
 *   - Complements backend product export handler and route tests.
 */

import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  getConversionHubTranscriptFormatterExport,
  requestConversionHubTranscriptFormatterExport,
} from "./conversionHubTranscriptFormatterExports";
import { useAuthStore } from "../stores/auth";

function jsonResponse(payload: unknown): Response {
  return new Response(JSON.stringify(payload), {
    headers: { "content-type": "application/json" },
    status: 200,
  });
}

function fetchInit(index: number): RequestInit {
  const init = vi.mocked(fetch).mock.calls[index]?.[1];
  if (!init) throw new Error(`Missing fetch init for call ${index}.`);
  return init;
}

describe("conversionHubTranscriptFormatterExports", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.mocked(fetch).mockReset();
    const auth = useAuthStore();
    auth.csrfToken = "csrf-token";
  });

  it("requests product-owned formatter export state through the saved transcript route", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({
        artifacts: [
          {
            artifact_key: "transcript_txt",
            content_type: "text/plain",
            filename: "transcript_txt.txt",
            requested_artifact: "txt",
            size_bytes: 12,
          },
        ],
        conversion_hub_job_id: "local-export-1",
        created_at: "2026-06-14T08:00:00Z",
        error_message: null,
        requested_artifacts: ["txt", "md", "vtt", "srt"],
        status: "succeeded",
        transcript_id: "saved-transcript-1",
        updated_at: "2026-06-14T08:00:01Z",
      }),
    );

    const response = await requestConversionHubTranscriptFormatterExport({
      transcriptId: "saved-transcript-1",
    });

    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/apps/documents.conversion_hub/transcripts/saved-transcript-1/formatter-exports",
      expect.objectContaining({ credentials: "include", method: "POST" }),
    );
    expect(fetchInit(0).body).toBe(
      JSON.stringify({ requested_artifacts: ["txt", "md", "vtt", "srt"] }),
    );
    expect([...new Headers(fetchInit(0).headers)].map(([key]) => key)).toContain("x-csrf-token");
    expect(response).toEqual({
      artifacts: [
        {
          artifact_key: "transcript_txt",
          content_type: "text/plain",
          filename: "transcript_txt.txt",
          requested_artifact: "txt",
          size_bytes: 12,
        },
      ],
      conversion_hub_job_id: "local-export-1",
      created_at: "2026-06-14T08:00:00Z",
      error_message: null,
      requested_artifacts: ["txt", "md", "vtt", "srt"],
      status: "succeeded",
      transcript_id: "saved-transcript-1",
      updated_at: "2026-06-14T08:00:01Z",
    });
  });

  it("reads product formatter export state without transcript JSON or producer payloads", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({
        artifacts: [],
        conversion_hub_job_id: null,
        created_at: null,
        error_message: null,
        requested_artifacts: ["txt", "md", "vtt", "srt"],
        status: "not_requested",
        transcript_id: "saved-transcript-1",
        updated_at: null,
      }),
    );

    const response = await getConversionHubTranscriptFormatterExport({
      transcriptId: "saved-transcript-1",
    });

    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/apps/documents.conversion_hub/transcripts/saved-transcript-1/formatter-exports",
      expect.objectContaining({ credentials: "include", method: "GET" }),
    );
    expect(Object.keys(response).sort()).toEqual([
      "artifacts",
      "conversion_hub_job_id",
      "created_at",
      "error_message",
      "requested_artifacts",
      "status",
      "transcript_id",
      "updated_at",
    ]);
  });
});
