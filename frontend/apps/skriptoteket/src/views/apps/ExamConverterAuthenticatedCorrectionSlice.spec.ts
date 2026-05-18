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

import ExamConverterAuthenticatedView from "./ExamConverterAuthenticatedView.vue";
import {
  finishConversion,
  mockReviewArtifacts,
  submittedJob,
  terminalResult,
} from "./examConverterAuthenticatedReviewFixtures";
import { mockManualGapFillCorrectionArtifacts } from "./examConverterAuthenticatedGapFillReviewFixtures";

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

beforeEach(() => {
  gatewayMocks.applyExamAuthoringCorrections.mockReset();
  gatewayMocks.downloadDigiExamMigrationArtifact.mockReset();
  gatewayMocks.getDigiExamMigrationJob.mockReset();
  gatewayMocks.getDigiExamMigrationResult.mockReset();
  gatewayMocks.issueExamAuthoringCorrectionSourceState.mockReset();
  gatewayMocks.listDigiExamMigrationArtifacts.mockReset();
  gatewayMocks.saveDigiExamMigrationArtifactToUserFiles.mockReset();
  gatewayMocks.submitDigiExamMigration.mockReset();
  gatewayMocks.submitDigiExamMigration.mockResolvedValue(submittedJob("succeeded"));
  gatewayMocks.getDigiExamMigrationResult.mockResolvedValue(terminalResult());
  gatewayMocks.issueExamAuthoringCorrectionSourceState.mockResolvedValue(correctionSourceState());
  gatewayMocks.applyExamAuthoringCorrections.mockResolvedValue(correctionApplyResult());
  mockReviewArtifacts(gatewayMocks);
});

function correctionSourceState() {
  return {
    schema_version: "exam_authoring_correction_source_state_issue_result_v1",
    source_binding: {
      source_authoring_schema_version: "exam_authoring_ir_v1",
      source_bundle_id: "job_exam_converter_review",
      source_file_sha256: "sha256:source",
      source_state_sha256: "sha256:source-state",
      source_state_signature: "hmac-sha256:signature",
    },
    source_authoring_state: {
      schema_version: "exam_authoring_correction_source_state_v1",
      source_authoring_schema_version: "exam_authoring_ir_v1",
      source_state_sha256: "sha256:source-state",
      items: [
        {
          choice_interactions: [],
          gap_open_cloze_interactions: [],
          item_id: "item-012",
          item_type: "open_ended",
          matching_interactions: [],
          max_score: 2,
          prompt_html: "<p>Förklara fotosyntes.</p>",
          prompt_lines: ["Förklara fotosyntes."],
          sequence: 12,
          source_item_fingerprint: "sha256:item-012",
          title: "Fråga 12",
        },
        {
          choice_interactions: [
            {
              answer_key: { correct_choice_ids: [], provenance: "absent" },
              choices: [
                { choice_id: "choice-001", order: 1, source_id: "choice-a", text: "A" },
                { choice_id: "choice-002", order: 2, source_id: "choice-b", text: "B" },
              ],
              evidence: [],
              interaction_id: "choice-item-004",
              interaction_kind: "single_choice",
              max_correct_choices: 1,
              min_correct_choices: 1,
              schema_version: "exam_authoring_ir_v1",
            },
          ],
          gap_open_cloze_interactions: [],
          item_id: "item-004",
          item_type: "single_choice",
          matching_interactions: [],
          max_score: 1,
          prompt_html: "<p>Välj svar.</p>",
          prompt_lines: ["Välj svar."],
          sequence: 4,
          source_item_fingerprint: "sha256:item-004",
          title: "Fråga 4",
        },
        {
          choice_interactions: [],
          gap_open_cloze_interactions: [
            {
              answer_key: { accepted_values: [], provenance: "absent" },
              evidence: [],
              gaps: [
                {
                  display_order: 1,
                  evidence: [],
                  gap_id: "gap-001",
                  prompt_binding: { kind: "source_locator", locator: "gap-001" },
                  required_for_auto_evaluation: true,
                },
                {
                  display_order: 2,
                  evidence: [],
                  gap_id: "gap-002",
                  prompt_binding: { kind: "source_locator", locator: "gap-002" },
                  required_for_auto_evaluation: true,
                },
              ],
              interaction_id: "gap-item-013",
              normalization_profile: "exact_trim_case_sensitive",
              schema_version: "exam_authoring_ir_v1",
            },
          ],
          item_id: "item-013",
          item_type: "gap_fill",
          matching_interactions: [],
          max_score: 1,
          prompt_html: "<p>Fyll i luckorna.</p>",
          prompt_lines: ["Fyll i luckorna."],
          sequence: 13,
          source_item_fingerprint: "sha256:item-013",
          title: "Fråga 13",
        },
      ],
    },
  };
}

function correctionApplyResult(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    schema_version: "exam_authoring_corrections_apply_result_v1",
    request_id: "correction-request",
    source_binding: correctionSourceState().source_binding,
    effective_state: {
      schema_version: "exam_authoring_effective_state_v1",
      effective_state_sha256: "sha256:effective-state",
      items: correctionSourceState().source_authoring_state.items,
    },
    correction_report: {
      schema_version: "exam_authoring_correction_report_v1",
      accepted_entries: [],
      rejected_entries: [],
    },
    target_readiness: {
      schema_version: "target_readiness_report_v1",
      targets: [],
    },
    artifact_availability: [],
    ...overrides,
  };
}

function deferred<T>() {
  let resolve!: (value: T | PromiseLike<T>) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, reject, resolve };
}

async function leaveAndReturnToQuestion(
  wrapper: ReturnType<typeof mount>,
  itemId: string,
): Promise<void> {
  const rowPrefix = "exam-converter-question-row-";
  const otherRow = wrapper
    .findAll(`[data-test^="${rowPrefix}"]`)
    .find((row) => row.attributes("data-test") !== `${rowPrefix}${itemId}`);
  if (otherRow) {
    await otherRow.trigger("click");
  } else {
    await wrapper.find('[data-test="exam-converter-inspection-tab-files"]').trigger("click");
    await wrapper.find('[data-test="exam-converter-inspection-tab-questions"]').trigger("click");
  }
  await wrapper.find(`[data-test="exam-converter-question-row-${itemId}"]`).trigger("click");
}

describe("ExamConverterAuthenticatedView teacher corrections", () => {
  it("submits item text patches through the unified correction route", async () => {
    gatewayMocks.applyExamAuthoringCorrections.mockResolvedValueOnce(
      correctionApplyResult({
        effective_state: {
          schema_version: "exam_authoring_effective_state_v1",
          effective_state_sha256: "sha256:effective-state",
          items: [
            {
              ...correctionSourceState().source_authoring_state.items[0],
              prompt_lines: ["Beskriv fotosyntesens delar."],
              prompt_html: "<p>Beskriv fotosyntesens delar.</p>",
            },
          ],
        },
      }),
    );
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    await wrapper.find('[data-test="exam-converter-question-row-item-012"]').trigger("click");
    await wrapper
      .find<HTMLTextAreaElement>('[data-test="exam-converter-item-text-patch-input"]')
      .setValue("Beskriv fotosyntesens delar.");
    await wrapper
      .find('[data-test="exam-converter-apply-item-text-patch-action"]')
      .trigger("click");
    await flushPromises();

    expect(gatewayMocks.applyExamAuthoringCorrections.mock.calls[0]?.[0]).toMatchObject({
      request: {
        corrections: [
          {
            kind: "item_text_patch",
            item_id: "item-012",
            patches: [
              {
                field: "prompt_lines",
                value: "Beskriv fotosyntesens delar.",
              },
            ],
          },
        ],
      },
    });
    await wrapper.find('[data-test="exam-converter-question-row-item-012"]').trigger("click");
    expect(wrapper.find('[data-test="exam-converter-selected-question-detail"]').text()).toContain(
      "Beskriv fotosyntesens delar.",
    );
    await leaveAndReturnToQuestion(wrapper, "item-012");
    expect(wrapper.find('[data-test="exam-converter-selected-question-detail"]').text()).toContain(
      "Beskriv fotosyntesens delar.",
    );
    expect(
      wrapper.find<HTMLTextAreaElement>('[data-test="exam-converter-item-text-patch-input"]')
        .element.value,
    ).toBe("Beskriv fotosyntesens delar.");
  });

  it("shows returned item titles after item-title patches and item navigation", async () => {
    gatewayMocks.applyExamAuthoringCorrections.mockResolvedValueOnce(
      correctionApplyResult({
        effective_state: {
          schema_version: "exam_authoring_effective_state_v1",
          effective_state_sha256: "sha256:effective-state",
          items: [
            {
              ...correctionSourceState().source_authoring_state.items[0],
              title: "Fotosyntesens delar",
            },
          ],
        },
      }),
    );
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    await wrapper.find('[data-test="exam-converter-question-row-item-012"]').trigger("click");
    await wrapper
      .find<HTMLSelectElement>('[data-test="exam-converter-item-text-patch-field"]')
      .setValue("item_title");
    await wrapper
      .find<HTMLTextAreaElement>('[data-test="exam-converter-item-text-patch-input"]')
      .setValue("Fotosyntesens delar");
    await wrapper
      .find('[data-test="exam-converter-apply-item-text-patch-action"]')
      .trigger("click");
    await flushPromises();

    await leaveAndReturnToQuestion(wrapper, "item-012");

    expect(wrapper.find('[data-test="exam-converter-effective-item-title"]').text()).toContain(
      "Fotosyntesens delar",
    );
    await wrapper
      .find<HTMLSelectElement>('[data-test="exam-converter-item-text-patch-field"]')
      .setValue("item_title");
    expect(
      wrapper.find<HTMLTextAreaElement>('[data-test="exam-converter-item-text-patch-input"]')
        .element.value,
    ).toBe("Fotosyntesens delar");
  });

  it("keeps the review surface mounted while a teacher correction is applying", async () => {
    const sourceState = deferred<ReturnType<typeof correctionSourceState>>();
    gatewayMocks.issueExamAuthoringCorrectionSourceState.mockReturnValueOnce(sourceState.promise);
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    await wrapper.find('[data-test="exam-converter-question-row-item-012"]').trigger("click");
    await wrapper
      .find<HTMLInputElement>('[data-test="exam-converter-point-correction-input"]')
      .setValue("3");
    await wrapper.find('[data-test="exam-converter-apply-point-correction-action"]').trigger("click");
    await wrapper.vm.$nextTick();

    expect(gatewayMocks.submitDigiExamMigration).toHaveBeenCalledTimes(1);
    expect(wrapper.find('[data-test="exam-converter-running-surface"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-converter-inspection-surface"]').exists()).toBe(true);
    expect(
      wrapper.find('[data-test="exam-converter-apply-point-correction-action"]').attributes(
        "disabled",
      ),
    ).toBeDefined();

    sourceState.resolve(correctionSourceState());
    await flushPromises();
  });

  it("submits point corrections as source-bound overlays and waits for returned state", async () => {
    gatewayMocks.applyExamAuthoringCorrections.mockResolvedValueOnce(
      correctionApplyResult({
        effective_state: {
          schema_version: "exam_authoring_effective_state_v1",
          effective_state_sha256: "sha256:effective-state",
          items: [
            {
              ...correctionSourceState().source_authoring_state.items[0],
              max_score: 3,
            },
          ],
        },
      }),
    );
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

    const pointCorrectionSubmit = gatewayMocks.applyExamAuthoringCorrections.mock.calls[0]?.[0];
    expect(pointCorrectionSubmit).toMatchObject({
      request: {
        schema_version: "exam_authoring_corrections_apply_request_v1",
        source_binding: {
          source_state_sha256: "sha256:source-state",
        },
        corrections: [
          {
            kind: "point_correction",
            item_id: "item-012",
            max_score: 3,
            source_item_fingerprint: "sha256:item-012",
          },
        ],
      },
    });
    expect(gatewayMocks.issueExamAuthoringCorrectionSourceState).toHaveBeenCalledWith({
      correlationId: "corr_exam_converter_review",
      request: {
        schema_version: "exam_authoring_correction_source_state_issue_request_v1",
        job_id: "job_exam_converter_review",
      },
    });
    expect(wrapper.find('[data-test="exam-converter-question-row-item-012"]').text()).toContain(
      "3 p",
    );
    await leaveAndReturnToQuestion(wrapper, "item-012");
    expect(
      wrapper.find<HTMLInputElement>('[data-test="exam-converter-point-correction-input"]').element
        .value,
    ).toBe("3");
    expect(wrapper.find('[data-test="exam-converter-selected-question-detail"]').text()).toContain(
      "Ändrad",
    );
  });

  it("submits manual choice answer keys before files unlock", async () => {
    mockReviewArtifacts(gatewayMocks, { choiceCandidateAvailable: false });
    gatewayMocks.applyExamAuthoringCorrections.mockResolvedValueOnce(
      correctionApplyResult({
        effective_state: {
          schema_version: "exam_authoring_effective_state_v1",
          effective_state_sha256: "sha256:effective-state",
          items: [
            {
              ...correctionSourceState().source_authoring_state.items[1],
              choice_interactions: [
                {
                  ...correctionSourceState().source_authoring_state.items[1].choice_interactions[0],
                  answer_key: {
                    correct_choice_ids: ["choice-002"],
                    provenance: "teacher_provided",
                  },
                  choices: [],
                },
              ],
            },
          ],
        },
      }),
    );
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    expect(wrapper.find('[data-test="exam-converter-inspection-attention-count"]').text()).toContain(
      "2 frågor",
    );
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

    const manualAnswerKeySubmit = gatewayMocks.applyExamAuthoringCorrections.mock.calls[0]?.[0];
    expect(manualAnswerKeySubmit).toMatchObject({
      request: {
        corrections: [
          {
            kind: "manual_choice_answer_key",
            item_id: "item-004",
            item_type: "single_choice",
            correct_choice_ids: ["choice-002"],
            interaction_id: "choice-item-004",
            submission_origin: "teacher_authored",
            source_item_fingerprint: "sha256:item-004",
          },
        ],
      },
    });

    const correctedRow = wrapper.find('[data-test="exam-converter-question-row-item-004"]');
    expect(correctedRow.text()).not.toContain("Facit");
    expect(wrapper.find('[data-test="exam-converter-inspection-attention-count"]').text()).toContain(
      "1 fråga",
    );
    await correctedRow.trigger("click");
    expect(wrapper.find('[data-test="exam-converter-selected-question-detail"]').text()).toContain(
      "Ändrat",
    );
    await leaveAndReturnToQuestion(wrapper, "item-004");
    expect(wrapper.find('[data-test="exam-converter-selected-question-detail"]').text()).toContain(
      "Facit",
    );
    expect(wrapper.find('[data-test="exam-converter-selected-question-detail"]').text()).toContain(
      "Ändrat",
    );
    expect(wrapper.find('[data-test="exam-converter-manual-answer-key-editor"]').exists()).toBe(
      false,
    );
    expect(
      wrapper.find('[data-test="exam-converter-effective-choice-2"]').classes(),
    ).not.toContain("bg-success");
    expect(
      wrapper.find('[data-test="exam-converter-effective-choice-ordinal-2"]').classes(),
    ).toContain("bg-success");
    expect(
      wrapper.find('[data-test="exam-converter-effective-choice-ordinal-1"]').classes(),
    ).not.toContain("bg-success");
    await wrapper.find('[data-test="exam-converter-inspection-tab-files"]').trigger("click");
    expect(
      wrapper.find('[data-test="exam-converter-download-file-examnet_pdf"]').attributes(
        "disabled",
      ),
    ).toBeDefined();
  });

  it("submits manual gap-fill accepted values before files unlock", async () => {
    mockManualGapFillCorrectionArtifacts(gatewayMocks);
    gatewayMocks.issueExamAuthoringCorrectionSourceState.mockResolvedValue(correctionSourceState());
    gatewayMocks.applyExamAuthoringCorrections.mockResolvedValueOnce(
      correctionApplyResult({
        effective_state: {
          schema_version: "exam_authoring_effective_state_v1",
          effective_state_sha256: "sha256:effective-state",
          items: [
            {
              ...correctionSourceState().source_authoring_state.items[2],
              gap_open_cloze_interactions: [
                {
                  ...correctionSourceState().source_authoring_state.items[2]
                    .gap_open_cloze_interactions[0],
                  answer_key: {
                    accepted_values: [
                      {
                        evidence: [],
                        gap_id: "gap-001",
                        provenance: "teacher_provided",
                        value: "kretslopp",
                      },
                      {
                        evidence: [],
                        gap_id: "gap-002",
                        provenance: "teacher_provided",
                        value: "näringsväv",
                      },
                    ],
                    provenance: "teacher_provided",
                  },
                },
              ],
            },
          ],
        },
      }),
    );
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

    const manualGapSubmit = gatewayMocks.applyExamAuthoringCorrections.mock.calls[0]?.[0];
    expect(manualGapSubmit).toMatchObject({
      request: {
        corrections: [
          {
            kind: "manual_gap_open_cloze_answer_key",
            item_id: "item-013",
            item_type: "gap_fill",
            gap_answers: [
              { accepted_values: ["kretslopp"], gap_id: "gap-001" },
              { accepted_values: ["näringsväv"], gap_id: "gap-002" },
            ],
            interaction_id: "gap-item-013",
            submission_origin: "teacher_authored",
            source_item_fingerprint: "sha256:item-013",
          },
        ],
      },
    });

    const correctedRow = wrapper.find('[data-test="exam-converter-question-row-item-013"]');
    expect(correctedRow.text()).not.toContain("Facit");
    await correctedRow.trigger("click");
    const detail = wrapper.find('[data-test="exam-converter-selected-question-detail"]');
    expect(detail.text()).toContain("gap-001: kretslopp");
    expect(detail.text()).toContain("gap-002: näringsväv");
    expect(detail.text()).toContain("Ändrat");
    await leaveAndReturnToQuestion(wrapper, "item-013");
    expect(wrapper.find('[data-test="exam-converter-effective-gap-answer-gap-001"]').text()).toContain(
      "kretslopp",
    );
    expect(wrapper.find('[data-test="exam-converter-effective-gap-answer-gap-002"]').text()).toContain(
      "näringsväv",
    );
    await wrapper.find('[data-test="exam-converter-inspection-tab-files"]').trigger("click");
    expect(
      wrapper.find('[data-test="exam-converter-download-file-examnet_pdf"]').attributes(
        "disabled",
      ),
    ).toBeDefined();
  });
});
