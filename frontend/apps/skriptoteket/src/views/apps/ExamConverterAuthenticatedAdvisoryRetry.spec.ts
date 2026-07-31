/**
 * Exam Converter authenticated advisory retry behavior.
 *
 * Slice purpose:
 *   Prove provider-only facitförslag failures can be retried explicitly without
 *   weakening normal idempotency or exposing provider machinery to teachers.
 *
 * Expected behavior:
 *   The first authenticated advisory submit remains deterministic. When the
 *   loaded completion report proves provider-only failure, the workspace shows
 *   the approved retry affordance. The explicit retry sends
 *   `advisoryRetryAttempt=1`; repeated clicks while that retry is in flight are
 *   guarded by normal runtime busy state.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ExamConverterAuthenticatedView from "./ExamConverterAuthenticatedView.vue";
import { correctionSourceState } from "./examConverterAuthenticatedCorrectionSessionFixtures";
import {
  artifactJsonBlob,
  finishConversion,
  mockReviewArtifacts,
  submittedJob,
  terminalResult,
} from "./examConverterAuthenticatedReviewFixtures";
import {
  DIGIEXAM_ARTIFACT_ANSWER_KEY_COMPLETION_REPORT,
  DIGIEXAM_ITEM_TYPE_SINGLE_CHOICE,
} from "../../api/sirConvertGateway/contractValues";
import { ANSWER_KEY_COMPLETION_REPORT_SCHEMA_VERSION } from "../../api/sirConvertGateway/schemaVersions";

const gatewayMocks = vi.hoisted(() => ({
  applyExamAuthoringCorrections: vi.fn(),
  downloadDigiExamMigrationArtifact: vi.fn(),
  getDigiExamMigrationJob: vi.fn(),
  getDigiExamMigrationResult: vi.fn(),
  issueExamAuthoringCorrectionSourceState: vi.fn(),
  listDigiExamMigrationArtifacts: vi.fn(),
  saveDigiExamMigrationArtifactToUserFiles: vi.fn(),
  submitDigiExamMigration: vi.fn(),
}));
const correctionSessionApiMocks = vi.hoisted(() => ({
  getExamConverterCorrectionSession: vi.fn(),
  registerExamConverterConversionHubJob: vi.fn(),
}));

vi.mock("../../api/sirConvertGateway", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api/sirConvertGateway")>();
  return {
    ...actual,
    applyExamAuthoringCorrections: gatewayMocks.applyExamAuthoringCorrections,
    downloadDigiExamMigrationArtifact: gatewayMocks.downloadDigiExamMigrationArtifact,
    getDigiExamMigrationJob: gatewayMocks.getDigiExamMigrationJob,
    getDigiExamMigrationResult: gatewayMocks.getDigiExamMigrationResult,
    issueExamAuthoringCorrectionSourceState: gatewayMocks.issueExamAuthoringCorrectionSourceState,
    listDigiExamMigrationArtifacts: gatewayMocks.listDigiExamMigrationArtifacts,
    saveDigiExamMigrationArtifactToUserFiles:
      gatewayMocks.saveDigiExamMigrationArtifactToUserFiles,
    submitDigiExamMigration: gatewayMocks.submitDigiExamMigration,
  };
});

vi.mock("../../api/examConverterCorrectionSessions", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api/examConverterCorrectionSessions")>();
  return {
    ...actual,
    getExamConverterCorrectionSession: correctionSessionApiMocks.getExamConverterCorrectionSession,
    registerExamConverterConversionHubJob:
      correctionSessionApiMocks.registerExamConverterConversionHubJob,
  };
});

function providerOnlyFailureReport() {
  return {
    schema_version: ANSWER_KEY_COMPLETION_REPORT_SCHEMA_VERSION,
    completion_mode: "local_llm_suggest_missing_machine_marked",
    job_id: "job_exam_converter_review",
    items: [
      {
        item_id: "item-004",
        sequence: 4,
        item_type: DIGIEXAM_ITEM_TYPE_SINGLE_CHOICE,
        decision_state: "manual_follow_up_required",
        validation_state: "manual_follow_up_required",
        backend_status: "failed",
        backend_failure_code: "provider_request_failed",
        candidate_id: null,
        candidate_payload_digest: null,
        provider_profile_id: null,
        model_profile: null,
        prompt_template_version: null,
        schema_name: null,
        schema_version: null,
        answer_payload: null,
      },
    ],
  };
}

function mockProviderOnlyAdvisoryFailureArtifacts(): void {
  mockReviewArtifacts(gatewayMocks, { choiceCandidateAvailable: false });
  const baseDownload = gatewayMocks.downloadDigiExamMigrationArtifact.getMockImplementation();
  gatewayMocks.downloadDigiExamMigrationArtifact.mockImplementation(
    (params: { artifactKey: string }) => {
      if (params.artifactKey === DIGIEXAM_ARTIFACT_ANSWER_KEY_COMPLETION_REPORT) {
        return Promise.resolve(
          artifactJsonBlob(
            DIGIEXAM_ARTIFACT_ANSWER_KEY_COMPLETION_REPORT,
            providerOnlyFailureReport(),
          ),
        );
      }
      return baseDownload?.(params);
    },
  );
}

beforeEach(() => {
  gatewayMocks.applyExamAuthoringCorrections.mockReset();
  gatewayMocks.downloadDigiExamMigrationArtifact.mockReset();
  gatewayMocks.getDigiExamMigrationJob.mockReset();
  gatewayMocks.getDigiExamMigrationResult.mockReset();
  gatewayMocks.issueExamAuthoringCorrectionSourceState.mockReset();
  gatewayMocks.listDigiExamMigrationArtifacts.mockReset();
  gatewayMocks.saveDigiExamMigrationArtifactToUserFiles.mockReset();
  gatewayMocks.submitDigiExamMigration.mockReset();
  correctionSessionApiMocks.getExamConverterCorrectionSession.mockReset();
  correctionSessionApiMocks.registerExamConverterConversionHubJob.mockReset();
  gatewayMocks.submitDigiExamMigration.mockResolvedValue(submittedJob("succeeded"));
  gatewayMocks.getDigiExamMigrationResult.mockResolvedValue(terminalResult());
  correctionSessionApiMocks.registerExamConverterConversionHubJob.mockResolvedValue({
    job_id: "local-conversion-hub-job-1",
    status: "succeeded",
    upstream_job_id: "job_exam_converter_review",
  });
  correctionSessionApiMocks.getExamConverterCorrectionSession.mockResolvedValue({
    active_intents: [],
    conversion_hub_job_id: "local-conversion-hub-job-1",
    owner_user_id: "11111111-1111-4111-8111-111111111111",
    session_id: null,
    session_version: 0,
    source_binding: null,
  });
  gatewayMocks.issueExamAuthoringCorrectionSourceState.mockResolvedValue(correctionSourceState());
  mockProviderOnlyAdvisoryFailureArtifacts();
});

describe("ExamConverterAuthenticatedView advisory retry", () => {
  it("offers the approved retry affordance and retries with attempt one", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);

    const retryPanel = wrapper.find('[data-test="exam-converter-advisory-retry-panel"]');
    const retryButton = wrapper.find('[data-test="exam-converter-advisory-retry-action"]');
    expect(retryPanel.text()).toContain("Det gick inte att ta fram ett facitförslag.");
    expect(retryButton.text()).toBe("Försök igen");
    expect(retryButton.html()).toContain("lucide-refresh-cw");
    expect(retryPanel.text()).not.toContain("AI");
    expect(retryPanel.text()).not.toContain("provider");
    expect(gatewayMocks.submitDigiExamMigration.mock.calls[0]?.[0]).not.toHaveProperty(
      "advisoryRetryAttempt",
    );

    mockReviewArtifacts(gatewayMocks);
    await retryButton.trigger("click");
    await flushPromises();

    expect(gatewayMocks.submitDigiExamMigration.mock.calls[1]?.[0]).toMatchObject({
      advisoryRetryAttempt: 1,
      completionMode: "local_llm_suggest_missing_machine_marked",
    });
    expect(wrapper.find('[data-test="exam-converter-advisory-retry-panel"]').exists()).toBe(
      false,
    );
    expect(wrapper.text()).toContain("Kontrollera facit");
  });

  it("increments only after a completed retry returns the same failure class", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    await wrapper.find('[data-test="exam-converter-advisory-retry-action"]').trigger("click");
    await flushPromises();
    await wrapper.find('[data-test="exam-converter-advisory-retry-action"]').trigger("click");
    await flushPromises();

    expect(gatewayMocks.submitDigiExamMigration.mock.calls[1]?.[0]).toMatchObject({
      advisoryRetryAttempt: 1,
    });
    expect(gatewayMocks.submitDigiExamMigration.mock.calls[2]?.[0]).toMatchObject({
      advisoryRetryAttempt: 2,
    });
  });
});
