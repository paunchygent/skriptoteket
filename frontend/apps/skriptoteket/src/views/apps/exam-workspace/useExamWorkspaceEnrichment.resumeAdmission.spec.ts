/**
 * A suggestion job this page lost is found again when an exam opens:
 * opening admission (TASK-SKRIPT-39-04-09 P1, P2, P7).
 *
 * Expected behavior:
 *   The answer is admitted only if, when it lands, the opening is still
 *   open, its copy still stands on the asked-for saved version, and the
 *   teacher has not started a job of their own there. Same-exam replacements
 *   keep the opening and ask nothing. A failed lookup affects only the
 *   opening that asked.
 *
 * Rows follow the case tables (C8, C10, C11, C13-C16) in the retained design
 * note `evidence/implementation/TASK-SKRIPT-39-04-09/design.md` and, for
 * the failed lookup's opening scope, (F2-e to F2-g) in `repair1/design.md`.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ExamWorkspaceAnswerKeySuggestionsStatus } from "../../../api/examWorkspace";
import { createSyncFence } from "./examWorkspaceSyncFence";
import { deferred } from "./useExamWorkspaceDocument.specSupport";
import { EXAM_WORKSPACE_ENRICHMENT_POLL_MS } from "./useExamWorkspaceEnrichment";
import {
  composeWorkspace,
  examResponse,
  expectDelivered,
  expectUntouched,
  jobStatus,
  lookupFailureToasts,
  open,
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

describe("a failed lookup affects only the opening that asked", () => {
  it("F2-e: A's failure landing after B opened shows nothing on B", async () => {
    const { document, enrichment, lookup } = await openAWithLookupHeld(apiMocks);
    await open(document, "lineage-b", apiMocks);
    await flushPromises();

    lookup.reject(new Error("network"));
    await flushPromises();

    expect(document.summary.value?.lineage_id).toBe("lineage-b");
    expect(enrichment.enrichmentLookupError.value).toBeNull();
    expect(lookupFailureToasts()).toBe(0);
    await enrichment.retryEnrichmentLookup();
    expect(apiMocks.findExamWorkspaceAnswerKeySuggestions.mock.calls).toEqual([
      ["lineage-a", 1],
      ["lineage-b", 1],
    ]);
  });

  it("F2-f: an earlier opening's failure does not reach a later opening of the same exam", async () => {
    const { document, enrichment, lookup } = await openAWithLookupHeld(apiMocks);
    await open(document, "lineage-b", apiMocks);
    await open(document, "lineage-a", apiMocks);
    await flushPromises();

    lookup.reject(new Error("network"));
    await flushPromises();

    expect(enrichment.enrichmentLookupError.value).toBeNull();
    expect(lookupFailureToasts()).toBe(0);
  });

  it("F2-g: a failure landing after disposal shows nothing", async () => {
    const { enrichment, lookup, scope } = await openAWithLookupHeld(apiMocks);
    scope.stop();

    lookup.reject(new Error("network"));
    await flushPromises();

    expect(enrichment.enrichmentLookupError.value).toBeNull();
    expect(lookupFailureToasts()).toBe(0);
  });
});

describe("the answer is admitted only when it lands on the opening that asked", () => {
  it("C8: the copy was saved to a newer version while the lookup was in flight", async () => {
    const { document, enrichment, lookup } = await openAWithLookupHeld(apiMocks);
    const currentC8 = document.workspaceDocument.value;
    if (currentC8 === null) {
      throw new Error("expected an open document");
    }
    document.noteStored(createSyncFence().begin(), { ...currentC8, revision: 2 });
    expect(document.savedRevision.value).toBe(2);

    lookup.resolve(jobStatus("succeeded", { withSuggestion: true }));
    await flushPromises();

    expectUntouched(document);
    expect(enrichment.enrichmentStatus.value).toBeNull();
  });

  it("C11: another exam was opened before the lookup landed", async () => {
    const { document, enrichment, lookup } = await openAWithLookupHeld(apiMocks);
    await open(document, "lineage-b", apiMocks);
    await flushPromises();

    lookup.resolve(jobStatus("succeeded", { withSuggestion: true }));
    await flushPromises();

    expect(document.summary.value?.lineage_id).toBe("lineage-b");
    expectUntouched(document);
    expect(enrichment.enrichmentStatus.value).toBeNull();
  });

  it("C10: the teacher's own request in this opening wins over a later lookup", async () => {
    const { document, enrichment, lookup } = await openAWithLookupHeld(apiMocks);
    apiMocks.requestExamWorkspaceAnswerKeySuggestions.mockResolvedValueOnce(
      jobStatus("queued", { jobId: "job-b" }),
    );
    await enrichment.requestSuggestionsForAll();

    lookup.resolve(jobStatus("succeeded", { withSuggestion: true }));
    await flushPromises();

    expectUntouched(document);
    expect(enrichment.enrichmentStatus.value?.job_id).toBe("job-b");
  });

  it("C10: a lookup landing while the teacher's request is in flight is dropped", async () => {
    const { document, enrichment, lookup } = await openAWithLookupHeld(apiMocks);
    const request = deferred<ExamWorkspaceAnswerKeySuggestionsStatus>();
    apiMocks.requestExamWorkspaceAnswerKeySuggestions.mockReturnValueOnce(request.promise);
    const requesting = enrichment.requestSuggestionsForAll();

    lookup.resolve(jobStatus("succeeded", { withSuggestion: true }));
    await flushPromises();
    expectUntouched(document);

    request.resolve(jobStatus("queued", { jobId: "job-b" }));
    await requesting;
    expect(enrichment.enrichmentStatus.value?.job_id).toBe("job-b");
  });

  it("disposal before the lookup lands applies nothing", async () => {
    const { document, lookup, scope } = await openAWithLookupHeld(apiMocks);
    scope.stop();

    lookup.resolve(jobStatus("succeeded", { withSuggestion: true }));
    await flushPromises();

    expectUntouched(document);
  });
});

describe("which openings ask", () => {
  it("C15: switching back to an exam finds the job its earlier opening lost", async () => {
    const { document, enrichment } = composeWorkspace();
    await open(document, "lineage-a", apiMocks);
    apiMocks.requestExamWorkspaceAnswerKeySuggestions.mockResolvedValueOnce(jobStatus("queued"));
    await enrichment.requestSuggestionsForAll();
    await open(document, "lineage-b", apiMocks);
    await flushPromises();

    apiMocks.findExamWorkspaceAnswerKeySuggestions.mockResolvedValueOnce(
      jobStatus("succeeded", { withSuggestion: true }),
    );
    await open(document, "lineage-a", apiMocks);
    await flushPromises();

    expect(apiMocks.findExamWorkspaceAnswerKeySuggestions.mock.calls).toEqual([
      ["lineage-a", 1],
      ["lineage-b", 1],
      ["lineage-a", 1],
    ]);
    expect(document.summary.value?.lineage_id).toBe("lineage-a");
    expectDelivered(document);
  });

  it("C13/C14: a same-exam reload keeps the opening and asks nothing", async () => {
    const { document } = composeWorkspace();
    await open(document, "lineage-a", apiMocks);
    await flushPromises();
    apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(examResponse("lineage-a"));

    await document.reloadDocument();
    await flushPromises();

    expect(apiMocks.findExamWorkspaceAnswerKeySuggestions).toHaveBeenCalledTimes(1);
  });

  it("C16 (P7): a resumed running job delivers across a later save", async () => {
    const { document, lookup } = await openAWithLookupHeld(apiMocks);
    lookup.resolve(jobStatus("running"));
    await flushPromises();
    const currentC16 = document.workspaceDocument.value;
    if (currentC16 === null) {
      throw new Error("expected an open document");
    }
    document.noteStored(createSyncFence().begin(), { ...currentC16, revision: 2 });

    apiMocks.getExamWorkspaceAnswerKeySuggestions.mockResolvedValueOnce(
      jobStatus("succeeded", { withSuggestion: true }),
    );
    await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_ENRICHMENT_POLL_MS);

    expect(document.savedRevision.value).toBe(2);
    expectDelivered(document);
  });
});
