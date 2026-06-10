/**
 * Conversion Hub transcript mode behavior.
 *
 * Domain purpose:
 *   Prove the authenticated Conversion Hub renders a bespoke transcript lane
 *   with speaker controls and Gateway-backed lifecycle actions.
 *
 * Relationships:
 *   - Mounts `ExamConverterAuthenticatedView` as the existing Conversion Hub
 *     authenticated host.
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

async function chooseTranscriptFile(wrapper: ReturnType<typeof mount>, file: File) {
  const input = wrapper.find<HTMLInputElement>('[data-test="transcript-source-file-input"]');
  Object.defineProperty(input.element, "files", {
    configurable: true,
    value: [file],
  });
  await input.trigger("change");
}

describe("Conversion Hub transcript mode", () => {
  beforeEach(() => {
    for (const mock of Object.values(gatewayMocks)) {
      mock.mockReset();
    }
    gatewayMocks.submitTranscriptJob.mockResolvedValue({
      audioProgress: {
        currentChunkIndex: null,
        percentComplete: null,
        processedMediaSeconds: null,
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
      stage: null,
      status: "succeeded",
    });
    gatewayMocks.getTranscriptResult.mockResolvedValue({
      conversion_metadata: {
        artifact_count: 1,
        bundle_schema_version: "transcript_bundle_v1",
        bundle_status: "complete",
        route_key: "audio_to_transcript_bundle",
        source_sha256: "sha256:source",
        transcript_json_artifact_key: "transcript_json",
        warning_count: 0,
      },
      artifact: {
        content_type: "application/json",
        filename: "transcript-bundle.json",
        sha256: "sha256:bundle",
        size_bytes: 512,
      },
      job: {
        audioProgress: {
          currentChunkIndex: null,
          percentComplete: null,
          processedMediaSeconds: null,
          totalChunks: null,
          totalMediaSeconds: null,
        },
        jobId: "job_transcript_1",
        stage: "succeeded",
        status: "succeeded",
      },
    });
    gatewayMocks.listTranscriptArtifacts.mockResolvedValue({
      artifacts: [
        {
          artifact_key: "transcript_json",
          availability: "available",
          content_type: "application/json",
          filename: "lektion.transcript.json",
          sha256: "sha256:json",
          size_bytes: 512,
        },
      ],
      bundle_status: "complete",
      job_id: "job_transcript_1",
      schema_version: "transcript_bundle_v1",
      source: { filename: "lektion.m4a", format: "audio", sha256: "sha256:source" },
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
    const wrapper = mount(ExamConverterAuthenticatedView);

    await wrapper.find('[data-test="conversion-hub-mode-transcript"]').trigger("click");
    await chooseTranscriptFile(
      wrapper,
      new File(["audio"], "lektion.m4a", { type: "audio/mp4" }),
    );
    await wrapper.find('[data-test="transcript-speaker-mode-known"]').trigger("click");
    await wrapper.find<HTMLInputElement>('[data-test="transcript-speaker-count"]').setValue("2");
    await wrapper.find('[data-test="transcript-start"]').trigger("click");
    await flushPromises();
    await wrapper.vm.$nextTick();

    expect(gatewayMocks.submitTranscriptJob).toHaveBeenCalledWith({
      file: expect.any(File),
      speakerControl: { mode: "known_speaker_count", speakerCount: 2 },
      waitSeconds: 0,
    });
    expect(wrapper.text()).toContain("Transkriptet är klart");
    expect(wrapper.text()).toContain("SPEAKER_00");
    expect(wrapper.text()).not.toContain("Sir Convert");
    expect(wrapper.text()).not.toContain("sidecar");
    expect(wrapper.text()).not.toContain("modell");
  });
});
