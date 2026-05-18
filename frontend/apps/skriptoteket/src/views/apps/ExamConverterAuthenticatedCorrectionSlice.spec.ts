/**
 * Exam Converter teacher correction behavior.
 *
 * Slice purpose:
 *   Prove PR-0332 teacher-owned corrections submit source-bound overlays and
 *   wait for returned Sir Convert effective state before files unlock.
 *
 * Expected behavior:
 *   Local point or answer-key drafts do not mutate question state, do not
 *   create answer-key evidence, and do not enable file actions until the
 *   corrected migration bundle is returned and projected.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
} from "../../api/sirConvertGateway/schemaVersions";
import ExamConverterAuthenticatedView from "./ExamConverterAuthenticatedView.vue";
import {
  finishConversion,
  mockReviewArtifacts,
  submittedJob,
  terminalResult,
} from "./examConverterAuthenticatedReviewFixtures";
import {
  MANUAL_GAP_FILL_APPLY_JOB_ID,
  mockManualGapFillCorrectionArtifacts,
} from "./examConverterAuthenticatedGapFillReviewFixtures";

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

beforeEach(() => {
  gatewayMocks.downloadDigiExamMigrationArtifact.mockReset();
  gatewayMocks.getDigiExamMigrationJob.mockReset();
  gatewayMocks.getDigiExamMigrationResult.mockReset();
  gatewayMocks.listDigiExamMigrationArtifacts.mockReset();
  gatewayMocks.saveDigiExamMigrationArtifactToUserFiles.mockReset();
  gatewayMocks.submitDigiExamMigration.mockReset();
  gatewayMocks.submitDigiExamMigration.mockResolvedValue(submittedJob("succeeded"));
  gatewayMocks.getDigiExamMigrationResult.mockResolvedValue(terminalResult());
  mockReviewArtifacts(gatewayMocks);
});

describe("ExamConverterAuthenticatedView teacher corrections", () => {
  it("submits point corrections as source-bound overlays and waits for returned state", async () => {
    let pointCorrectionApplied = false;
    gatewayMocks.submitDigiExamMigration.mockImplementation((params) => {
      pointCorrectionApplied = Boolean(params.ingestionOverlay?.items[0]?.point_correction);
      mockReviewArtifacts(gatewayMocks, { pointCorrectionApplied });
      return Promise.resolve(
        submittedJob(
          "succeeded",
          pointCorrectionApplied ? "job_exam_converter_point_correction" : undefined,
        ),
      );
    });
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    await wrapper.find('[data-test="exam-converter-question-row-item-012"]').trigger("click");
    await wrapper
      .find<HTMLInputElement>('[data-test="exam-converter-point-correction-input"]')
      .setValue("3");
    expect(gatewayMocks.submitDigiExamMigration).toHaveBeenCalledTimes(1);
    await wrapper.find('[data-test="exam-converter-inspection-tab-files"]').trigger("click");
    expect(
      wrapper.find('[data-test="exam-converter-download-file-examnet_pdf"]').attributes(
        "disabled",
      ),
    ).toBeDefined();

    await wrapper.find('[data-test="exam-converter-inspection-tab-questions"]').trigger("click");
    await wrapper.find('[data-test="exam-converter-question-row-item-012"]').trigger("click");
    await wrapper
      .find<HTMLInputElement>('[data-test="exam-converter-point-correction-input"]')
      .setValue("3");
    await wrapper.find('[data-test="exam-converter-apply-point-correction-action"]').trigger("click");
    await flushPromises();

    const pointCorrectionSubmit = gatewayMocks.submitDigiExamMigration.mock.calls[1]?.[0];
    expect(pointCorrectionSubmit).toMatchObject({
      completionMode: "source_evidence_only",
      ingestionOverlay: {
        source_binding: {
          source_file_sha256: "sha256:source",
          source_ir_schema_version: DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
          source_ir_sha256: "sha256:ir",
        },
        items: [
          {
            item_id: "item-012",
            manual_answer_key: null,
            point_correction: { kind: "item_points", max_score: 3 },
            source_item_fingerprint: "sha256:item-012",
          },
        ],
      },
    });
    expect(gatewayMocks.listDigiExamMigrationArtifacts).toHaveBeenLastCalledWith({
      completionReportRequired: false,
      correlationId: "corr_exam_converter_review",
      jobId: "job_exam_converter_point_correction",
    });
    expect(wrapper.find('[data-test="exam-converter-question-row-item-012"]').text()).toContain(
      "3 p",
    );
  });

  it("submits manual choice answer keys before files unlock", async () => {
    mockReviewArtifacts(gatewayMocks, { choiceCandidateAvailable: false });
    let manualAnswerKeyApplied = false;
    gatewayMocks.submitDigiExamMigration.mockImplementation((params) => {
      manualAnswerKeyApplied = Boolean(params.ingestionOverlay?.items[0]?.manual_answer_key);
      mockReviewArtifacts(gatewayMocks, {
        choiceCandidateAvailable: false,
        manualAnswerKeyApplied,
      });
      return Promise.resolve(
        submittedJob(
          "succeeded",
          manualAnswerKeyApplied ? "job_exam_converter_manual_answer_key" : undefined,
        ),
      );
    });
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    await wrapper.find('[data-test="exam-converter-question-row-item-004"]').trigger("click");
    await wrapper.find('[data-test="exam-converter-manual-choice-2"]').trigger("click");
    expect(gatewayMocks.submitDigiExamMigration).toHaveBeenCalledTimes(1);
    await wrapper.find('[data-test="exam-converter-inspection-tab-files"]').trigger("click");
    expect(
      wrapper.find('[data-test="exam-converter-download-file-examnet_pdf"]').attributes(
        "disabled",
      ),
    ).toBeDefined();

    await wrapper.find('[data-test="exam-converter-inspection-tab-questions"]').trigger("click");
    await wrapper.find('[data-test="exam-converter-question-row-item-004"]').trigger("click");
    await wrapper.find('[data-test="exam-converter-manual-choice-2"]').trigger("click");
    await wrapper
      .find('[data-test="exam-converter-apply-manual-answer-key-action"]')
      .trigger("click");
    await flushPromises();

    const manualAnswerKeySubmit = gatewayMocks.submitDigiExamMigration.mock.calls[1]?.[0];
    expect(manualAnswerKeySubmit).toMatchObject({
      completionMode: "source_evidence_only",
      ingestionOverlay: {
        source_binding: {
          source_file_sha256: "sha256:source",
          source_ir_schema_version: DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
          source_ir_sha256: "sha256:ir",
        },
        items: [
          {
            item_id: "item-004",
            item_type: "single_choice",
            manual_answer_key: {
              correct_alternative_ids: [2],
              kind: "choice",
            },
            source_item_fingerprint: "sha256:item-004",
          },
        ],
      },
    });
    expect(gatewayMocks.listDigiExamMigrationArtifacts).toHaveBeenLastCalledWith({
      completionReportRequired: false,
      correlationId: "corr_exam_converter_review",
      jobId: "job_exam_converter_manual_answer_key",
    });

    const correctedRow = wrapper.find('[data-test="exam-converter-question-row-item-004"]');
    expect(correctedRow.text()).not.toContain("Facit");
    await correctedRow.trigger("click");
    expect(wrapper.find('[data-test="exam-converter-selected-question-detail"]').text()).toContain(
      "Ändrat",
    );
    await wrapper.find('[data-test="exam-converter-inspection-tab-files"]').trigger("click");
    expect(
      wrapper.find('[data-test="exam-converter-download-file-examnet_pdf"]').attributes(
        "disabled",
      ),
    ).toBeUndefined();
  });

  it("submits manual gap-fill accepted values before files unlock", async () => {
    mockManualGapFillCorrectionArtifacts(gatewayMocks);
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    await wrapper.find('[data-test="exam-converter-question-row-item-013"]').trigger("click");
    await wrapper
      .find<HTMLInputElement>('[data-test="exam-converter-manual-gap-gap-001"]')
      .setValue("kretslopp, kretslopp");
    await wrapper
      .find<HTMLInputElement>('[data-test="exam-converter-manual-gap-gap-002"]')
      .setValue("näringsväv");
    expect(gatewayMocks.submitDigiExamMigration).toHaveBeenCalledTimes(1);
    await wrapper.find('[data-test="exam-converter-inspection-tab-files"]').trigger("click");
    expect(
      wrapper.find('[data-test="exam-converter-download-file-examnet_pdf"]').attributes(
        "disabled",
      ),
    ).toBeDefined();

    await wrapper.find('[data-test="exam-converter-inspection-tab-questions"]').trigger("click");
    await wrapper.find('[data-test="exam-converter-question-row-item-013"]').trigger("click");
    await wrapper
      .find<HTMLInputElement>('[data-test="exam-converter-manual-gap-gap-001"]')
      .setValue("kretslopp, kretslopp");
    await wrapper
      .find<HTMLInputElement>('[data-test="exam-converter-manual-gap-gap-002"]')
      .setValue("näringsväv");
    await wrapper
      .find('[data-test="exam-converter-apply-manual-answer-key-action"]')
      .trigger("click");
    await flushPromises();

    const manualGapSubmit = gatewayMocks.submitDigiExamMigration.mock.calls[1]?.[0];
    expect(manualGapSubmit).toMatchObject({
      completionMode: "source_evidence_only",
      ingestionOverlay: {
        source_binding: {
          source_file_sha256: "sha256:source",
          source_ir_schema_version: DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
          source_ir_sha256: "sha256:ir",
        },
        items: [
          {
            item_id: "item-013",
            item_type: "gap_fill",
            manual_answer_key: {
              gap_answers: [
                { accepted_values: ["kretslopp"], gap_id: "gap-001" },
                { accepted_values: ["näringsväv"], gap_id: "gap-002" },
              ],
              kind: "gap_fill",
            },
            source_item_fingerprint: "sha256:item-013",
          },
        ],
      },
    });
    expect(gatewayMocks.listDigiExamMigrationArtifacts).toHaveBeenLastCalledWith({
      completionReportRequired: false,
      correlationId: "corr_exam_converter_review",
      jobId: MANUAL_GAP_FILL_APPLY_JOB_ID,
    });

    const correctedRow = wrapper.find('[data-test="exam-converter-question-row-item-013"]');
    expect(correctedRow.text()).not.toContain("Facit");
    await correctedRow.trigger("click");
    const detail = wrapper.find('[data-test="exam-converter-selected-question-detail"]');
    expect(detail.text()).toContain("gap-001: kretslopp");
    expect(detail.text()).toContain("gap-002: näringsväv");
    expect(detail.text()).toContain("Ändrat");
    await wrapper.find('[data-test="exam-converter-inspection-tab-files"]').trigger("click");
    expect(
      wrapper.find('[data-test="exam-converter-download-file-examnet_pdf"]').attributes(
        "disabled",
      ),
    ).toBeUndefined();
  });
});
