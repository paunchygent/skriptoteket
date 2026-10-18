/**
 * Public Exam Converter view tests.
 *
 * These tests cover the anonymous browser workflow against the app-hosted
 * public runtime API without involving auth stores, CSRF, or protected routes.
 */

import { flushPromises, mount, type VueWrapper } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ExamConverterPublicView from "./ExamConverterPublicView.vue";
import { STATUS_POLL_INTERVAL_MS } from "./exam-converter-public/usePublicExamConverterRuntime";

const clientMocks = vi.hoisted(() => ({
  isApiError: vi.fn(),
  publicApiFetchBlobResponse: vi.fn(),
  publicApiGet: vi.fn(),
  publicApiPost: vi.fn(),
}));

vi.mock("../../api/client", () => ({
  isApiError: clientMocks.isApiError,
  publicApiFetchBlobResponse: clientMocks.publicApiFetchBlobResponse,
  publicApiGet: clientMocks.publicApiGet,
  publicApiPost: clientMocks.publicApiPost,
}));

function mockFileInput(input: Element, files: File[]): void {
  Object.defineProperty(input, "files", {
    configurable: true,
    value: files,
  });
}

async function chooseFile(
  selector: string,
  file: File,
  wrapper: VueWrapper,
): Promise<void> {
  const input = wrapper.find<HTMLInputElement>(selector);
  mockFileInput(input.element, [file]);
  await input.trigger("change");
}

const JOB_URL = "/api/v1/public/apps/documents.conversion_hub/exam-converter/jobs/public-job-1";

const QUEUED_SUBMIT = {
  public_job_id: "public-job-1",
  status: "queued",
  requested_targets: ["examnet_pdf", "qti_package"],
  expires_at: "2026-10-18T13:00:00Z",
  poll_url: JOB_URL,
  result_url: `${JOB_URL}/result`,
  artifact_manifest_url: `${JOB_URL}/artifacts`,
};

function statusResponse(status: string, error: string | null = null) {
  return {
    public_job_id: "public-job-1",
    status,
    expires_at: "2026-10-18T13:00:00Z",
    error,
  };
}

function unavailableTarget(artifactKey: string, filename: string) {
  return {
    artifact_key: artifactKey,
    filename,
    content_type: "application/octet-stream",
    availability: "unavailable",
    size_bytes: null,
    sha256: null,
    download_url: null,
    unavailable_code: "manual_answer_key_required",
  };
}

// Shape observed from the guest worker path for 1776888013-ak7-lag-och-ratt.dxe.
const NEEDS_REVIEW_MANIFEST = {
  public_job_id: "public-job-1",
  status: "succeeded",
  bundle_status: "needs_review",
  artifacts: [
    unavailableTarget("qti_package", "examnet-qti.zip"),
    unavailableTarget("examnet_pdf", "examnet-import.pdf"),
    unavailableTarget("qti_validation_report", "qti-validation-report.json"),
    {
      artifact_key: "target_readiness_report",
      filename: "target-readiness-report.json",
      content_type: "application/json",
      availability: "available",
      size_bytes: 10,
      sha256: "sha256:readiness",
      download_url: `${JOB_URL}/artifacts/target_readiness_report/download`,
      unavailable_code: null,
    },
  ],
  manual_follow_up: { required: true, artifact_key: "target_readiness_report", count: 12 },
  warnings: null,
};

async function submitDxe(wrapper: VueWrapper): Promise<void> {
  await chooseFile(
    'input[accept=".dxe"]',
    new File(["{}"], "exam.dxe", { type: "application/octet-stream" }),
    wrapper,
  );
  await wrapper.find("form").trigger("submit");
  await flushPromises();
}

async function advancePoll(): Promise<void> {
  await vi.advanceTimersByTimeAsync(STATUS_POLL_INTERVAL_MS);
  await flushPromises();
}

describe("ExamConverterPublicView", () => {
  beforeEach(() => {
    clientMocks.isApiError.mockReset();
    clientMocks.isApiError.mockReturnValue(false);
    clientMocks.publicApiFetchBlobResponse.mockReset();
    clientMocks.publicApiGet.mockReset();
    clientMocks.publicApiPost.mockReset();
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: vi.fn(() => "blob:exam-converter"),
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: vi.fn(),
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("uses the public Provhantering lane label instead of the compatibility-shell name", () => {
    const wrapper = mount(ExamConverterPublicView);

    expect(wrapper.text()).toContain("Provhantering");
    expect(wrapper.get("h1").text()).toBe("Exam Converter");
  });

  it("submits a public multipart job and renders available artifacts", async () => {
    clientMocks.publicApiPost.mockResolvedValue({
      public_job_id: "public-job-1",
      status: "succeeded",
      requested_targets: ["examnet_pdf"],
      expires_at: "2026-05-13T13:00:00Z",
      poll_url:
        "/api/v1/public/apps/documents.conversion_hub/exam-converter/jobs/public-job-1",
      result_url:
        "/api/v1/public/apps/documents.conversion_hub/exam-converter/jobs/public-job-1/result",
      artifact_manifest_url:
        "/api/v1/public/apps/documents.conversion_hub/exam-converter/jobs/public-job-1/artifacts",
    });
    clientMocks.publicApiGet
      .mockResolvedValueOnce({
        public_job_id: "public-job-1",
        status: "succeeded",
        expires_at: "2026-05-13T13:00:00Z",
        error: null,
      })
      .mockResolvedValueOnce({
        public_job_id: "public-job-1",
        status: "succeeded",
        bundle_status: "complete",
        artifacts: [
          {
            artifact_key: "examnet_pdf",
            filename: "examnet-import.pdf",
            content_type: "application/pdf",
            availability: "available",
            size_bytes: 3,
            sha256: "sha256:pdf",
            download_url:
              "/api/v1/public/apps/documents.conversion_hub/exam-converter/jobs/public-job-1/artifacts/examnet_pdf/download",
            unavailable_code: null,
          },
        ],
        manual_follow_up: null,
        warnings: null,
      });

    const wrapper = mount(ExamConverterPublicView);
    await chooseFile(
      'input[accept=".dxe"]',
      new File(["{}"], "exam.dxe", { type: "application/octet-stream" }),
      wrapper,
    );
    await wrapper.find("form").trigger("submit");
    await vi.dynamicImportSettled();

    expect(clientMocks.publicApiPost).toHaveBeenCalledWith(
      "/api/v1/public/apps/documents.conversion_hub/exam-converter/jobs",
      expect.any(FormData),
    );
    const submittedForm = clientMocks.publicApiPost.mock.calls[0]?.[1] as FormData;
    expect(submittedForm.get("source_dxe")).toBeInstanceOf(File);
    expect(submittedForm.get("targets_json")).toBe('["examnet_pdf","qti_package"]');
    expect(wrapper.text()).toContain("public-job-1");
    expect(wrapper.text()).toContain("examnet-import.pdf");
    expect(wrapper.text()).toContain("1 fil(er) redo att hämta.");
  });

  it("downloads an available artifact through the public backend URL", async () => {
    clientMocks.publicApiPost.mockResolvedValue({
      public_job_id: "public-job-1",
      status: "succeeded",
      requested_targets: ["examnet_pdf"],
      expires_at: "2026-05-13T13:00:00Z",
      poll_url:
        "/api/v1/public/apps/documents.conversion_hub/exam-converter/jobs/public-job-1",
      result_url:
        "/api/v1/public/apps/documents.conversion_hub/exam-converter/jobs/public-job-1/result",
      artifact_manifest_url:
        "/api/v1/public/apps/documents.conversion_hub/exam-converter/jobs/public-job-1/artifacts",
    });
    clientMocks.publicApiGet
      .mockResolvedValueOnce({
        public_job_id: "public-job-1",
        status: "succeeded",
        expires_at: "2026-05-13T13:00:00Z",
        error: null,
      })
      .mockResolvedValueOnce({
        public_job_id: "public-job-1",
        status: "succeeded",
        bundle_status: "complete",
        artifacts: [
          {
            artifact_key: "examnet_pdf",
            filename: "examnet-import.pdf",
            content_type: "application/pdf",
            availability: "available",
            size_bytes: 3,
            sha256: "sha256:pdf",
            download_url:
              "/api/v1/public/apps/documents.conversion_hub/exam-converter/jobs/public-job-1/artifacts/examnet_pdf/download",
            unavailable_code: null,
          },
        ],
        manual_follow_up: null,
        warnings: null,
      });
    clientMocks.publicApiFetchBlobResponse.mockResolvedValue({
      blob: new Blob(["pdf"], { type: "application/pdf" }),
      contentType: "application/pdf",
      filename: "examnet-import.pdf",
    });

    const wrapper = mount(ExamConverterPublicView);
    await chooseFile(
      'input[accept=".dxe"]',
      new File(["{}"], "exam.dxe", { type: "application/octet-stream" }),
      wrapper,
    );
    await wrapper.find("form").trigger("submit");
    await vi.dynamicImportSettled();
    await wrapper.find(".exam-converter__download").trigger("click");

    expect(clientMocks.publicApiFetchBlobResponse).toHaveBeenCalledWith(
      "/api/v1/public/apps/documents.conversion_hub/exam-converter/jobs/public-job-1/artifacts/examnet_pdf/download",
    );
  });

  it("polls a queued job until it succeeds and then stops polling", async () => {
    vi.useFakeTimers();
    clientMocks.publicApiPost.mockResolvedValue(QUEUED_SUBMIT);
    clientMocks.publicApiGet
      .mockResolvedValueOnce(statusResponse("queued"))
      .mockResolvedValueOnce(statusResponse("processing"))
      .mockResolvedValueOnce(statusResponse("succeeded"))
      .mockResolvedValueOnce(NEEDS_REVIEW_MANIFEST);

    const wrapper = mount(ExamConverterPublicView);
    await submitDxe(wrapper);

    expect(clientMocks.publicApiGet).toHaveBeenCalledTimes(1);
    expect(wrapper.text()).toContain("Väntar på färdiga filer.");

    await advancePoll();
    expect(clientMocks.publicApiGet).toHaveBeenCalledTimes(2);

    await advancePoll();
    expect(clientMocks.publicApiGet).toHaveBeenCalledTimes(4);
    expect(clientMocks.publicApiGet).toHaveBeenLastCalledWith(`${JOB_URL}/artifacts`);
    expect(wrapper.text()).not.toContain("Väntar på färdiga filer.");

    await advancePoll();
    await advancePoll();
    expect(clientMocks.publicApiGet).toHaveBeenCalledTimes(4);
  });

  it("shows a final needs-answer-key state instead of waiting for files", async () => {
    vi.useFakeTimers();
    clientMocks.publicApiPost.mockResolvedValue(QUEUED_SUBMIT);
    clientMocks.publicApiGet
      .mockResolvedValueOnce(statusResponse("succeeded"))
      .mockResolvedValueOnce(NEEDS_REVIEW_MANIFEST);

    const wrapper = mount(ExamConverterPublicView);
    await submitDxe(wrapper);

    const notice = wrapper.get(".exam-converter__needs-answer-key");
    expect(notice.text()).toContain("Exam.net PDF och QTI-paket kunde inte skapas.");
    expect(notice.text()).toContain("saknar facit");
    expect(notice.text()).toContain("resultat-PDF:en från DigiExam");
    expect(wrapper.text()).not.toContain("Väntar på färdiga filer.");
    expect(wrapper.get("header [data-state]").text()).toBe("Facit saknas");
    expect(wrapper.get("header [data-state]").classes()).not.toContain("text-success");

    const rows = wrapper.findAll("li");
    const pdfRow = rows.find((row) => row.text().includes("examnet-import.pdf"));
    expect(pdfRow?.text()).toContain("Kunde inte skapas");
    expect(pdfRow?.text()).toContain("Facit saknas i provfilen.");
    expect(pdfRow?.find(".exam-converter__download").exists()).toBe(false);
    expect(wrapper.text()).not.toContain("Status okänd");

    await advancePoll();
    expect(clientMocks.publicApiGet).toHaveBeenCalledTimes(2);
  });

  it("does not keep waiting when the manifest request fails after success", async () => {
    vi.useFakeTimers();
    clientMocks.publicApiPost.mockResolvedValue(QUEUED_SUBMIT);
    clientMocks.publicApiGet
      .mockResolvedValueOnce(statusResponse("succeeded"))
      .mockRejectedValueOnce(new Error("network"));

    const wrapper = mount(ExamConverterPublicView);
    await submitDxe(wrapper);

    expect(wrapper.text()).toContain("Konverteringen kunde inte genomföras. Försök igen.");
    expect(wrapper.text()).not.toContain("Väntar på färdiga filer.");
  });

  it("stops polling and stops waiting when the job fails", async () => {
    vi.useFakeTimers();
    clientMocks.publicApiPost.mockResolvedValue(QUEUED_SUBMIT);
    clientMocks.publicApiGet
      .mockResolvedValueOnce(statusResponse("processing"))
      .mockResolvedValueOnce(
        statusResponse("failed", "Konverteringen kunde inte genomföras. Försök igen."),
      );

    const wrapper = mount(ExamConverterPublicView);
    await submitDxe(wrapper);
    await advancePoll();

    expect(wrapper.text()).toContain("Konverteringen stannade.");
    expect(wrapper.text()).not.toContain("Väntar på färdiga filer.");

    await advancePoll();
    expect(clientMocks.publicApiGet).toHaveBeenCalledTimes(2);
  });

  it("stops polling when the view unmounts", async () => {
    vi.useFakeTimers();
    clientMocks.publicApiPost.mockResolvedValue(QUEUED_SUBMIT);
    clientMocks.publicApiGet.mockResolvedValue(statusResponse("processing"));

    const wrapper = mount(ExamConverterPublicView);
    await submitDxe(wrapper);
    wrapper.unmount();
    await advancePoll();

    expect(clientMocks.publicApiGet).toHaveBeenCalledTimes(1);
  });
});
