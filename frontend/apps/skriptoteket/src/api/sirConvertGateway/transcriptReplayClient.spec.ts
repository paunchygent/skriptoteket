/**
 * Transcript formatter replay Gateway client specs.
 *
 * Domain purpose:
 *   Prove saved transcript replay jobs use the authenticated HuleEdu Gateway
 *   path and accept only producer-owned formatter artifact refs.
 *
 * Relationships:
 *   - Exercises replay methods on `client.ts`.
 *   - Complements backend replay request/provenance tests.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

import { createSirConvertGatewayClient } from "./client";
import type { SirConvertTranscriptFormatterReplayJobSpec } from "./transcriptTypes";

function jsonResponse(payload: unknown, init: ResponseInit = {}): Response {
  const headers = new Headers(init.headers);
  if (!headers.has("content-type")) {
    headers.set("content-type", "application/json");
  }
  return new Response(JSON.stringify(payload), { ...init, headers });
}

type FetchMock = ReturnType<typeof vi.fn<typeof fetch>>;

type ReplayArtifactFixture = {
  artifact_key: string;
  availability: string;
  content_type?: string;
  filename?: string;
  retrieval_path?: string;
  sha256?: string;
  size_bytes?: number;
};

type ReplayManifestFixture = {
  api_version: "v2";
  job_id: string;
  output_format: "transcript_bundle";
  artifacts: ReplayArtifactFixture[];
};

function fetchInit(fetcher: FetchMock, index: number): RequestInit {
  const init = fetcher.mock.calls[index]?.[1];
  if (!init) throw new Error(`Missing fetch init for call ${index}.`);
  return init;
}

function fetchHeaders(fetcher: FetchMock, index: number): Headers {
  const headers = fetchInit(fetcher, index).headers;
  if (headers instanceof Headers) return headers;
  throw new Error(`Missing Headers instance for call ${index}.`);
}

function fetchFormData(fetcher: FetchMock, index: number): FormData {
  const body = fetchInit(fetcher, index).body;
  if (body instanceof FormData) return body;
  throw new Error(`Missing FormData body for call ${index}.`);
}

function replayJobSpec(): SirConvertTranscriptFormatterReplayJobSpec {
  return {
    api_version: "v2",
    source: {
      kind: "upload",
      filename: "saved-transcript-1.json",
      format: "transcript_json",
    },
    conversion: { output_format: "transcript_bundle" },
    transcript_formatter_options: {
      schema_version: "transcript_formatter_replay_v1",
      requested_artifacts: ["txt", "md"],
      speaker_label_overrides: [
        { canonical_speaker_label: "SPEAKER_00", display_name: "Anna Andersson" },
      ],
    },
    retention: { pin: false },
  };
}

function replayResult(): Record<string, unknown> {
  return {
    result: {
      artifact: {
        filename: "transcript_replay_bundle_manifest.json",
        format: "transcript_bundle",
        content_type: "application/json",
        size_bytes: 42,
        sha256: "abc",
      },
      conversion_metadata: {
        pipeline_used: "transcript_json_to_transcript_bundle_replay_v2",
        backend_used: null,
        acceleration_used: null,
        options_fingerprint: "sha256:abc",
      },
    },
  };
}

function replayArtifacts(): ReplayArtifactFixture[] {
  return [
      {
        artifact_key: "transcript_txt",
        availability: "available",
        content_type: "text/plain",
        filename: "transcript_txt.txt",
        size_bytes: 12,
        sha256: "txt",
        retrieval_path: "/v2/convert/jobs/job_replay_1/artifacts/transcript_txt",
      },
      {
        artifact_key: "transcript_md",
        availability: "available",
        content_type: "text/markdown",
        filename: "transcript_md.md",
        size_bytes: 24,
        sha256: "md",
        retrieval_path: "/v2/convert/jobs/job_replay_1/artifacts/transcript_md",
      },
    ];
}

function replayManifest(artifacts: ReplayArtifactFixture[] = replayArtifacts()): ReplayManifestFixture {
  return {
    api_version: "v2",
    job_id: "job_replay_1",
    output_format: "transcript_bundle",
    artifacts,
  };
}

describe("Sir Convert transcript formatter replay Gateway client", () => {
  const fetcher = vi.fn<typeof fetch>();
  const client = createSirConvertGatewayClient({
    ensureCsrfToken: async () => "csrf-token",
    fetcher,
  });

  beforeEach(() => {
    fetcher.mockReset();
  });

  it("submits replay through the HuleEdu Gateway with prepared JobSpec and JSON upload", async () => {
    fetcher.mockResolvedValueOnce(
      jsonResponse(
        { job: { job_id: "job_replay_1", status: "queued" } },
        { headers: { "X-Idempotent-Replay": "false" } },
      ),
    );

    const submitted = await client.submitTranscriptFormatterReplay({
      contentType: "application/json",
      correlationId: "corr-replay-1",
      gatewayFilename: "saved-transcript-1.json",
      idempotencyKey: "idem-replay-1",
      jobSpec: replayJobSpec(),
      requestedArtifacts: ["txt", "md"],
      transcriptJson: { schema_version: "transcript_json_v1" },
      waitSeconds: 20,
    });

    expect(submitted.jobId).toBe("job_replay_1");
    expect(fetcher).toHaveBeenCalledWith(
      "/sir-convert/v2/convert/jobs?wait_seconds=20",
      expect.objectContaining({ credentials: "include", method: "POST" }),
    );
    expect(fetchHeaders(fetcher, 0).get("X-CSRF-Token")).toBe("csrf-token");
    expect(fetchHeaders(fetcher, 0).get("Idempotency-Key")).toBe("idem-replay-1");
    const body = fetchFormData(fetcher, 0);
    expect(body.get("file")).toBeInstanceOf(File);
    expect(JSON.parse(String(body.get("job_spec")))).toMatchObject({
      source: { format: "transcript_json" },
      conversion: { output_format: "transcript_bundle" },
      transcript_formatter_options: {
        schema_version: "transcript_formatter_replay_v1",
        requested_artifacts: ["txt", "md"],
      },
      retention: { pin: false },
    });
  });

  it("accepts replay result and requested formatter artifact refs without transcript_json", async () => {
    fetcher
      .mockResolvedValueOnce(jsonResponse(replayResult()))
      .mockResolvedValueOnce(jsonResponse(replayManifest()));

    const result = await client.getTranscriptFormatterReplayResult({
      correlationId: "corr-replay-1",
      jobId: "job_replay_1",
    });
    const manifest = await client.listTranscriptFormatterReplayArtifacts({
      correlationId: "corr-replay-1",
      jobId: "job_replay_1",
      requestedArtifacts: ["txt", "md"],
    });

    expect(result.conversion_metadata.pipeline_used).toBe(
      "transcript_json_to_transcript_bundle_replay_v2",
    );
    expect(manifest.artifacts.map((artifact) => artifact.artifact_key)).toEqual([
      "transcript_txt",
      "transcript_md",
    ]);
  });

  it("rejects replay manifests with transcript_json or missing requested artifacts", async () => {
    fetcher.mockResolvedValueOnce(
      jsonResponse({
        ...replayManifest(),
        artifacts: [
          ...replayArtifacts(),
          { artifact_key: "transcript_json", availability: "available" },
        ],
      }),
    );

    await expect(
      client.listTranscriptFormatterReplayArtifacts({
        correlationId: "corr-replay-1",
        jobId: "job_replay_1",
        requestedArtifacts: ["txt", "md"],
      }),
    ).rejects.toThrow("transcript_json");

    fetcher.mockResolvedValueOnce(
      jsonResponse({
        ...replayManifest(),
        artifacts: replayArtifacts().slice(0, 1),
      }),
    );

    await expect(
      client.listTranscriptFormatterReplayArtifacts({
        correlationId: "corr-replay-1",
        jobId: "job_replay_1",
        requestedArtifacts: ["txt", "md"],
      }),
    ).rejects.toThrow("missing requested");
  });
});
