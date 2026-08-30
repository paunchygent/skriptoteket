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

import { ApiError } from "../../api/client";
import ExamConverterAuthenticatedView from "./ExamConverterAuthenticatedView.vue";
import {
  answerKeyReviewItem,
  answerKeyReviewStateReport,
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
  replayLocalExamConversion: vi.fn(),
  saveDigiExamMigrationArtifactToUserFiles: vi.fn(),
  submitDigiExamMigration: vi.fn(),
}));

vi.mock("../../api/examConverterLocal", () => ({
  downloadLocalExamConversionArtifact: gatewayMocks.downloadDigiExamMigrationArtifact,
  getLocalExamConversionJob: gatewayMocks.getDigiExamMigrationJob,
  getLocalExamConversionResult: gatewayMocks.getDigiExamMigrationResult,
  getLocalExamConversionSourceState: gatewayMocks.issueExamAuthoringCorrectionSourceState,
  listLocalExamConversionArtifacts: gatewayMocks.listDigiExamMigrationArtifacts,
  replayLocalExamConversion: gatewayMocks.replayLocalExamConversion,
  submitLocalExamConversion: gatewayMocks.submitDigiExamMigration,
}));
const correctionSessionApiMocks = vi.hoisted(() => ({
  getExamConverterCorrectionSession: vi.fn(),
  registerExamConverterConversionHubJob: vi.fn(),
  upsertExamConverterCorrectionIntent: vi.fn(),
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

vi.mock("../../api/examConverterCorrectionSessions", () => ({
  getExamConverterCorrectionSession: correctionSessionApiMocks.getExamConverterCorrectionSession,
  registerExamConverterConversionHubJob:
    correctionSessionApiMocks.registerExamConverterConversionHubJob,
  upsertExamConverterCorrectionIntent: correctionSessionApiMocks.upsertExamConverterCorrectionIntent,
}));

beforeEach(() => {
  window.sessionStorage.clear();
  lastCorrectionSession = emptyCorrectionSession();
  correctionSessionApiMocks.getExamConverterCorrectionSession.mockReset();
  correctionSessionApiMocks.registerExamConverterConversionHubJob.mockReset();
  correctionSessionApiMocks.upsertExamConverterCorrectionIntent.mockReset();
  gatewayMocks.applyExamAuthoringCorrections.mockReset();
  gatewayMocks.downloadDigiExamMigrationArtifact.mockReset();
  gatewayMocks.getDigiExamMigrationJob.mockReset();
  gatewayMocks.getDigiExamMigrationResult.mockReset();
  gatewayMocks.issueExamAuthoringCorrectionSourceState.mockReset();
  gatewayMocks.listDigiExamMigrationArtifacts.mockReset();
  gatewayMocks.replayLocalExamConversion.mockReset();
  gatewayMocks.saveDigiExamMigrationArtifactToUserFiles.mockReset();
  gatewayMocks.submitDigiExamMigration.mockReset();
  gatewayMocks.submitDigiExamMigration.mockResolvedValue(submittedJob("succeeded"));
  gatewayMocks.getDigiExamMigrationResult.mockResolvedValue(terminalResult());
  gatewayMocks.issueExamAuthoringCorrectionSourceState.mockResolvedValue(correctionSourceState());
  gatewayMocks.applyExamAuthoringCorrections.mockResolvedValue(correctionApplyResult());
  gatewayMocks.replayLocalExamConversion.mockResolvedValue({});
  correctionSessionApiMocks.registerExamConverterConversionHubJob.mockResolvedValue({
    job_id: "local-conversion-hub-job-1",
    status: "succeeded",
    upstream_job_id: "job_exam_converter_review",
  });
  correctionSessionApiMocks.upsertExamConverterCorrectionIntent.mockImplementation(
    ({ request }: { request: { intent: Record<string, unknown> } }) =>
      Promise.resolve(correctionSessionFromIntent(request.intent)),
  );
  correctionSessionApiMocks.getExamConverterCorrectionSession.mockImplementation(() =>
    Promise.resolve(lastCorrectionSession),
  );
  mockReviewArtifacts(gatewayMocks);
});

let lastCorrectionSession: Record<string, unknown> = emptyCorrectionSession();

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
    answer_key_review_state: correctionAnswerKeyReviewState(),
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

function correctionAnswerKeyReviewState() {
  return answerKeyReviewStateReport([
    answerKeyReviewItem(),
    answerKeyReviewItem({
      choice_ids: ["choice-002"],
      choice_interaction_ids: ["choice-item-004"],
      current_key_origin: "teacher_authored",
      item_id: "item-004",
      item_type: "single_choice",
      message_key: "exam_converter.answer_key.teacher_answer_key_present",
      reasons: ["teacher_answer_key_present"],
      review_state: "teacher_modified",
      sequence: 4,
      source_item_fingerprint: "sha256:item-004",
    }),
    answerKeyReviewItem({
      choice_ids: ["choice-1", "choice-2"],
      choice_interaction_ids: ["choice-item-005"],
      current_key_origin: "reviewed_advisory",
      item_id: "item-005",
      item_type: "multiple_response",
      message_key: "exam_converter.answer_key.reviewed_advisory_accepted",
      reasons: ["reviewed_advisory_accepted"],
      review_state: "review_complete",
      sequence: 5,
      source_item_fingerprint: "sha256:item-005",
    }),
    answerKeyReviewItem({
      current_key_origin: "none",
      item_id: "item-006",
      item_type: "open_ended",
      message_key: "exam_converter.answer_key.source_present",
      reasons: ["source_answer_key_present"],
      review_state: "review_complete",
      sequence: 6,
      source_item_fingerprint: "sha256:item-006",
    }),
    answerKeyReviewItem({
      current_key_origin: "teacher_edited_advisory",
      item_id: "item-012",
      item_type: "open_ended",
      message_key: "exam_converter.answer_key.teacher_modified",
      reasons: ["teacher_edited_advisory_candidate"],
      review_state: "teacher_modified",
      sequence: 12,
      source_item_fingerprint: "sha256:item-012",
    }),
    answerKeyReviewItem({
      current_key_origin: "teacher_authored",
      gap_ids: ["gap-001", "gap-002"],
      gap_interaction_ids: ["gap-item-013"],
      item_id: "item-013",
      item_type: "gap_fill",
      message_key: "exam_converter.answer_key.teacher_answer_key_present",
      reasons: ["teacher_answer_key_present"],
      review_state: "teacher_modified",
      sequence: 13,
      source_item_fingerprint: "sha256:item-013",
    }),
  ]);
}

function emptyCorrectionSession() {
  return {
    active_intents: [],
    conversion_hub_job_id: "local-conversion-hub-job-1",
    owner_user_id: "11111111-1111-4111-8111-111111111111",
    session_id: null,
    session_version: 0,
    source_binding: null,
  };
}

function targetKeyForIntent(intent: Record<string, unknown>): string {
  const target = intent.target as Record<string, unknown> | undefined;
  if (
    intent.kind === "manual_choice_answer_key" ||
    intent.kind === "manual_gap_open_cloze_answer_key"
  ) {
    return `${String(intent.kind)}:${String(intent.item_id)}:${String(target?.interaction_id)}`;
  }
  if (intent.kind === "item_text_patch") {
    return `${String(intent.kind)}:${String(intent.item_id)}:${String(target?.text_field)}`;
  }
  return `${String(intent.kind)}:${String(intent.item_id)}`;
}

function correctionSessionFromIntent(intent: Record<string, unknown>) {
  lastCorrectionSession = {
    active_intents: [
      {
        ...intent,
        intent_id: "22222222-2222-4222-8222-222222222222",
        target: intent.target ?? {},
        target_key: targetKeyForIntent(intent),
      },
    ],
    conversion_hub_job_id: "local-conversion-hub-job-1",
    owner_user_id: "11111111-1111-4111-8111-111111111111",
    session_id: "33333333-3333-4333-8333-333333333333",
    session_version: 1,
    source_binding: intent.source_binding,
  };
  return lastCorrectionSession;
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

    expect(correctionSessionApiMocks.upsertExamConverterCorrectionIntent.mock.calls[0]?.[0]).toMatchObject({
      request: {
        intent: {
            kind: "item_text_patch",
            item_id: "item-012",
            payload: { patches: [
              {
                field: "prompt_lines",
                value: "Beskriv fotosyntesens delar.",
              },
            ] },
          },
      },
    });
    expect(gatewayMocks.replayLocalExamConversion).toHaveBeenCalledWith({
      correlationId: "corr_exam_converter_review",
      jobId: "job_exam_converter_review",
    });
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
      .find<HTMLInputElement>('[data-test="exam-converter-item-title-patch-input"]')
      .setValue("Fotosyntesens delar");
    await wrapper
      .find('[data-test="exam-converter-apply-item-title-patch-action"]')
      .trigger("click");
    await flushPromises();

    expect(correctionSessionApiMocks.upsertExamConverterCorrectionIntent).toHaveBeenCalledWith(
      expect.objectContaining({
        request: expect.objectContaining({
          intent: expect.objectContaining({ kind: "item_text_patch" }),
        }),
      }),
    );
    expect(gatewayMocks.replayLocalExamConversion).toHaveBeenCalledTimes(1);
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

    const pointCorrectionIntent =
      correctionSessionApiMocks.upsertExamConverterCorrectionIntent.mock.calls[0]?.[0];
    expect(pointCorrectionIntent).toMatchObject({
      conversionHubJobId: "job_exam_converter_review",
      request: {
        expected_session_version: 0,
        intent: {
          entry_id: "corr-points-item-012",
          item_id: "item-012",
          kind: "point_correction",
          payload: { max_score: 3 },
          source_binding: {
            source_state_sha256: "sha256:source-state",
          },
          source_item_fingerprint: "sha256:item-012",
        },
      },
    });
    expect(gatewayMocks.replayLocalExamConversion).toHaveBeenCalledWith({
      correlationId: "corr_exam_converter_review",
      jobId: "job_exam_converter_review",
    });
    expect(gatewayMocks.issueExamAuthoringCorrectionSourceState).toHaveBeenCalledWith({
      jobId: "job_exam_converter_review",
    });
    expect(wrapper.find('[data-test="exam-converter-selected-question-detail"]').text()).not.toContain(
      "Ändrad",
    );
    expect(wrapper.find('[data-test="exam-converter-correction-session-status"]').exists()).toBe(
      false,
    );
  });

  it("reads back saved correction intents after a route reload and replays them before rendering", async () => {
    gatewayMocks.applyExamAuthoringCorrections.mockImplementation(({ request }) => {
      const hasPointCorrection = request.corrections.some(
        (correction: { kind: string }) => correction.kind === "point_correction",
      );
      return Promise.resolve(
        correctionApplyResult({
          effective_state: {
            schema_version: "exam_authoring_effective_state_v1",
            effective_state_sha256: "sha256:effective-state",
            items: [
              {
                ...correctionSourceState().source_authoring_state.items[0],
                max_score: hasPointCorrection ? 3 : 2,
              },
            ],
          },
        }),
      );
    });
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    await wrapper.find('[data-test="exam-converter-question-row-item-012"]').trigger("click");
    await wrapper
      .find<HTMLInputElement>('[data-test="exam-converter-point-correction-input"]')
      .setValue("3");
    await wrapper.find('[data-test="exam-converter-apply-point-correction-action"]').trigger("click");
    await flushPromises();
    wrapper.unmount();

    const reloaded = mount(ExamConverterAuthenticatedView);
    await flushPromises();

    expect(correctionSessionApiMocks.getExamConverterCorrectionSession).toHaveBeenCalledWith({
      conversionHubJobId: "job_exam_converter_review",
    });
    expect(gatewayMocks.replayLocalExamConversion).toHaveBeenCalledTimes(2);
    expect(reloaded.find('[data-test="exam-converter-inspection-surface"]').exists()).toBe(true);
  });

  it("shows conflict state when the persisted session version is stale", async () => {
    correctionSessionApiMocks.upsertExamConverterCorrectionIntent.mockRejectedValueOnce(
      new ApiError({
        code: "CONFLICT",
        message: "Session changed",
        status: 409,
      }),
    );
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    await wrapper.find('[data-test="exam-converter-question-row-item-012"]').trigger("click");
    await wrapper
      .find<HTMLInputElement>('[data-test="exam-converter-point-correction-input"]')
      .setValue("3");
    await wrapper.find('[data-test="exam-converter-apply-point-correction-action"]').trigger("click");
    await flushPromises();

    expect(wrapper.find('[data-test="exam-converter-correction-session-status"]').text()).toContain(
      "provet ändrades samtidigt",
    );
  });

  it("keeps saved intent truth distinct when replay is unavailable", async () => {
    gatewayMocks.replayLocalExamConversion.mockRejectedValueOnce(new Error("local replay failed"));
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    await wrapper.find('[data-test="exam-converter-question-row-item-012"]').trigger("click");
    await wrapper
      .find<HTMLInputElement>('[data-test="exam-converter-point-correction-input"]')
      .setValue("3");
    await wrapper.find('[data-test="exam-converter-apply-point-correction-action"]').trigger("click");
    await flushPromises();

    expect(correctionSessionApiMocks.upsertExamConverterCorrectionIntent).toHaveBeenCalledTimes(1);
    expect(wrapper.find('[data-test="exam-converter-correction-session-status"]').exists()).toBe(
      false,
    );
    expect(gatewayMocks.replayLocalExamConversion).toHaveBeenCalledTimes(1);
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
      "1 fråga",
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

    const manualAnswerKeySubmit =
      correctionSessionApiMocks.upsertExamConverterCorrectionIntent.mock.calls[0]?.[0];
    expect(manualAnswerKeySubmit).toMatchObject({
      request: {
        intent: {
            kind: "manual_choice_answer_key",
            item_id: "item-004",
            item_type: "single_choice",
            payload: { correct_choice_ids: ["choice-002"] },
            source_item_fingerprint: "sha256:item-004",
          },
      },
    });
    expect(gatewayMocks.replayLocalExamConversion).toHaveBeenCalledTimes(1);
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

    const manualGapSubmit =
      correctionSessionApiMocks.upsertExamConverterCorrectionIntent.mock.calls[0]?.[0];
    expect(manualGapSubmit).toMatchObject({
      request: {
        intent: {
            kind: "manual_gap_open_cloze_answer_key",
            item_id: "item-013",
            item_type: "gap_fill",
            payload: { gap_answers: [
              { accepted_values: ["kretslopp"], gap_id: "gap-001" },
              { accepted_values: ["näringsväv"], gap_id: "gap-002" },
            ] },
            source_item_fingerprint: "sha256:item-013",
          },
      },
    });
    expect(gatewayMocks.replayLocalExamConversion).toHaveBeenCalledTimes(1);
  });
});
