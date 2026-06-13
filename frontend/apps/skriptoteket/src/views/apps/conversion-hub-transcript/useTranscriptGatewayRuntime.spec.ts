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
};

type GatewayRuntimeClient = NonNullable<TranscriptGatewayRuntimeOptions["client"]>;

function transcriptFile(): File {
  return new File(["lesson audio"], "lektion.m4a", { type: "audio/mp4" });
}

function transcriptJob(status: "running" | "succeeded" | "canceled") {
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
  } as Awaited<ReturnType<GatewayRuntimeClient["getTranscriptJob"]>>;
}

function submittedTranscriptJob() {
  return {
    ...transcriptJob("running"),
    idempotentReplay: false,
    requestContext: {
      correlationId: "corr_transcript_1",
      idempotencyKey: "idem_transcript_1",
      jobSpec: {} as never,
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

  it("does not report pre-id abort as accepted until Gateway cancel succeeds", async () => {
    const client = runtimeClient();
    const submitted = deferred<Awaited<ReturnType<GatewayRuntimeClient["submitTranscriptJob"]>>>();
    vi.mocked(client.submitTranscriptJob).mockReturnValueOnce(submitted.promise);
    vi.mocked(client.cancelTranscriptJob).mockResolvedValueOnce(transcriptJob("canceled"));
    const { runtime, wrapper } = mountRuntime(client);

    const runPromise = runtime.submitAndPoll({
      file: transcriptFile(),
      speakerControl: { mode: "auto" },
    });
    await flushPromises();

    const cancelPromise = runtime.cancelTranscript();
    await flushPromises();

    expect(runtime.status.value).toBe("running");
    expect(runtime.abortState.value.status).toBe("pending");
    expect(client.cancelTranscriptJob).not.toHaveBeenCalled();
    expect(client.getTranscriptJob).not.toHaveBeenCalled();

    submitted.resolve(submittedTranscriptJob());
    await cancelPromise;
    await flushPromises();

    expect(client.cancelTranscriptJob).toHaveBeenCalledWith({
      correlationId: "corr_transcript_1",
      jobId: "job_transcript_1",
    });
    expect(client.getTranscriptJob).not.toHaveBeenCalled();
    expect(runtime.abortState.value.status).toBe("accepted");
    expect(runtime.status.value).toBe("canceled");
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
