import { beforeEach, describe, expect, it, vi } from "vitest";

import { replaceExamConverterCorrectionIntents } from "./examConverterCorrectionSessions";

const clientMocks = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPut: vi.fn(),
}));
vi.mock("./client", () => clientMocks);

describe("Exam Converter correction-session API", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("sends every intent in one persisted request", async () => {
    const request = {
      expected_session_version: 3,
      intents: [{ entry_id: "one" }, { entry_id: "two" }],
    };
    clientMocks.apiPut.mockResolvedValue({ session_version: 4 });

    await replaceExamConverterCorrectionIntents({
      conversionHubJobId: "job/one",
      request,
    } as Parameters<typeof replaceExamConverterCorrectionIntents>[0]);

    expect(clientMocks.apiPut).toHaveBeenCalledOnce();
    expect(clientMocks.apiPut).toHaveBeenCalledWith(
      "/api/v1/apps/documents.conversion_hub/exam-converter/jobs/job%2Fone/correction-session/intents",
      request,
    );
  });
});
