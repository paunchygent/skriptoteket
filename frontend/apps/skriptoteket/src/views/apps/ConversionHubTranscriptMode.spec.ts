/**
 * Audio Transcription authenticated identity behavior.
 *
 * Domain purpose:
 *   Prove the canonical protected Audio Transcription identity renders a
 *   bespoke transcript lane with speaker controls and Gateway-backed lifecycle
 *   actions.
 *
 * Relationships:
 *   - Mounts `ExamConverterAuthenticatedView` with transcript presentation
 *     identity while reusing the shared authenticated runtime host.
 *   - Uses mocked Sir Convert Gateway methods only at the product edge.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ExamConverterAuthenticatedView from "./ExamConverterAuthenticatedView.vue";

const gatewayMocks = vi.hoisted(() => ({
  applyExamAuthoringCorrections: vi.fn(),
  cancelTranscriptJob: vi.fn(),
  downloadDigiExamMigrationArtifact: vi.fn(),
  downloadTranscriptJson: vi.fn(),
  getDigiExamMigrationJob: vi.fn(),
  getDigiExamMigrationResult: vi.fn(),
  getTranscriptJob: vi.fn(),
  getTranscriptResult: vi.fn(),
  issueExamAuthoringCorrectionSourceState: vi.fn(),
  listDigiExamMigrationArtifacts: vi.fn(),
  listTranscriptArtifacts: vi.fn(),
  saveDigiExamMigrationArtifactToUserFiles: vi.fn(),
  submitDigiExamMigration: vi.fn(),
  submitTranscriptJob: vi.fn(),
}));

vi.mock("../../api/sirConvertGateway", () => ({
  SIR_CONVERT_ARTIFACT_AVAILABLE: "available",
  applyExamAuthoringCorrections: gatewayMocks.applyExamAuthoringCorrections,
  cancelTranscriptJob: gatewayMocks.cancelTranscriptJob,
  downloadDigiExamMigrationArtifact: gatewayMocks.downloadDigiExamMigrationArtifact,
  downloadTranscriptJson: gatewayMocks.downloadTranscriptJson,
  getDigiExamMigrationJob: gatewayMocks.getDigiExamMigrationJob,
  getDigiExamMigrationResult: gatewayMocks.getDigiExamMigrationResult,
  getTranscriptJob: gatewayMocks.getTranscriptJob,
  getTranscriptResult: gatewayMocks.getTranscriptResult,
  issueExamAuthoringCorrectionSourceState: gatewayMocks.issueExamAuthoringCorrectionSourceState,
  listDigiExamMigrationArtifacts: gatewayMocks.listDigiExamMigrationArtifacts,
  listTranscriptArtifacts: gatewayMocks.listTranscriptArtifacts,
  saveDigiExamMigrationArtifactToUserFiles:
    gatewayMocks.saveDigiExamMigrationArtifactToUserFiles,
  submitDigiExamMigration: gatewayMocks.submitDigiExamMigration,
  submitTranscriptJob: gatewayMocks.submitTranscriptJob,
}));

vi.mock("vue-router", () => ({
  useRoute: () => ({ query: {} }),
}));

async function chooseTranscriptFile(wrapper: ReturnType<typeof mount>, file: File) {
  const input = wrapper.find<HTMLInputElement>('[data-test="transcript-source-file-input"]');
  Object.defineProperty(input.element, "files", {
    configurable: true,
    value: [file],
  });
  await input.trigger("change");
}

describe("Audio Transcription authenticated presentation", () => {
  beforeEach(() => {
    for (const mock of Object.values(gatewayMocks)) {
      mock.mockReset();
    }
    gatewayMocks.submitTranscriptJob.mockResolvedValue({
      progress: {
        currentChunkIndex: null,
        currentPhaseStartedAt: null,
        lastHeartbeatAt: null,
        percentComplete: null,
        phase: null,
        phaseTimingsMs: {},
        processedMediaSeconds: null,
        status: "succeeded",
        totalChunks: null,
        totalMediaSeconds: null,
      },
      idempotentReplay: false,
      jobId: "job_transcript_1",
      requestContext: {
        correlationId: "corr_transcript_1",
        idempotencyKey: "idem_transcript_1",
        jobSpec: {},
      },
      status: "succeeded",
    });
    gatewayMocks.getTranscriptResult.mockResolvedValue({
      conversion_metadata: {
        acceleration_used: "rocm",
        backend_used: "stt_sidecar",
        options_fingerprint: "audio-options-fingerprint",
        pipeline_used: "audio_to_transcript_bundle_v2",
      },
      artifact: {
        content_type: "application/json",
        filename: "transcript-bundle.json",
        sha256: "sha256:bundle",
        size_bytes: 512,
      },
      job: {
        progress: {
          currentChunkIndex: null,
          currentPhaseStartedAt: null,
          lastHeartbeatAt: null,
          percentComplete: null,
          phase: "succeeded",
          phaseTimingsMs: {},
          processedMediaSeconds: null,
          status: "succeeded",
          totalChunks: null,
          totalMediaSeconds: null,
        },
        jobId: "job_transcript_1",
        status: "succeeded",
      },
    });
    gatewayMocks.listTranscriptArtifacts.mockResolvedValue({
      api_version: "v2",
      artifacts: [
        {
          artifact_key: "transcript_json",
          availability: "available",
          content_type: "application/json",
          filename: "lektion.transcript.json",
          sha256: "sha256:json",
          size_bytes: 512,
        },
        {
          artifact_key: "transcript_txt",
          availability: "unrequested",
          unavailable_code: "audio_transcript_artifact_unavailable",
        },
        {
          artifact_key: "transcript_md",
          availability: "unrequested",
          unavailable_code: "audio_transcript_artifact_unavailable",
        },
        {
          artifact_key: "transcript_vtt",
          availability: "unrequested",
          unavailable_code: "audio_transcript_artifact_unavailable",
        },
        {
          artifact_key: "transcript_srt",
          availability: "unrequested",
          unavailable_code: "audio_transcript_artifact_unavailable",
        },
      ],
      job_id: "job_transcript_1",
      output_format: "transcript_bundle",
      formatterArtifacts: {
        transcript_txt: {
          artifact_key: "transcript_txt",
          availability: "unrequested",
          unavailable_code: "audio_transcript_artifact_unavailable",
        },
      },
      transcriptJsonArtifact: {
        artifact_key: "transcript_json",
        availability: "available",
        content_type: "application/json",
        filename: "lektion.transcript.json",
        sha256: "sha256:json",
        size_bytes: 512,
      },
    });
    gatewayMocks.downloadTranscriptJson.mockResolvedValue({
      schemaVersion: "transcript_json_v1",
      segments: [
        {
          endSeconds: 2,
          id: "seg_1",
          speakerLabel: "SPEAKER_00",
          startSeconds: 0,
          text: "Hej från seminariet.",
        },
      ],
      transcriptText: "Hej från seminariet.",
    });
  });

  it("submits selected audio with exact speaker controls through the transcript Gateway lane", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView, {
      props: { presentationMode: "transcript" },
    });

    expect(wrapper.find('[data-test="conversion-hub-mode-exam"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="conversion-hub-mode-transcript"]').exists()).toBe(false);
    await chooseTranscriptFile(
      wrapper,
      new File(["audio"], "lektion.m4a", { type: "audio/mp4" }),
    );
    await wrapper.find('[data-test="transcript-speaker-mode-known"]').trigger("click");
    await wrapper.find<HTMLInputElement>('[data-test="transcript-speaker-count"]').setValue("2");
    await wrapper.find('[data-test="transcript-start"]').trigger("click");
    await flushPromises();
    await wrapper.vm.$nextTick();

    expect(gatewayMocks.submitTranscriptJob).toHaveBeenCalledWith(
      expect.objectContaining({
        abortSignal: expect.any(AbortSignal),
        file: expect.any(File),
        onUploadProgress: expect.any(Function),
        speakerControl: { mode: "known_speaker_count", speakerCount: 2 },
        waitSeconds: 0,
      }),
    );
    expect(wrapper.text()).toContain("Transkriptet är klart");
    expect(wrapper.text()).toContain("SPEAKER_00");
    expect(wrapper.text()).not.toContain("Sir Convert");
    expect(wrapper.text()).not.toContain("sidecar");
    expect(wrapper.text()).not.toContain("modell");
  });
});
