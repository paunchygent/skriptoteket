/**
 * Exam Converter IR-backed review shell behavior.
 *
 * Domain purpose: prove authenticated review projection for question, file,
 * and report artifacts.
 *
 * Relationships: complements the correction-specific PR-0332 spec.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ExamConverterAuthenticatedView from "./ExamConverterAuthenticatedView.vue";
import { mockFreeTextOnlyReviewArtifacts } from "./examConverterAuthenticatedFreeTextFixtures";
import {
  artifactJsonBlob,
  finishConversion,
  mockReviewArtifacts,
  submittedJob,
  terminalResult,
} from "./examConverterAuthenticatedReviewFixtures";
import { mockVisionBackedGapFillReviewArtifacts, REVIEWED_GAP_FILL_APPLY_JOB_ID } from "./examConverterAuthenticatedGapFillReviewFixtures";
import {
  DIGIEXAM_ARTIFACT_TARGET_READINESS_REPORT,
  DIGIEXAM_TARGET_EXAMNET_PDF,
  DIGIEXAM_TARGET_NEEDS_TEACHER_REVIEW_DECISION,
  DIGIEXAM_TARGET_QTI_PACKAGE,
  DIGIEXAM_TARGET_READY,
  SIR_CONVERT_BUNDLE_STATUS_COMPLETE,
} from "../../api/sirConvertGateway/contractValues";
import {
  TARGET_READINESS_REPORT_SCHEMA_VERSION,
} from "../../api/sirConvertGateway/schemaVersions";

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

describe("ExamConverterAuthenticatedView IR-backed review shell", () => {
  it("loads read-only IR artifacts and opens the questions mode when data is missing", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);

    expect(gatewayMocks.listDigiExamMigrationArtifacts).toHaveBeenCalledWith({
      completionReportRequired: true,
      correlationId: "corr_exam_converter_review",
      jobId: "job_exam_converter_review",
    });
    expect(gatewayMocks.downloadDigiExamMigrationArtifact).toHaveBeenCalledWith({
      artifactKey: "ir_json",
      correlationId: "corr_exam_converter_review",
      jobId: "job_exam_converter_review",
    });
    expect(gatewayMocks.downloadDigiExamMigrationArtifact).toHaveBeenCalledWith({
      artifactKey: "answer_key_completion_report",
      correlationId: "corr_exam_converter_review",
      jobId: "job_exam_converter_review",
    });
    expect(wrapper.text()).toContain("Granska AI-facit");
    expect(wrapper.text()).toContain("Frågor (6)");
    expect(wrapper.text()).toContain("Filer (2)");
    expect(wrapper.find('[data-test="exam-converter-question-review-shell"]').exists()).toBe(true);
  });

  it("uses sparse missing-field labels and icon-only row status in the dense question list", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    const questions = wrapper.find('[data-test="exam-converter-question-review-shell"]');

    expect(questions.text()).toContain("Saknas");
    expect(questions.text()).toContain("Facit");
    expect(questions.text()).toContain("Poäng");
    expect(questions.text()).not.toContain("Facit saknas");
    expect(questions.text()).not.toContain("Poäng saknas");
    expect(questions.text()).not.toContain("FOSID");
    expect(questions.text()).not.toContain("Svarsalternativ");
    expect(questions.text()).not.toContain("Komplettering");
    expect(questions.text()).not.toContain("Behöver ses över");
    expect(questions.findAll(".lucide-circle-check").length).toBeGreaterThan(0);
    expect(questions.findAll(".lucide-bot").length).toBeGreaterThan(0);
    expect(questions.find('[data-test="exam-converter-question-row-item-004"]').text()).not.toContain(
      "Giltigt",
    );
  });

  it("shows question number and prompt preview in one column and treats marked free text as normal", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    const questions = wrapper.find('[data-test="exam-converter-question-review-shell"]');
    const keyedRow = wrapper.find('[data-test="exam-converter-question-row-item-004"]');
    const manualMarkedFreeTextRow = wrapper.find(
      '[data-test="exam-converter-question-row-item-013"]',
    );

    expect(questions.text()).not.toContain("Nr");
    expect(keyedRow.text()).toContain(
      "4. Vilket av följande påståenden beskriver cellandning bäst?",
    );
    expect(manualMarkedFreeTextRow.text()).toContain(
      "13. Förklara varför stål är hårdare än järn.",
    );
    expect(manualMarkedFreeTextRow.text()).toContain("Fritext");
    expect(manualMarkedFreeTextRow.text()).toContain("—");
    expect(manualMarkedFreeTextRow.text()).toContain("1 p");
    expect(manualMarkedFreeTextRow.text()).not.toContain("Facit");
    expect(manualMarkedFreeTextRow.text()).not.toContain("Poäng");
    expect(manualMarkedFreeTextRow.find(".lucide-circle-check").exists()).toBe(true);
    expect(manualMarkedFreeTextRow.find(".lucide-triangle-alert").exists()).toBe(false);
  });

  it("uses the approved Swedish item labels and no Enval shortcut", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);

    expect(wrapper.find('[data-test="exam-converter-question-row-item-001"]').text()).toContain(
      "Lucktext",
    );
    expect(wrapper.find('[data-test="exam-converter-question-row-item-004"]').text()).toContain(
      "Flerval",
    );
    expect(wrapper.find('[data-test="exam-converter-question-row-item-005"]').text()).toContain(
      "Flerval",
    );
    expect(wrapper.find('[data-test="exam-converter-question-row-item-006"]').text()).toContain(
      "Fritext",
    );
    expect(wrapper.text()).not.toContain("Enval");
    expect(wrapper.text()).not.toContain("Flerval: matchning");
  });

  it("does not present free-text manual marking as missing facit or poäng", async () => {
    mockFreeTextOnlyReviewArtifacts(gatewayMocks);
    const freeTextOnlyResult = terminalResult();
    gatewayMocks.getDigiExamMigrationResult.mockResolvedValue({
      ...freeTextOnlyResult,
      conversion_metadata: {
        ...freeTextOnlyResult.conversion_metadata,
        warning_count: 0,
      },
    });
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);

    expect(wrapper.text()).toContain("Provet är konverterat");
    expect(wrapper.text()).not.toContain("Konverteringen av provet lyckades delvis");
    expect(wrapper.text()).not.toContain("saknar facit eller poäng");

    await wrapper.find('[data-test="exam-converter-inspection-tab-questions"]').trigger("click");
    const freeTextRow = wrapper.find('[data-test="exam-converter-question-row-item-001"]');
    expect(freeTextRow.text()).toContain(
      "1. Varför är stål hårdare och starkare än järn?",
    );
    expect(freeTextRow.text()).toContain("Fritext");
    expect(freeTextRow.text()).toContain("—");
    expect(freeTextRow.text()).toContain("1 p");
    expect(freeTextRow.find(".lucide-circle-check").exists()).toBe(true);
    expect(freeTextRow.find(".lucide-triangle-alert").exists()).toBe(false);
  });

  it("keeps the success banner when all question rows and target files are ready despite warnings", async () => {
    mockFreeTextOnlyReviewArtifacts(gatewayMocks);
    const resultWithNonBlockingWarning = terminalResult();
    gatewayMocks.getDigiExamMigrationResult.mockResolvedValue({
      ...resultWithNonBlockingWarning,
      conversion_metadata: {
        ...resultWithNonBlockingWarning.conversion_metadata,
        bundle_status: SIR_CONVERT_BUNDLE_STATUS_COMPLETE,
        manual_follow_up_required: false,
        warning_count: 1,
      },
    });
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);

    expect(wrapper.text()).toContain("Provet är konverterat");
    expect(wrapper.text()).not.toContain("Konverteringen av provet lyckades delvis");
    expect(wrapper.findAll(".lucide-circle-check").length).toBeGreaterThan(0);
  });

  it("offers explicit export copy when QTI needs a target-level export decision even with green question rows", async () => {
    mockFreeTextOnlyReviewArtifacts(gatewayMocks);
    const baseDownload = gatewayMocks.downloadDigiExamMigrationArtifact.getMockImplementation();
    gatewayMocks.downloadDigiExamMigrationArtifact.mockImplementation(
      (params: { artifactKey: string }) => {
        if (params.artifactKey === DIGIEXAM_ARTIFACT_TARGET_READINESS_REPORT) {
          return Promise.resolve(
            artifactJsonBlob(DIGIEXAM_ARTIFACT_TARGET_READINESS_REPORT, {
              schema_version: TARGET_READINESS_REPORT_SCHEMA_VERSION,
              job_id: "job_exam_converter_review",
              source_ir_sha256: "sha256:ir",
              effective_exam_sha256: "sha256:effective",
              targets: [
                {
                  target: DIGIEXAM_TARGET_EXAMNET_PDF,
                  readiness: DIGIEXAM_TARGET_READY,
                  export_enabled: true,
                  artifact_key: DIGIEXAM_TARGET_EXAMNET_PDF,
                  reason_code: "target_available",
                  teacher_action: "none",
                  retryable: false,
                  message_key: "exam_converter.target.ready",
                  item_id: null,
                  sequence: null,
                  source_item_fingerprint: null,
                },
                {
                  target: DIGIEXAM_TARGET_QTI_PACKAGE,
                  readiness: DIGIEXAM_TARGET_NEEDS_TEACHER_REVIEW_DECISION,
                  export_enabled: false,
                  artifact_key: null,
                  reason_code: "manual_marking_required",
                  teacher_action: "accept_current_state_for_export",
                  retryable: false,
                  message_key: "exam_converter.target.needs_teacher_review_decision",
                  item_id: "item-001",
                  sequence: 1,
                  source_item_fingerprint: "sha256:item-001",
                },
              ],
            }),
          );
        }
        return baseDownload?.(params);
      },
    );
    gatewayMocks.getDigiExamMigrationResult.mockResolvedValue({
      ...terminalResult(),
      conversion_metadata: {
        ...terminalResult().conversion_metadata,
        bundle_status: SIR_CONVERT_BUNDLE_STATUS_COMPLETE,
        manual_follow_up_required: false,
        warning_count: 0,
      },
    });
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);

    expect(wrapper.text()).toContain("Konverteringen av provet lyckades delvis");
    expect(wrapper.text()).toContain("1 målfil väntar på att skapas.");
    expect(wrapper.text()).not.toContain("1 fråga saknar facit eller poäng.");
    expect(
      wrapper.find('[data-test="exam-converter-review-questions-action"]').exists(),
    ).toBe(false);
    const reviewPlaceholder = wrapper.find(
      '[data-test="exam-converter-review-questions-placeholder"]',
    );
    expect(reviewPlaceholder.exists()).toBe(true);
    expect(reviewPlaceholder.attributes("aria-hidden")).toBe("true");
    expect(wrapper.text()).toContain("Skapa filer");
    expect(wrapper.text()).not.toContain("Godkänn");

    await wrapper.find('[data-test="exam-converter-accept-current-state-action"]').trigger("click");
    await flushPromises();

    expect(gatewayMocks.submitDigiExamMigration).toHaveBeenLastCalledWith(
      expect.objectContaining({
        ingestionOverlay: expect.objectContaining({
          items: [
            expect.objectContaining({
              item_id: "item-001",
              review_decision: expect.objectContaining({
                accepted_targets: expect.arrayContaining([DIGIEXAM_TARGET_QTI_PACKAGE]),
              }),
            }),
          ],
        }),
      }),
    );
  });

  it("shows one selected AI-facit detail with contextual review actions", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    await wrapper.find('[data-test="exam-converter-question-row-item-004"]').trigger("click");

    const detail = wrapper.find('[data-test="exam-converter-selected-question-detail"]');
    expect(detail.text()).toContain("Fråga 4");
    expect(detail.text()).toContain("item-004");
    expect(detail.text()).toContain("AI-förslag");
    expect(detail.text()).toContain("Använd förslag");
    expect(detail.text()).toContain("Redigera");
    expect(detail.text()).not.toContain("Lämna");
    expect(detail.text()).not.toContain("Avvisa förslag");
    expect(detail.text()).toContain("Finns");
    expect(detail.text()).toContain("Växter tar upp vatten ur marken.");
    expect(detail.text()).toContain(
      "Djur och växter frigör energi ur socker med hjälp av syre.",
    );
    expect(detail.text()).toContain("Saknas");
    expect(detail.text()).toContain("Facit");
    expect(wrapper.text()).not.toContain("candidate-item-004");
    expect(wrapper.text()).not.toContain("digiexam_choice_answer_key_decision_v1");
  });

  it("builds a reviewed-completion overlay when the teacher accepts an AI-facit", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    await wrapper.find('[data-test="exam-converter-question-row-item-004"]').trigger("click");
    await wrapper.find('[data-test="exam-converter-accept-ai-suggestion-action"]').trigger("click");
    await wrapper
      .find('[data-test="exam-converter-apply-reviewed-ai-suggestions-action"]')
      .trigger("click");
    await flushPromises();

    const reviewedSubmit = gatewayMocks.submitDigiExamMigration.mock.calls[1]?.[0];
    expect(reviewedSubmit).toMatchObject({
      completionMode: "local_llm_apply_missing_machine_marked_with_review",
    });
    expect(reviewedSubmit.ingestionOverlay.items).toEqual([
      expect.objectContaining({
        item_id: "item-004",
        manual_answer_key: null,
        review_decision: null,
        effective_item_patch: null,
        reviewed_completion_answer_key: expect.objectContaining({
          kind: "choice",
          review_outcome: "accepted_unchanged",
          candidate_lineage: expect.objectContaining({
            completion_report_sha256: "sha256:completion-report",
            candidate_id: "candidate-item-004",
            validation_state: "valid",
          }),
          answer_payload: {
            kind: "choice",
            correct_alternative_ids: [3],
          },
        }),
      }),
    ]);
  });

  it("reviews and applies a vision-backed Lucktext AI-facit from the second bundle", async () => {
    mockVisionBackedGapFillReviewArtifacts(gatewayMocks);
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    await wrapper.find('[data-test="exam-converter-question-row-item-013"]').trigger("click");

    const detail = wrapper.find('[data-test="exam-converter-selected-question-detail"]');
    expect(detail.text()).toContain("AI-förslag");
    expect(detail.text()).toContain("Lucka 1");
    expect(detail.text()).toContain("kretslopp");

    await wrapper.find('[data-test="exam-converter-accept-ai-suggestion-action"]').trigger("click");
    await wrapper
      .find('[data-test="exam-converter-apply-reviewed-ai-suggestions-action"]')
      .trigger("click");
    await flushPromises();

    const reviewedSubmit = gatewayMocks.submitDigiExamMigration.mock.calls[1]?.[0];
    expect(reviewedSubmit).toMatchObject({
      completionMode: "local_llm_apply_missing_machine_marked_with_review",
      ingestionOverlay: {
        items: [
          expect.objectContaining({
            item_id: "item-013",
            reviewed_completion_answer_key: expect.objectContaining({
              answer_payload: {
                gap_answers: [
                  { accepted_values: ["kretslopp"], gap_id: "gap-001" },
                  { accepted_values: ["näringsväv"], gap_id: "gap-002" },
                ],
                kind: "gap_fill",
              },
              candidate_lineage: expect.objectContaining({
                candidate_id: "candidate-item-013",
                candidate_payload_digest: "sha256:candidate-item-013",
                completion_report_sha256: "sha256:completion-report-gap",
                provider_profile_id: "task309-llama-cpp",
                schema_name: "digiexam_gap_fill_answer_key_decision_v1",
                validation_state: "valid",
              }),
              kind: "gap_fill",
              review_outcome: "accepted_unchanged",
            }),
          }),
        ],
      },
    });
    expect(gatewayMocks.listDigiExamMigrationArtifacts).toHaveBeenLastCalledWith({
      completionReportRequired: false,
      correlationId: "corr_exam_converter_review",
      jobId: REVIEWED_GAP_FILL_APPLY_JOB_ID,
    });
    expect(wrapper.find('[data-test="exam-converter-ai-review-action-panel"]').exists()).toBe(
      false,
    );
    expect(
      wrapper.find('[data-test="exam-converter-accept-current-state-action"]').exists(),
    ).toBe(false);
    expect(wrapper.text()).toContain("Filer (2)");
    expect(wrapper.text()).toContain("Kan hämtas");

    await wrapper.find('[data-test="exam-converter-inspection-tab-questions"]').trigger("click");
    const reviewedRow = wrapper.find('[data-test="exam-converter-question-row-item-013"]');
    expect(reviewedRow.text()).toContain("Lucktext");
    expect(reviewedRow.text()).not.toContain("Facit");
    expect(reviewedRow.find(".lucide-circle-check").exists()).toBe(true);
    expect(reviewedRow.find(".lucide-bot").exists()).toBe(false);
  });

  it("surfaces Lucktext gaps and embedded image structure in the detail pane", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    await wrapper.find('[data-test="exam-converter-question-row-item-001"]').trigger("click");

    const detail = wrapper.find('[data-test="exam-converter-selected-question-detail"]');
    const lucktext = wrapper.find('[data-test="exam-converter-selected-question-lucktext"]');
    expect(detail.text()).toContain("Fråga 1");
    expect(detail.text()).toContain("Lucktext");
    expect(lucktext.text()).toContain("Luckor");
    expect(lucktext.text()).toContain("5");
    expect(lucktext.text()).toContain("Bilder");
    expect(lucktext.text()).toContain("1");
    expect(lucktext.find("img").attributes("src")).toContain("data:image/png;base64,");
  });

  it("keeps file actions gated before the review decision is accepted", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    await wrapper.find('[data-test="exam-converter-inspection-tab-files"]').trigger("click");

    const files = wrapper.find('[data-test="exam-converter-files-readiness-list"]');
    expect(files.exists()).toBe(true);
    expect(files.text()).toContain("Ma1c_Exam.net.pdf");
    expect(files.text()).toContain("QTI-format");
    expect(files.text()).toContain("Granska facit först");
    expect(files.text()).not.toContain("Åtgärd");
    expect(
      wrapper.find('[data-test="exam-converter-download-file-examnet_pdf"]').attributes(
        "disabled",
      ),
    ).toBeDefined();
    expect(
      wrapper.find('[data-test="exam-converter-save-file-examnet_pdf"]').attributes("disabled"),
    ).toBeDefined();
  });

  it("keeps the report diagnostic and points back to the questions mode", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    await wrapper.find('[data-test="exam-converter-inspection-tab-report"]').trigger("click");

    const report = wrapper.find('[data-test="exam-converter-report-summary"]');
    expect(report.text()).toContain("Rapporten visar frågor som saknar facit eller poäng.");
    expect(report.text()).toContain("Facit saknas");
    expect(report.text()).toContain("Poäng saknas");
    expect(report.text()).not.toContain("manifest");
    expect(report.text()).not.toContain("bundle");
    expect(report.text()).not.toContain("Sir Convert");

    await wrapper.find('[data-test="exam-converter-report-open-questions"]').trigger("click");
    expect(wrapper.find('[data-test="exam-converter-question-review-shell"]').exists()).toBe(
      true,
    );
  });
});
