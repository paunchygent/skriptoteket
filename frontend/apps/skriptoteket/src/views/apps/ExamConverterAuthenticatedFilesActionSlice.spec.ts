/**
 * Exam Converter corrected file-action behavior.
 *
 * Slice purpose:
 *   Keep generated file actions bound to producer-authorized artifact
 *   references after durable teacher corrections are replayed.
 *
 * Expected behavior:
 *   File actions stay disabled until the producer report marks a generated
 *   target exportable and provides an authorized artifact reference for the
 *   same artifact authority that drives the visible row.
 *
 * Recommended implementation shape:
 *   Keep file rows inside `Filer` and use replay-result artifact references
 *   for corrected downloads and owner-scoped user-file saves.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ExamConverterAuthenticatedView from "./ExamConverterAuthenticatedView.vue";
import ExamConverterFilesReadinessList from "./exam-converter-authenticated/ExamConverterFilesReadinessList.vue";
import {
  correctionApplyResult,
  correctionSourceState,
  createCorrectionSessionRecorder,
} from "./examConverterAuthenticatedCorrectionSessionFixtures";
import {
  answerKeyReviewStateReportPayload,
  artifactJsonBlob,
  fileArtifactBlob,
  filesTerminalResult,
  singleMissingChoiceManifest,
  submittedFilesJob,
  targetReadinessReportPayload,
} from "./examConverterAuthenticatedFilesActionPayloads";
import {
  DIGIEXAM_ARTIFACT_ANSWER_KEY_COMPLETION_REPORT,
  DIGIEXAM_ARTIFACT_ANSWER_KEY_REVIEW_STATE_REPORT,
} from "../../api/sirConvertGateway/contractValues";
import {
  ANSWER_KEY_COMPLETION_REPORT_SCHEMA_VERSION,
  DIGIEXAM_EFFECTIVE_EXAM_SCHEMA_VERSION,
  DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
  DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
} from "../../api/sirConvertGateway/schemaVersions";

const gatewayMocks = vi.hoisted(() => ({
  applyExamAuthoringCorrections: vi.fn(),
  downloadDigiExamMigrationArtifact: vi.fn(),
  downloadDigiExamMigrationCorrectionReplayArtifact: vi.fn(),
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
  upsertExamConverterCorrectionIntent: vi.fn(),
}));
const correctionSessionRecorder = createCorrectionSessionRecorder();

vi.mock("../../api/sirConvertGateway", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api/sirConvertGateway")>();
  return {
    ...actual,
    applyExamAuthoringCorrections: gatewayMocks.applyExamAuthoringCorrections,
    downloadDigiExamMigrationArtifact: gatewayMocks.downloadDigiExamMigrationArtifact,
    downloadDigiExamMigrationCorrectionReplayArtifact:
      gatewayMocks.downloadDigiExamMigrationCorrectionReplayArtifact,
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

function mockReviewArtifacts(): void {
  gatewayMocks.listDigiExamMigrationArtifacts.mockResolvedValue({
    artifacts: [
      {
        artifact_key: "examnet_pdf",
        availability: "unavailable",
        content_type: "application/pdf",
        filename: "Ma1c_Exam.net.pdf",
        unavailable_code: "manual_answer_key_required",
        sha256: null,
        size_bytes: null,
      },
      {
        artifact_key: "qti_package",
        availability: "unavailable",
        content_type: "application/zip",
        filename: "Ma1c_QTI.zip",
        unavailable_code: "manual_answer_key_required",
        sha256: null,
        size_bytes: null,
      },
      {
        artifact_key: DIGIEXAM_ARTIFACT_ANSWER_KEY_REVIEW_STATE_REPORT,
        availability: "available",
        content_type: "application/json",
        filename: "answer-key-review-state.json",
        sha256: "sha256:answer-key-review-state-files",
        size_bytes: 512,
      },
      {
        artifact_key: DIGIEXAM_ARTIFACT_ANSWER_KEY_COMPLETION_REPORT,
        availability: "available",
        content_type: "application/json",
        filename: "answer-key-completion-report.json",
        sha256: "sha256:completion-report",
        size_bytes: 512,
      },
    ],
    bundle_status: "needs_review",
    job_id: "job_exam_converter_files",
    source: {
      filename: "Ma1c_NationelltProv_HT25.dxe",
      format: "digiexam_dxe",
      sha256: "sha256:source",
    },
    manual_follow_up: {
      artifact_key: "manual_follow_up_report",
      count: 1,
      required: true,
    },
    schema_version: DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
    warnings: {
      artifact_key: "warnings_report",
      count: 0,
    },
    readiness: {
      artifact_key: "target_readiness_report",
      exportable_targets: [],
      review_required: true,
    },
    source_binding: {
      source_ir_schema_version: DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
      source_ir_sha256: "sha256:ir",
      effective_exam_schema_version: DIGIEXAM_EFFECTIVE_EXAM_SCHEMA_VERSION,
      effective_exam_sha256: "sha256:effective",
    },
  });
  gatewayMocks.downloadDigiExamMigrationArtifact.mockImplementation(
    ({ artifactKey }: { artifactKey: string }) => {
      if (artifactKey === "ir_json") {
        return Promise.resolve(
          artifactJsonBlob("ir_json", {
            items: [
              {
                answer_key: { provenance: "absent" },
                item_id: "item-001",
                item_type: "multiple_choice",
                max_score: 1,
                alternatives: [
                  { id: 1, title: "21", about: "" },
                  { id: 2, title: "37", about: "" },
                ],
                prompt_html: null,
                prompt_lines: ["Vilket av följande tal är ett primtal?"],
                sequence: 1,
                title: "Vilket av följande tal är ett primtal?",
                warnings: [],
              },
            ],
            manual_follow_ups: [
              {
                item_id: "item-001",
                message: "Manual answer key is required.",
                reason: "manual_answer_key_required",
                source_span: null,
              },
            ],
            parse_status: "success",
            renderer_ready: true,
            schema_version: DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
            source_filename: "Ma1c_NationelltProv_HT25.dxe",
            source_producer: null,
            warnings: [],
          }),
        );
      }
      if (artifactKey === "migration_manifest") {
        return Promise.resolve(
          artifactJsonBlob("migration_manifest", singleMissingChoiceManifest),
        );
      }
      if (artifactKey === "target_readiness_report") {
        return Promise.resolve(
          artifactJsonBlob(
            "target_readiness_report",
            targetReadinessReportPayload(),
          ),
        );
      }
      if (artifactKey === DIGIEXAM_ARTIFACT_ANSWER_KEY_COMPLETION_REPORT) {
        return Promise.resolve(
          artifactJsonBlob(DIGIEXAM_ARTIFACT_ANSWER_KEY_COMPLETION_REPORT, {
            schema_version: ANSWER_KEY_COMPLETION_REPORT_SCHEMA_VERSION,
            completion_mode: "local_llm_suggest_missing_machine_marked",
            job_id: "job_exam_converter_files",
            items: [
              {
                item_id: "item-001",
                sequence: 1,
                item_type: "multiple_choice",
                decision_state: "manual_follow_up_required",
                validation_state: "manual_follow_up_required",
                backend_status: "skipped",
                backend_failure_code: null,
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
          }),
        );
      }
      if (artifactKey === DIGIEXAM_ARTIFACT_ANSWER_KEY_REVIEW_STATE_REPORT) {
        return Promise.resolve(
          artifactJsonBlob(
            DIGIEXAM_ARTIFACT_ANSWER_KEY_REVIEW_STATE_REPORT,
            answerKeyReviewStateReportPayload(),
          ),
        );
      }
      return Promise.resolve(
        fileArtifactBlob(
          artifactKey,
          artifactKey === "examnet_pdf" ? "Ma1c_Exam.net.pdf" : "Ma1c_QTI.zip",
          artifactKey === "examnet_pdf" ? "application/pdf" : "application/zip",
        ),
      );
    },
  );
  gatewayMocks.saveDigiExamMigrationArtifactToUserFiles.mockResolvedValue({
    source_artifact_id: "documents.conversion_hub:job_exam_converter_files:qti_package",
    vault_artifact: {
      bytes: 4,
      created_at: "2026-05-14T10:00:00Z",
      file_id: "vault-file-1",
      name: "Ma1c_QTI.zip",
    },
  });
}

async function chooseSourceFile(wrapper: ReturnType<typeof mount>) {
  const input = wrapper.find<HTMLInputElement>(
    '[data-test="exam-converter-source-file-input"]',
  );
  Object.defineProperty(input.element, "files", {
    configurable: true,
    value: [
      new File(["exam"], "Ma1c_NationelltProv_HT25.dxe", {
        type: "application/octet-stream",
      }),
    ],
  });
  await input.trigger("change");
}

async function finishConversion(wrapper: ReturnType<typeof mount>) {
  await chooseSourceFile(wrapper);
  await wrapper.find('[data-test="exam-converter-start-conversion"]').trigger("click");
  await flushPromises();
}

beforeEach(() => {
  correctionSessionRecorder.reset();
  for (const mock of Object.values(correctionSessionApiMocks)) mock.mockReset();
  gatewayMocks.applyExamAuthoringCorrections.mockReset();
  gatewayMocks.downloadDigiExamMigrationArtifact.mockReset();
  gatewayMocks.downloadDigiExamMigrationCorrectionReplayArtifact.mockReset();
  gatewayMocks.getDigiExamMigrationJob.mockReset();
  gatewayMocks.getDigiExamMigrationResult.mockReset();
  gatewayMocks.issueExamAuthoringCorrectionSourceState.mockReset();
  gatewayMocks.listDigiExamMigrationArtifacts.mockReset();
  gatewayMocks.saveDigiExamMigrationArtifactToUserFiles.mockReset();
  gatewayMocks.submitDigiExamMigration.mockReset();
  gatewayMocks.submitDigiExamMigration.mockImplementation(() => {
    mockReviewArtifacts();
    return Promise.resolve(submittedFilesJob("succeeded"));
  });
  gatewayMocks.getDigiExamMigrationResult.mockResolvedValue(filesTerminalResult());
  correctionSessionApiMocks.registerExamConverterConversionHubJob.mockResolvedValue({
    job_id: "local-conversion-hub-job-files",
    status: "succeeded",
    upstream_job_id: "job_exam_converter_files",
  });
  correctionSessionApiMocks.getExamConverterCorrectionSession.mockImplementation(() =>
    Promise.resolve(correctionSessionRecorder.current()),
  );
  correctionSessionApiMocks.upsertExamConverterCorrectionIntent.mockImplementation(
    ({ request }: { request: { intent: Record<string, unknown> } }) =>
      Promise.resolve(correctionSessionRecorder.recordIntent(request.intent)),
  );
  gatewayMocks.issueExamAuthoringCorrectionSourceState.mockResolvedValue(correctionSourceState());
  gatewayMocks.applyExamAuthoringCorrections.mockResolvedValue(correctionApplyResult());
  gatewayMocks.downloadDigiExamMigrationCorrectionReplayArtifact.mockImplementation(
    ({ artifactKey }: { artifactKey: string }) =>
      Promise.resolve(fileArtifactBlob(artifactKey, `${artifactKey}.bin`, "application/octet-stream")),
  );
  mockReviewArtifacts();
});

function seedManualChoiceCorrection(): void {
  correctionSessionRecorder.recordIntent({
    entry_id: "corr-choice-item-004",
    item_id: "item-004",
    item_type: "single_choice",
    kind: "manual_choice_answer_key",
    payload: {
      correct_choice_ids: ["choice-3"],
      interaction_id: "choice-item-004",
      submission_origin: "teacher_authored",
    },
    sequence: 4,
    source_binding: correctionSourceState().source_binding,
    source_item_fingerprint: "sha256:item-004",
    target: {
      interaction_id: "choice-item-004",
    },
  });
}

function withoutReplayArtifactReferences(result: ReturnType<typeof correctionApplyResult>) {
  return {
    ...result,
    answer_key_review_state: {
      ...result.answer_key_review_state,
      items: result.answer_key_review_state.items.map((item) => ({
        ...item,
        replay_artifact_references: [],
      })),
    },
  };
}

describe("ExamConverterAuthenticatedView corrected file actions", () => {
  it("maps producer reason codes to teacher-facing file copy without raw codes", () => {
    const wrapper = mount(ExamConverterFilesReadinessList, {
      props: {
        actionStates: {},
        actionsEnabled: true,
        actionNotice: null,
        files: [
          {
            artifactActionReference: null,
            artifactKey: "qti_package",
            availability: "unavailable",
            contentType: "application/zip",
            exportEnabled: false,
            filename: "Ma1c_QTI.zip",
            kindLabel: "QTI-format",
            reasonCode: "unsupported_target_shape",
            readiness: "unsupported_target_shape",
            sha256: null,
            sizeBytes: null,
            sizeLabel: null,
            statusLabel: "Kunde inte skapas",
            unavailableCode: "unsupported_target_shape",
          },
        ],
      },
    });

    expect(wrapper.text()).toContain(
      "Målfilen kunde inte skapas. Granska rapporten.",
    );
    expect(wrapper.text()).not.toContain("Orsak:");
    expect(wrapper.text()).not.toContain("unsupported_target_shape");
  });

  it("does not render the removed current-state export gate", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);

    expect(wrapper.find('[data-test="exam-converter-review-decision-gate"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-converter-accept-current-state-action"]').exists()).toBe(false);
    expect(wrapper.text()).not.toContain("Använd provet som det är");
    expect(wrapper.text()).not.toContain("Godkänn");
  });

  it("keeps replayed file actions disabled when replay gives no artifact reference", async () => {
    const replayResult = correctionApplyResult();
    gatewayMocks.applyExamAuthoringCorrections.mockResolvedValue(
      withoutReplayArtifactReferences(replayResult),
    );
    seedManualChoiceCorrection();
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    await wrapper.find('[data-test="exam-converter-inspection-tab-files"]').trigger("click");

    const downloadBefore = wrapper.find(
      '[data-test="exam-converter-download-file-examnet_pdf"]',
    );
    const saveBefore = wrapper.find('[data-test="exam-converter-save-file-examnet_pdf"]');
    expect(downloadBefore.attributes("disabled")).toBeDefined();
    expect(saveBefore.attributes("disabled")).toBeDefined();
    expect(wrapper.text()).toContain("Filer kunde inte skapas");

    await flushPromises();

    const pdfDownloadAfter = wrapper.find(
      '[data-test="exam-converter-download-file-examnet_pdf"]',
    );
    const qtiDownloadAfter = wrapper.find(
      '[data-test="exam-converter-download-file-qti_package"]',
    );
    const qtiSaveAfter = wrapper.find('[data-test="exam-converter-save-file-qti_package"]');
    expect(wrapper.text()).toContain("Filer kunde inte skapas");
    expect(pdfDownloadAfter.attributes("disabled")).toBeDefined();
    expect(qtiDownloadAfter.attributes("disabled")).toBeDefined();
    expect(qtiSaveAfter.attributes("disabled")).toBeDefined();
  });

  it("does not save a replayed generated file without a replay artifact reference", async () => {
    const replayResult = correctionApplyResult();
    gatewayMocks.applyExamAuthoringCorrections.mockResolvedValue(
      withoutReplayArtifactReferences(replayResult),
    );
    seedManualChoiceCorrection();
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    await flushPromises();
    await wrapper.find('[data-test="exam-converter-inspection-tab-files"]').trigger("click");
    const saveAction = wrapper.find('[data-test="exam-converter-save-file-qti_package"]');

    expect(saveAction.attributes("disabled")).toBeDefined();
    expect(gatewayMocks.saveDigiExamMigrationArtifactToUserFiles).not.toHaveBeenCalled();
    expect(gatewayMocks.downloadDigiExamMigrationArtifact).not.toHaveBeenCalledWith(
      expect.objectContaining({
        artifactKey: "qti_package",
        correlationId: "corr_exam_converter_files",
        jobId: "job_exam_converter_files",
      }),
    );
    expect(gatewayMocks.downloadDigiExamMigrationCorrectionReplayArtifact).not.toHaveBeenCalled();
  });

  it("uses a replay artifact reference when the correction replay result provides one", async () => {
    const replayResult = correctionApplyResult();
    gatewayMocks.applyExamAuthoringCorrections.mockResolvedValue({
      ...replayResult,
      target_readiness: {
        ...replayResult.target_readiness,
        targets: replayResult.target_readiness.targets.map((target) => ({
          ...target,
          artifact_key:
            target.target === "qti_package"
              ? "correction_replay_qti_package"
              : "correction_replay_examnet_pdf",
        })),
      },
    });
    seedManualChoiceCorrection();
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    await flushPromises();
    await wrapper.find('[data-test="exam-converter-inspection-tab-files"]').trigger("click");
    gatewayMocks.downloadDigiExamMigrationArtifact.mockClear();
    gatewayMocks.downloadDigiExamMigrationCorrectionReplayArtifact.mockClear();

    const saveAction = wrapper.find('[data-test="exam-converter-save-file-qti_package"]');
    expect(saveAction.attributes("disabled")).toBeUndefined();
    await saveAction.trigger("click");
    await flushPromises();

    expect(gatewayMocks.downloadDigiExamMigrationArtifact).not.toHaveBeenCalled();
    expect(gatewayMocks.downloadDigiExamMigrationCorrectionReplayArtifact).toHaveBeenCalledWith(
      expect.objectContaining({
        artifactKey: "correction_replay_qti_package",
        artifactSetId: "job_correction_replay-artifact-set-qti",
        contentSha256: "sha256:job_correction_replay-qti",
        correlationId: "corr_exam_converter_files",
        jobId: "job_correction_replay",
      }),
    );
    expect(gatewayMocks.saveDigiExamMigrationArtifactToUserFiles).toHaveBeenCalledWith(
      expect.objectContaining({
        artifact: expect.objectContaining({
          artifact_key: "correction_replay_qti_package",
        }),
      }),
    );
  });

  it("clears corrected file state when local choices are reset", async () => {
    seedManualChoiceCorrection();
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    await flushPromises();
    await wrapper.find('[data-test="exam-converter-inspection-tab-files"]').trigger("click");
    expect(
      wrapper.find('[data-test="exam-converter-download-file-qti_package"]').attributes(
        "disabled",
      ),
    ).toBeUndefined();

    await wrapper.find('[data-test="exam-converter-reset-local-choices"]').trigger("click");

    expect(wrapper.find('[data-test="exam-converter-source-drop-zone"]').exists()).toBe(true);
  });
});
