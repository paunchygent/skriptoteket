/**
 * Public Exam Converter view tests.
 *
 * These tests cover the anonymous browser workflow against the app-hosted
 * public runtime API without involving auth stores, CSRF, or protected routes.
 */

import { mount, type VueWrapper } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ExamConverterPublicView from "./ExamConverterPublicView.vue";

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
        status: "succeeded",
        artifacts: [
          {
            artifact_key: "examnet_pdf",
            filename: "examnet-import.pdf",
            content_type: "application/pdf",
            availability: "available",
            download_url:
              "/api/v1/public/apps/documents.conversion_hub/exam-converter/jobs/public-job-1/artifacts/examnet_pdf/download",
            blocker_code: null,
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
        status: "succeeded",
        artifacts: [
          {
            artifact_key: "examnet_pdf",
            filename: "examnet-import.pdf",
            content_type: "application/pdf",
            availability: "available",
            download_url:
              "/api/v1/public/apps/documents.conversion_hub/exam-converter/jobs/public-job-1/artifacts/examnet_pdf/download",
            blocker_code: null,
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
});
