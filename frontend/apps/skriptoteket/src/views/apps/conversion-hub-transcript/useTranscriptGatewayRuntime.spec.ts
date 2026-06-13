/**
 * Transcript Gateway runtime specs.
 *
 * Domain purpose:
 *   Prove transcript job polling and abort feedback stay truthful when Gateway
 *   cancel requests are accepted or rejected.
 *
 * Relationships:
 *   - Exercises `useTranscriptGatewayRuntime` as the transcript lane state
 *     orchestrator.
 *   - Complements DOM feedback proof in `TranscriptWorkspaceShell.spec.ts`.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { defineComponent, h } from "vue";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  SirConvertGatewayError,
  type SirConvertTranscriptJobSpec,
} from "../../../api/sirConvertGateway";
import {
  type TranscriptGatewayRuntimeOptions,
  useTranscriptGatewayRuntime,
} from "./useTranscriptGatewayRuntime";

type RuntimeWithAbort = ReturnType<typeof useTranscriptGatewayRuntime> & {
  abortState: {
    value: {
      message: string | null;
      status: string;
    };
  };
  uploadState: {
    value: {
      loadedBytes: number;
      percentComplete: number | null;
      status: string;
      totalBytes: number | null;
    };
  };
};

type GatewayRuntimeClient = NonNullable<TranscriptGatewayRuntimeOptions["client"]>;

function transcriptFile(): File {
  return new File(["lesson audio"], "lektion.m4a", { type: "audio/mp4" });
}

function transcriptJob(
  status: "running" | "succeeded" | "canceled",
): Awaited<ReturnType<GatewayRuntimeClient["getTranscriptJob"]>> {
  return {
    jobId: "job_transcript_1",
    progress: {
      currentChunkIndex: status === "running" ? 1 : null,
      currentPhaseStartedAt: "2026-06-13T08:14:00Z",
      lastHeartbeatAt: "2026-06-13T08:15:30Z",
      percentComplete: status === "running" ? 35 : 100,
      phase: status === "running" ? "transcribing" : status,
      phaseTimingsMs: {},
      processedMediaSeconds: status === "running" ? 42 : 120,
      status,
      totalChunks: status === "running" ? 3 : null,
      totalMediaSeconds: 120,
    },
    status,
  };
}

function transcriptJobSpec(): SirConvertTranscriptJobSpec {
  return {
    api_version: "v2",
    audio_transcription_options: {
      diarization: {
        max_speakers: null,
        min_speakers: null,
        mode: "auto",
        num_speakers: null,
      },
      language: "auto",
      max_duration_seconds: 7200,
      output_artifacts: ["json", "txt", "md", "vtt", "srt"],
    },
    conversion: { output_format: "transcript_bundle" },
    execution: {
      acceleration_policy: "gpu_required",
      document_timeout_seconds: 7200,
      priority: "normal",
    },
    retention: { pin: false },
    source: {
      filename: "lektion.m4a",
      format: "audio",
      kind: "upload",
    },
  };
}

function submittedTranscriptJob() {
  return {
    ...transcriptJob("running"),
    idempotentReplay: false,
    requestContext: {
      correlationId: "corr_transcript_1",
      idempotencyKey: "idem_transcript_1",
      jobSpec: transcriptJobSpec(),
    },
  };
}

function transcriptJson() {
  return {
    schemaVersion: "transcript_json_v1",
    segments: [
      {
        endSeconds: 1,
        id: "seg_1",
        speakerLabel: "SPEAKER_00",
        startSeconds: 0,
        text: "Hej.",
      },
    ],
    transcriptText: "Hej.",
  };
}

function runtimeClient(): GatewayRuntimeClient {
  return {
    cancelTranscriptJob: vi.fn(),
    downloadTranscriptJson: vi.fn().mockResolvedValue(transcriptJson()),
    getTranscriptJob: vi.fn(),
    getTranscriptResult: vi.fn().mockResolvedValue({}),
    listTranscriptArtifacts: vi.fn().mockResolvedValue({
      transcriptJsonArtifact: { artifact_key: "transcript_json", availability: "available" },
    }),
    submitTranscriptJob: vi.fn().mockResolvedValue(submittedTranscriptJob()),
  } satisfies GatewayRuntimeClient;
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((promiseResolve, promiseReject) => {
    resolve = promiseResolve;
    reject = promiseReject;
  });
  return { promise, reject, resolve };
}

function requireAbortSignal(signal: AbortSignal | null): AbortSignal {
  if (!signal) throw new Error("Expected an abort signal.");
  return signal;
}

function mountRuntime(client: GatewayRuntimeClient) {
  let runtime: ReturnType<typeof useTranscriptGatewayRuntime> | null = null;
  const Harness = defineComponent({
    setup() {
      runtime = useTranscriptGatewayRuntime({ client, pollIntervalMs: 1_000 });
      return () => h("div");
    },
  });
  const wrapper = mount(Harness);
  if (!runtime) throw new Error("Runtime harness did not initialize.");
  return { runtime: runtime as RuntimeWithAbort, wrapper };
}

describe("useTranscriptGatewayRuntime", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("keeps polling when an abort request fails", async () => {
    vi.useFakeTimers();
    const client = runtimeClient();
    vi.mocked(client.cancelTranscriptJob).mockRejectedValueOnce(new Error("cancel rejected"));
    vi.mocked(client.getTranscriptJob).mockResolvedValueOnce(transcriptJob("succeeded"));
    const { runtime, wrapper } = mountRuntime(client);

    const runPromise = runtime.submitAndPoll({
      file: transcriptFile(),
      speakerControl: { mode: "auto" },
    });
    await flushPromises();

    await runtime.cancelTranscript();
    await flushPromises();

    expect(runtime.abortState.value.status).toBe("failed");
    expect(runtime.abortState.value.message).toContain("Transkriberingen fortsätter");
    expect(runtime.status.value).toBe("running");

    await vi.advanceTimersByTimeAsync(1_000);
    await flushPromises();
    await expect(runPromise).resolves.toMatchObject({
      transcriptText: "Hej.",
    });

    expect(client.getTranscriptJob).toHaveBeenCalledWith({
      correlationId: "corr_transcript_1",
      jobId: "job_transcript_1",
    });
    expect(runtime.status.value).toBe("succeeded");
    wrapper.unmount();
  });

  it("exposes upload progress before the Gateway returns a transcript job id", async () => {
    const client = runtimeClient();
    const submitted = deferred<Awaited<ReturnType<GatewayRuntimeClient["submitTranscriptJob"]>>>();
    vi.mocked(client.submitTranscriptJob).mockImplementationOnce(async (params) => {
      params.onUploadProgress?.({
        loadedBytes: 5,
        percentComplete: 50,
        totalBytes: 10,
      });
      return await submitted.promise;
    });
    const { runtime, wrapper } = mountRuntime(client);

    const runPromise = runtime.submitAndPoll({
      file: transcriptFile(),
      speakerControl: { mode: "auto" },
    });
    await flushPromises();

    expect(runtime.status.value).toBe("running");
    expect(runtime.currentJob.value).toBeNull();
    expect(runtime.uploadState.value).toMatchObject({
      loadedBytes: 5,
      percentComplete: 50,
      status: "uploading",
      totalBytes: 10,
    });

    submitted.resolve({
      ...transcriptJob("succeeded"),
      idempotentReplay: false,
      requestContext: submittedTranscriptJob().requestContext,
    });
    await flushPromises();

    await expect(runPromise).resolves.toMatchObject({ transcriptText: "Hej." });
    expect(runtime.uploadState.value.status).toBe("idle");
    wrapper.unmount();
  });

  it("aborts an upload before a Gateway job id exists", async () => {
    const client = runtimeClient();
    let capturedSignal: AbortSignal | null = null;
    vi.mocked(client.submitTranscriptJob).mockImplementationOnce(async (params) => {
      capturedSignal = params.abortSignal ?? null;
      return await new Promise<Awaited<ReturnType<GatewayRuntimeClient["submitTranscriptJob"]>>>(
        (_resolve, reject) => {
        params.abortSignal?.addEventListener("abort", () => {
          reject(
            new SirConvertGatewayError({
              code: "SIR_CONVERT_UPLOAD_ABORTED",
              message: "Upload aborted.",
              status: 0,
            }),
          );
        });
      });
    });
    const { runtime, wrapper } = mountRuntime(client);

    const runPromise = runtime.submitAndPoll({
      file: transcriptFile(),
      speakerControl: { mode: "auto" },
    });
    await flushPromises();

    await runtime.cancelTranscript();
    await flushPromises();

    expect(requireAbortSignal(capturedSignal).aborted).toBe(true);
    expect(runtime.status.value).toBe("canceled");
    expect(runtime.abortState.value).toMatchObject({
      message: "Uppladdningen är avbruten.",
      status: "accepted",
    });
    expect(client.cancelTranscriptJob).not.toHaveBeenCalled();
    await expect(runPromise).resolves.toBeNull();
    wrapper.unmount();
  });

  it("marks abort accepted only after Gateway returns a canceled job", async () => {
    vi.useFakeTimers();
    const client = runtimeClient();
    vi.mocked(client.cancelTranscriptJob).mockResolvedValueOnce(transcriptJob("canceled"));
    const { runtime, wrapper } = mountRuntime(client);

    const runPromise = runtime.submitAndPoll({
      file: transcriptFile(),
      speakerControl: { mode: "auto" },
    });
    await flushPromises();

    await runtime.cancelTranscript();
    await flushPromises();

    expect(runtime.abortState.value.status).toBe("accepted");
    expect(runtime.status.value).toBe("canceled");
    expect(runtime.currentJob.value).toMatchObject({ status: "canceled" });

    await vi.advanceTimersByTimeAsync(1_000);
    await expect(runPromise).resolves.toBeNull();
    wrapper.unmount();
  });
});
