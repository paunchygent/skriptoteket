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
  downloadDigiExamMigrationArtifact: vi.fn(),
  getDigiExamMigrationJob: vi.fn(),
  getDigiExamMigrationResult: vi.fn(),
  listDigiExamMigrationArtifacts: vi.fn(),
  saveDigiExamMigrationArtifactToUserFiles: vi.fn(),
  submitDigiExamMigration: vi.fn(),
}));

vi.mock("../../api/sirConvertGateway", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api/sirConvertGateway")>();
  return {
    ...actual,
    downloadDigiExamMigrationArtifact: gatewayMocks.downloadDigiExamMigrationArtifact,
    getDigiExamMigrationJob: gatewayMocks.getDigiExamMigrationJob,
    getDigiExamMigrationResult: gatewayMocks.getDigiExamMigrationResult,
    listDigiExamMigrationArtifacts: gatewayMocks.listDigiExamMigrationArtifacts,
    saveDigiExamMigrationArtifactToUserFiles:
      gatewayMocks.saveDigiExamMigrationArtifactToUserFiles,
    submitDigiExamMigration: gatewayMocks.submitDigiExamMigration,
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
  mockReviewArtifacts(gatewayMocks);
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
  gatewayMocks.downloadDigiExamMigrationArtifact.mockReset();
  gatewayMocks.getDigiExamMigrationJob.mockReset();
  gatewayMocks.getDigiExamMigrationResult.mockReset();
  gatewayMocks.listDigiExamMigrationArtifacts.mockReset();
  gatewayMocks.saveDigiExamMigrationArtifactToUserFiles.mockReset();
  gatewayMocks.submitDigiExamMigration.mockReset();
  gatewayMocks.submitDigiExamMigration.mockResolvedValue(submittedJob("succeeded"));
  gatewayMocks.getDigiExamMigrationResult.mockResolvedValue(terminalResult());
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
    expect(wrapper.text()).toContain("Granska AI-facit");
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
