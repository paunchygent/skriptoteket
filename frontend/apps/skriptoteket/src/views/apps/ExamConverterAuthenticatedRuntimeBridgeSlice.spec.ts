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

const gatewayMocks = vi.hoisted(() => ({
  getDigiExamMigrationJob: vi.fn(),
  getDigiExamMigrationResult: vi.fn(),
  submitDigiExamMigration: vi.fn(),
}));

vi.mock("../../api/sirConvertGateway", () => ({
  getDigiExamMigrationJob: gatewayMocks.getDigiExamMigrationJob,
  getDigiExamMigrationResult: gatewayMocks.getDigiExamMigrationResult,
  submitDigiExamMigration: gatewayMocks.submitDigiExamMigration,
}));

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
      bundle_schema_version: "digiexam_migration_bundle_v1",
      bundle_status: "complete",
      manual_follow_up_required: false,
      route_key: "digiexam_dxe_to_examnet_migration_bundle",
      source_sha256: "sha256:source",
      target_availability: {
        examnet_pdf: "available",
        qti_package: "available",
      },
      warning_count: 0,
      ...overrides,
    },
    job: {
      jobId: "job_exam_converter_1",
      status: "succeeded",
    },
  };
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
  gatewayMocks.getDigiExamMigrationJob.mockReset();
  gatewayMocks.getDigiExamMigrationResult.mockReset();
  gatewayMocks.submitDigiExamMigration.mockReset();
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
    expect(wrapper.text()).not.toContain("Konverterade frågor");
    expect(wrapper.text()).not.toContain("Filer klara att hämta");
    expect(wrapper.text()).not.toContain("Rapport");
  });

  it("polls queued jobs with the returned correlation ID before reading the result", async () => {
    vi.useFakeTimers();
    gatewayMocks.submitDigiExamMigration.mockResolvedValueOnce(submittedJob("queued"));
    gatewayMocks.getDigiExamMigrationJob
      .mockResolvedValueOnce({ jobId: "job_exam_converter_1", status: "processing" })
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

  it("maps partial terminal results to teacher action copy without inventing question counts", async () => {
    gatewayMocks.submitDigiExamMigration.mockResolvedValueOnce(submittedJob("succeeded"));
    gatewayMocks.getDigiExamMigrationResult.mockResolvedValueOnce(
      terminalResult({
        bundle_status: "partial",
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
    expect(wrapper.text()).toContain("Några frågor behöver ses över innan provet är klart.");
    expect(wrapper.text()).not.toContain("3 frågor");
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
