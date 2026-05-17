/**
 * Exam Converter authenticated runtime-bridge slice behavior.
 *
 * Slice purpose:
 *   Connect the approved local intake and conversion-start surface to the
 *   authenticated HuleEdu Gateway submit, status, and terminal-result calls.
 *
 * Expected behavior:
 *   The teacher can start exactly one selected exam conversion. The browser
 *   submits the `.dxe`, optional corrected PDF, Swedish artifact language, and
 *   declared target formats through the Gateway client, polls with the returned
 *   correlation ID, and maps the terminal result to the compact result strip.
 *
 * Recommended implementation shape:
 *   Keep transport in the existing Gateway client, keep submit/poll orchestration
 *   in a small runtime composable, and keep the view as a thin coordinator. Do
 *   not introduce question rows, file rows, reports, downloads, or save actions
 *   in this slice.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ExamConverterAuthenticatedView from "./ExamConverterAuthenticatedView.vue";
import type {
  SirConvertJobStatus,
  SirConvertSubmittedJob,
  SirConvertTerminalResult,
} from "../../api/sirConvertGateway";
import { DIGIEXAM_ARTIFACT_ANSWER_KEY_COMPLETION_REPORT } from "../../api/sirConvertGateway/contractValues";
import {
  ANSWER_KEY_COMPLETION_REPORT_SCHEMA_VERSION,
  DIGIEXAM_EFFECTIVE_EXAM_SCHEMA_VERSION,
  DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
  DIGIEXAM_IR_MANIFEST_SCHEMA_VERSION,
  DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
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

function submittedJob(status: SirConvertJobStatus): SirConvertSubmittedJob {
  return {
    idempotentReplay: false,
    jobId: "job_exam_converter_1",
    requestContext: {
      correlationId: "corr_exam_converter_1",
      idempotencyKey: "idem_exam_converter_1",
      jobSpec: {} as SirConvertSubmittedJob["requestContext"]["jobSpec"],
    },
    status,
  };
}

function terminalResult(
  overrides: Partial<SirConvertTerminalResult["conversion_metadata"]> = {},
): SirConvertTerminalResult {
  return {
    artifact: {
      content_type: "application/json",
      filename: "exam-converter-result.json",
      sha256: "sha256:abc",
      size_bytes: 1024,
    },
    conversion_metadata: {
      artifact_count: 2,
      bundle_schema_version: DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
      bundle_status: "complete",
      manual_follow_up_required: false,
      route_key: "digiexam_dxe_to_examnet_migration_bundle",
      source_sha256: "sha256:source",
      target_readiness_report_artifact_key: "target_readiness_report",
      warning_count: 0,
      ...overrides,
    },
    job: {
      jobId: "job_exam_converter_1",
      status: "succeeded",
    },
  };
}

function artifactJsonBlob(artifactKey: string, payload: unknown) {
  return {
    artifactKey,
    blob: {
      text: () => Promise.resolve(JSON.stringify(payload)),
    } as Blob,
    contentType: "application/json",
    filename: `${artifactKey}.json`,
  };
}

function reviewItem(overrides: Record<string, unknown> = {}) {
  return {
    answer_key: { provenance: "dxe_populated_key" },
    item_id: "item-001",
    item_type: "multiple_choice",
    max_score: 1,
    prompt_html: null,
    prompt_lines: ["Beräkna värdet."],
    sequence: 1,
    title: "Beräkna värdet.",
    warnings: [],
    ...overrides,
  };
}

function mockReviewArtifacts(options: { requiresReview?: boolean } = {}): void {
  const requiresReview = options.requiresReview ?? false;
  gatewayMocks.listDigiExamMigrationArtifacts.mockResolvedValue({
    artifacts: [
      {
        artifact_key: "examnet_pdf",
        availability: "available",
        content_type: "application/pdf",
        filename: "Ma1c_Exam.net.pdf",
        sha256: null,
        size_bytes: 684 * 1024,
      },
      {
        artifact_key: "qti_package",
        availability: "available",
        content_type: "application/zip",
        filename: "Ma1c_QTI.zip",
        sha256: null,
        size_bytes: 1_200_000,
      },
      {
        artifact_key: DIGIEXAM_ARTIFACT_ANSWER_KEY_COMPLETION_REPORT,
        availability: "available",
        content_type: "application/json",
        filename: "answer-key-completion-report.json",
        sha256: "sha256:completion-report-runtime",
        size_bytes: 512,
      },
    ],
    bundle_status: "partial",
    job_id: "job_exam_converter_1",
    source: {
      filename: "Ma1c_NationelltProv_HT25.dxe",
      format: "digiexam_dxe",
      sha256: "sha256:source",
    },
    manual_follow_up: {
      artifact_key: "manual_follow_up_report",
      count: requiresReview ? 1 : 0,
      required: requiresReview,
    },
    schema_version: DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
    warnings: {
      artifact_key: "warnings_report",
      count: 0,
    },
    readiness: {
      artifact_key: "target_readiness_report",
      exportable_targets: requiresReview ? [] : ["examnet_pdf", "qti_package"],
      review_required: requiresReview,
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
              reviewItem(),
              reviewItem({
                answer_key: { provenance: requiresReview ? "absent" : "dxe_populated_key" },
                item_id: "item-002",
                max_score: 1,
                prompt_lines: ["Vilket av följande tal är ett primtal?"],
                sequence: 2,
                title: "Vilket av följande tal är ett primtal?",
              }),
            ],
            manual_follow_ups: requiresReview
              ? [
                  {
                    item_id: "item-002",
                    message: "Manual answer key is required.",
                    reason: "manual_answer_key_required",
                    source_span: null,
                  },
                ]
              : [],
            parse_status: "success",
            renderer_ready: true,
            schema_version: DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
            source_filename: "Ma1c_NationelltProv_HT25.dxe",
            source_producer: null,
            warnings: [],
          }),
        );
      }
      if (artifactKey === "target_readiness_report") {
        return Promise.resolve(
          artifactJsonBlob("target_readiness_report", {
            schema_version: TARGET_READINESS_REPORT_SCHEMA_VERSION,
            job_id: "job_exam_converter_1",
            source_ir_sha256: "sha256:ir",
            effective_exam_sha256: "sha256:effective",
            targets: [
              {
                target: "examnet_pdf",
                readiness: requiresReview ? "needs_teacher_answer_key" : "ready",
                export_enabled: !requiresReview,
                artifact_key: requiresReview ? null : "examnet_pdf",
                reason_code: requiresReview ? "manual_answer_key_required" : "target_available",
                teacher_action: requiresReview ? "supply_answer_key_overlay" : "none",
                retryable: false,
                message_key: requiresReview
                  ? "exam_converter.target.needs_teacher_answer_key"
                  : "exam_converter.target.ready",
                item_id: requiresReview ? "item-002" : null,
                sequence: requiresReview ? 2 : null,
                source_item_fingerprint: requiresReview ? "sha256:item-002" : null,
              },
              {
                target: "qti_package",
                readiness: requiresReview ? "needs_teacher_answer_key" : "ready",
                export_enabled: !requiresReview,
                artifact_key: requiresReview ? null : "qti_package",
                reason_code: requiresReview ? "manual_answer_key_required" : "target_available",
                teacher_action: requiresReview ? "supply_answer_key_overlay" : "none",
                retryable: false,
                message_key: requiresReview
                  ? "exam_converter.target.needs_teacher_answer_key"
                  : "exam_converter.target.ready",
                item_id: requiresReview ? "item-002" : null,
                sequence: requiresReview ? 2 : null,
                source_item_fingerprint: requiresReview ? "sha256:item-002" : null,
              },
            ],
          }),
        );
      }
      if (artifactKey === DIGIEXAM_ARTIFACT_ANSWER_KEY_COMPLETION_REPORT) {
        return Promise.resolve(
          artifactJsonBlob(DIGIEXAM_ARTIFACT_ANSWER_KEY_COMPLETION_REPORT, {
            schema_version: ANSWER_KEY_COMPLETION_REPORT_SCHEMA_VERSION,
            completion_mode: "local_llm_suggest_missing_machine_marked",
            job_id: "job_exam_converter_1",
            items: [
              {
                item_id: "item-002",
                sequence: 2,
                item_type: "multiple_choice",
                decision_state: requiresReview ? "manual_follow_up_required" : "skipped",
                validation_state: requiresReview ? "manual_follow_up_required" : "skipped",
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
      return Promise.resolve(
        artifactJsonBlob("migration_manifest", {
          asset_count: 0,
          asset_summaries: [],
          exam_schema_version: DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
          item_count: 2,
          item_summaries: [
            {
              item_id: "item-001",
              sequence: 1,
              title: "Beräkna värdet.",
              item_type: "multiple_choice",
              source_item_fingerprint: "sha256:item-001",
              answer_key_provenance: "dxe_populated_key",
              manual_follow_up_required: false,
              asset_summaries: [],
            },
            {
              item_id: "item-002",
              sequence: 2,
              title: "Vilket av följande tal är ett primtal?",
              item_type: "multiple_choice",
              source_item_fingerprint: "sha256:item-002",
              answer_key_provenance: requiresReview ? "absent" : "dxe_populated_key",
              manual_follow_up_required: requiresReview,
              asset_summaries: [],
            },
          ],
          manual_follow_up_count: requiresReview ? 1 : 0,
          parse_status: "success",
          renderer_ready: true,
          schema_version: DIGIEXAM_IR_MANIFEST_SCHEMA_VERSION,
          source_filename: "Ma1c_NationelltProv_HT25.dxe",
          source_producer: null,
          warning_count: 0,
        }),
      );
    },
  );
}

async function chooseFile(wrapper: ReturnType<typeof mount>, selector: string, file: File) {
  const input = wrapper.find<HTMLInputElement>(selector);
  Object.defineProperty(input.element, "files", {
    configurable: true,
    value: [file],
  });
  await input.trigger("change");
}

async function chooseSourceFile(wrapper: ReturnType<typeof mount>, file: File) {
  await chooseFile(wrapper, '[data-test="exam-converter-source-file-input"]', file);
}

async function chooseSupportingFile(wrapper: ReturnType<typeof mount>, file: File) {
  await chooseFile(wrapper, '[data-test="exam-converter-supporting-file-input"]', file);
}

function startButton(wrapper: ReturnType<typeof mount>) {
  return wrapper.find('[data-test="exam-converter-start-conversion"]');
}

beforeEach(() => {
  gatewayMocks.downloadDigiExamMigrationArtifact.mockReset();
  gatewayMocks.getDigiExamMigrationJob.mockReset();
  gatewayMocks.getDigiExamMigrationResult.mockReset();
  gatewayMocks.listDigiExamMigrationArtifacts.mockReset();
  gatewayMocks.saveDigiExamMigrationArtifactToUserFiles.mockReset();
  gatewayMocks.submitDigiExamMigration.mockReset();
  mockReviewArtifacts();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("ExamConverterAuthenticatedView runtime bridge slice", () => {
  it("submits selected files and declared target formats through the Gateway client", async () => {
    gatewayMocks.submitDigiExamMigration.mockResolvedValueOnce(submittedJob("succeeded"));
    gatewayMocks.getDigiExamMigrationResult.mockResolvedValueOnce(terminalResult());
    const wrapper = mount(ExamConverterAuthenticatedView);

    await chooseSourceFile(
      wrapper,
      new File(["exam"], "Ma1c_NationelltProv_HT25.dxe", {
        type: "application/octet-stream",
      }),
    );
    await chooseSupportingFile(
      wrapper,
      new File(["answers"], "Ma1c_HT25_Rattat_prov.pdf", {
        type: "application/pdf",
      }),
    );
    await startButton(wrapper).trigger("click");
    await flushPromises();

    expect(gatewayMocks.submitDigiExamMigration).toHaveBeenCalledWith({
      artifactLanguage: "sv",
      completionMode: "local_llm_suggest_missing_machine_marked",
      file: expect.objectContaining({ name: "Ma1c_NationelltProv_HT25.dxe" }),
      gradedResultPdf: expect.objectContaining({ name: "Ma1c_HT25_Rattat_prov.pdf" }),
      targets: ["examnet_pdf", "qti_package"],
      waitSeconds: 0,
    });
    expect(gatewayMocks.getDigiExamMigrationResult).toHaveBeenCalledWith({
      correlationId: "corr_exam_converter_1",
      jobId: "job_exam_converter_1",
    });
    expect(wrapper.text()).toContain("Provet är konverterat");
    expect(wrapper.text()).toContain("Frågor (2)");
    expect(wrapper.text()).toContain("Filer (2)");
    expect(wrapper.text()).toContain("Rapport");
    expect(wrapper.text()).not.toContain("Spara i mina filer");
  });

  it("polls queued jobs with the returned correlation ID before reading the result", async () => {
    vi.useFakeTimers();
    gatewayMocks.submitDigiExamMigration.mockResolvedValueOnce(submittedJob("queued"));
    gatewayMocks.getDigiExamMigrationJob
      .mockResolvedValueOnce({ jobId: "job_exam_converter_1", status: "running" })
      .mockResolvedValueOnce({ jobId: "job_exam_converter_1", status: "succeeded" });
    gatewayMocks.getDigiExamMigrationResult.mockResolvedValueOnce(terminalResult());
    const wrapper = mount(ExamConverterAuthenticatedView);

    await chooseSourceFile(
      wrapper,
      new File(["exam"], "Ma1c_NationelltProv_HT25.dxe", {
        type: "application/octet-stream",
      }),
    );
    await startButton(wrapper).trigger("click");
    await flushPromises();

    expect(gatewayMocks.getDigiExamMigrationJob).not.toHaveBeenCalled();

    await vi.advanceTimersByTimeAsync(2_000);
    await flushPromises();
    expect(gatewayMocks.getDigiExamMigrationJob).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(2_000);
    await flushPromises();
    expect(gatewayMocks.getDigiExamMigrationJob).toHaveBeenCalledTimes(2);
    expect(gatewayMocks.getDigiExamMigrationJob).toHaveBeenLastCalledWith({
      correlationId: "corr_exam_converter_1",
      jobId: "job_exam_converter_1",
    });
    expect(gatewayMocks.getDigiExamMigrationResult).toHaveBeenCalledWith({
      correlationId: "corr_exam_converter_1",
      jobId: "job_exam_converter_1",
    });
    expect(wrapper.text()).toContain("Provet är konverterat");
    wrapper.unmount();
  });

  it("maps partial terminal results to artifact-backed teacher action copy", async () => {
    mockReviewArtifacts({ requiresReview: true });
    gatewayMocks.submitDigiExamMigration.mockResolvedValueOnce(submittedJob("succeeded"));
    gatewayMocks.getDigiExamMigrationResult.mockResolvedValueOnce(
      terminalResult({
        bundle_status: "needs_review",
        manual_follow_up_required: true,
        warning_count: 3,
      }),
    );
    const wrapper = mount(ExamConverterAuthenticatedView);

    await chooseSourceFile(
      wrapper,
      new File(["exam"], "Ma1c_NationelltProv_HT25.dxe", {
        type: "application/octet-stream",
      }),
    );
    await startButton(wrapper).trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("Konverteringen av provet lyckades delvis");
    expect(wrapper.text()).toContain("1 fråga saknar facit eller poäng.");
    expect(wrapper.text()).not.toContain("Sir Convert");
  });

  it("maps failed terminal jobs to the failure strip without exposing upstream details", async () => {
    gatewayMocks.submitDigiExamMigration.mockResolvedValueOnce(submittedJob("failed"));
    const wrapper = mount(ExamConverterAuthenticatedView);

    await chooseSourceFile(
      wrapper,
      new File(["exam"], "Ma1c_NationelltProv_HT25.dxe", {
        type: "application/octet-stream",
      }),
    );
    await startButton(wrapper).trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("Konverteringen av provet misslyckades");
    expect(wrapper.text()).toContain("Kontrollera provfilen och försök igen.");
    expect(wrapper.text()).not.toContain("Exam Converter job did not finish");
    expect(gatewayMocks.getDigiExamMigrationResult).not.toHaveBeenCalled();
  });
});
