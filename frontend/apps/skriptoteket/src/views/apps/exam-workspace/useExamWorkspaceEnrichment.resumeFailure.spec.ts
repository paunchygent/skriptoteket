/**
 * A suggestion job this page lost is found again when an exam opens:
 * failed lookup and retry (TASK-SKRIPT-39-04-09 P1, P2, P7).
 *
 * Expected behavior:
 *   A failed lookup is shown with a retry that asks again, only while the
 *   opening that asked is still open. The teacher's own request clears the
 *   failure, and a failure landing while that request is in flight is not
 *   shown.
 *
 * Rows follow the failed lookup that replaces C12, (F2-a to F2-d, F2-h,
 * F2-i) in `repair1/design.md`.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ExamWorkspaceAnswerKeySuggestionsStatus } from "../../../api/examWorkspace";
import { deferred } from "./useExamWorkspaceDocument.specSupport";
import { EXAM_WORKSPACE_ENRICHMENT_MAX_POLL_MS } from "./useExamWorkspaceEnrichment";
import {
  LOOKUP_FAILURE_COPY,
  expectDelivered,
  expectUntouched,
  jobStatus,
  lookupFailureToasts,
  openAWithLookupHeld,
  setupResumeEnv,
  teardownResumeEnv,
} from "./useExamWorkspaceEnrichment.resume.specSupport";

const apiMocks = vi.hoisted(() => ({
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceConversionStatus: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  requestExamWorkspaceAnswerKeySuggestions: vi.fn(),
}));
const exportApiMocks = vi.hoisted(() => ({
  downloadExamWorkspaceExport: vi.fn(),
}));

vi.mock("../../../api/examWorkspaceExports", () => exportApiMocks);
vi.mock("../../../api/examWorkspace", async () => ({
  ...apiMocks,
  getExamCourseCatalog: (await import("../../../test/examCourseCatalog")).getExamCourseCatalog,
}));

beforeEach(() => {
  setupResumeEnv(apiMocks, exportApiMocks);
});

afterEach(() => {
  teardownResumeEnv();
});

describe("a failed lookup is shown and can be retried (C12)", () => {
  it("F2-a: the failure is shown once, delivers nothing and is not rerun on its own", async () => {
    const { document, enrichment, lookup } = await openAWithLookupHeld(apiMocks);

    lookup.reject(new Error("network"));
    await flushPromises();
    expect(lookupFailureToasts()).toBe(1);
    await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_ENRICHMENT_MAX_POLL_MS);

    expectUntouched(document);
    expect(enrichment.enrichmentStatus.value).toBeNull();
    expect(enrichment.enrichmentLookupError.value).toBe(LOOKUP_FAILURE_COPY);
    expect(apiMocks.findExamWorkspaceAnswerKeySuggestions).toHaveBeenCalledTimes(1);
  });

  it("F2-b: retry asks again for the same saved version and delivers the found job", async () => {
    const { document, enrichment, lookup } = await openAWithLookupHeld(apiMocks);
    lookup.reject(new Error("network"));
    await flushPromises();

    apiMocks.findExamWorkspaceAnswerKeySuggestions.mockResolvedValueOnce(
      jobStatus("succeeded", { withSuggestion: true }),
    );
    await enrichment.retryEnrichmentLookup();
    await flushPromises();

    expect(apiMocks.findExamWorkspaceAnswerKeySuggestions.mock.calls).toEqual([
      ["lineage-a", 1],
      ["lineage-a", 1],
    ]);
    expectDelivered(document);
    expect(enrichment.enrichmentLookupError.value).toBeNull();
  });

  it("F2-c: a retry that fails again shows the failure again", async () => {
    const { enrichment, lookup } = await openAWithLookupHeld(apiMocks);
    lookup.reject(new Error("network"));
    await flushPromises();

    apiMocks.findExamWorkspaceAnswerKeySuggestions.mockRejectedValueOnce(new Error("500"));
    await enrichment.retryEnrichmentLookup();
    await flushPromises();

    expect(enrichment.enrichmentLookupError.value).toBe(LOOKUP_FAILURE_COPY);
    expect(apiMocks.findExamWorkspaceAnswerKeySuggestions).toHaveBeenCalledTimes(2);
  });

  it("F2-d: a retry that finds no job clears the failure", async () => {
    const { document, enrichment, lookup } = await openAWithLookupHeld(apiMocks);
    lookup.reject(new Error("network"));
    await flushPromises();

    await enrichment.retryEnrichmentLookup();
    await flushPromises();

    expectUntouched(document);
    expect(enrichment.enrichmentLookupError.value).toBeNull();
    expect(enrichment.enrichmentStatus.value).toBeNull();
  });

  it("F2-h: the teacher's own request clears the failure", async () => {
    const { enrichment, lookup } = await openAWithLookupHeld(apiMocks);
    lookup.reject(new Error("network"));
    await flushPromises();
    apiMocks.requestExamWorkspaceAnswerKeySuggestions.mockResolvedValueOnce(
      jobStatus("queued", { jobId: "job-b" }),
    );

    await enrichment.requestSuggestionsForAll();

    expect(enrichment.enrichmentLookupError.value).toBeNull();
    expect(enrichment.enrichmentStatus.value?.job_id).toBe("job-b");
  });

  it("F2-i: a failure landing while the teacher's own request is in flight is not shown", async () => {
    const { enrichment, lookup } = await openAWithLookupHeld(apiMocks);
    const request = deferred<ExamWorkspaceAnswerKeySuggestionsStatus>();
    apiMocks.requestExamWorkspaceAnswerKeySuggestions.mockReturnValueOnce(request.promise);
    const requesting = enrichment.requestSuggestionsForAll();

    lookup.reject(new Error("network"));
    await flushPromises();
    request.resolve(jobStatus("queued", { jobId: "job-b" }));
    await requesting;

    expect(enrichment.enrichmentLookupError.value).toBeNull();
    expect(lookupFailureToasts()).toBe(0);
  });
});
