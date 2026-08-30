import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  downloadLocalExamConversionArtifact,
  getLocalExamConversionResult,
  replayLocalExamConversion,
  submitLocalExamConversion,
} from "./examConverterLocal";

const clientMocks = vi.hoisted(() => ({
  apiFetch: vi.fn(),
  apiFetchBlobResponse: vi.fn(),
  apiGet: vi.fn(),
  apiPost: vi.fn(),
}));
vi.mock("./client", () => clientMocks);

describe("Skriptoteket-owned Exam Converter API", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("submits binary sources directly with byte-derived idempotency", async () => {
    clientMocks.apiFetch.mockResolvedValue({
      error: null,
      idempotent_replay: false,
      job_id: "local-job-1",
      status: "submitted",
    });
    const firstFile = new File([new Uint8Array([0x80])], "prov.dxe", { type: "application/octet-stream" });
    const sameBytesFile = new File([new Uint8Array([0x80])], "prov.dxe", { type: "application/octet-stream" });
    const distinctBytesFile = new File([new Uint8Array([0x81])], "prov.dxe", { type: "application/octet-stream" });

    const result = await submitLocalExamConversion({ file: firstFile });
    const sameBytesResult = await submitLocalExamConversion({ file: sameBytesFile });
    const distinctBytesResult = await submitLocalExamConversion({ file: distinctBytesFile });

    expect(clientMocks.apiFetch).toHaveBeenCalledWith(
      "/api/v1/apps/documents.conversion_hub/exam-converter/conversions",
      expect.objectContaining({ body: expect.any(FormData), method: "POST" }),
    );
    expect(result.jobId).toBe("local-job-1");
    const request = clientMocks.apiFetch.mock.calls[0]?.[1] as { body: FormData };
    expect(request.body.get("idempotency_key")).toMatch(/^exam-converter-/);
    expect(result.idempotencyKey).toBe(sameBytesResult.idempotencyKey);
    expect(result.idempotencyKey).not.toBe(distinctBytesResult.idempotencyKey);
    expect(result.idempotentReplay).toBe(false);
  });

  it("reads terminal state, replay, and artifacts from local job identity", async () => {
    clientMocks.apiGet.mockResolvedValue({
      artifact_count: 9,
      bundle_status: "complete",
      error: null,
      job_id: "local-job-1",
      manual_follow_up_required: false,
      status: "succeeded",
      warning_count: 0,
    });
    clientMocks.apiPost.mockResolvedValue({ job_id: "local-job-1" });
    clientMocks.apiFetchBlobResponse.mockResolvedValue({
      blob: new Blob(["pdf"]),
      contentType: "application/pdf",
      filename: "examnet-import.pdf",
    });

    const result = await getLocalExamConversionResult({ jobId: "local-job-1" });
    await replayLocalExamConversion({ jobId: "local-job-1" });
    const artifact = await downloadLocalExamConversionArtifact({
      artifactKey: "examnet_pdf",
      jobId: "local-job-1",
    });

    expect(result.job.jobId).toBe("local-job-1");
    expect(clientMocks.apiPost).toHaveBeenCalledWith(
      "/api/v1/apps/documents.conversion_hub/exam-converter/jobs/local-job-1/replay",
    );
    expect(artifact.filename).toBe("examnet-import.pdf");
    expect(JSON.stringify(clientMocks)).not.toContain("/sir-convert/");
  });
});
