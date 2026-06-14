/**
 * Conversion Hub transcript formatter artifact action specs.
 *
 * Domain purpose:
 *   Prove download and Mina filer save commands use Skriptoteket's
 *   owner-scoped formatter artifact API rather than browser-local formatting or
 *   direct Sir Convert paths.
 *
 * Relationships:
 *   - Exercises `conversionHubTranscriptFormatterArtifactActions.ts`.
 *   - Complements transcript workspace action-state specs.
 */

import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  downloadConversionHubTranscriptFormatterArtifact,
  saveConversionHubTranscriptFormatterArtifact,
} from "./conversionHubTranscriptFormatterArtifactActions";
import { useAuthStore } from "../stores/auth";

describe("conversionHubTranscriptFormatterArtifactActions", () => {
  const downloadUrl =
    "/api/v1/apps/documents.conversion_hub/transcripts/saved-transcript-1" +
    "/formatter-artifacts/transcript_txt/download";
  const saveUrl =
    "/api/v1/apps/documents.conversion_hub/transcripts/saved-transcript-1" +
    "/formatter-artifacts/transcript_txt/save";

  beforeEach(() => {
    setActivePinia(createPinia());
    vi.mocked(fetch).mockReset();
    const auth = useAuthStore();
    auth.csrfToken = "csrf-token";
  });

  it("downloads a formatter artifact through the protected Skriptoteket API", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response("overlay-aware transcript", {
        headers: {
          "content-disposition": 'attachment; filename="transkript-abcdef12.txt"',
          "content-type": "text/plain",
        },
        status: 200,
      }),
    );

    const response = await downloadConversionHubTranscriptFormatterArtifact({
      artifactKey: "transcript_txt",
      transcriptId: "saved-transcript-1",
    });

    expect(response.filename).toBe("transkript-abcdef12.txt");
    expect(response.contentType).toBe("text/plain");
    expect(response.blob).toBeInstanceOf(Blob);
    expect(fetch).toHaveBeenCalledWith(
      downloadUrl,
      expect.objectContaining({
        credentials: "include",
        method: "GET",
      }),
    );
    const headers = vi.mocked(fetch).mock.calls[0][1]?.headers as Headers;
    expect(headers.get("X-API-Key")).toBeNull();
  });

  it("saves a formatter artifact through the protected Skriptoteket API", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          source_artifact_id:
            "documents.conversion_hub:transcript-export:local-job:transcript_txt",
          vault_artifact: {
            bytes: 24,
            created_at: "2026-06-13T12:05:00Z",
            file_id: "vault-file-1",
            name: "transkript-abcdef12.txt",
          },
        }),
        {
          headers: { "content-type": "application/json" },
          status: 200,
        },
      ),
    );

    const saved = await saveConversionHubTranscriptFormatterArtifact({
      artifactKey: "transcript_txt",
      transcriptId: "saved-transcript-1",
    });

    expect(saved.vault_artifact.name).toBe("transkript-abcdef12.txt");
    expect(fetch).toHaveBeenCalledWith(
      saveUrl,
      expect.objectContaining({
        credentials: "include",
        method: "POST",
      }),
    );
    const headers = vi.mocked(fetch).mock.calls[0][1]?.headers as Headers;
    expect(headers.get("X-CSRF-Token")).toBe("csrf-token");
    expect(headers.get("X-API-Key")).toBeNull();
  });
});
