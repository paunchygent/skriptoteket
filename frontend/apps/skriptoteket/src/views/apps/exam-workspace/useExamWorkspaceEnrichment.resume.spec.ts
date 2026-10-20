/**
 * A suggestion job this page lost is found again when an exam opens:
 * lookup and resume (TASK-SKRIPT-39-04-09 P1, P2, P7).
 *
 * Expected behavior:
 *   Every new opening asks for the newest job requested on its saved
 *   version. A queued or running job is polled, a finished job's suggestions
 *   are written through the same arrival path as any job of this opening.
 *   A failed job delivers its partial suggestions with its failure message.
 *
 * Rows follow the case tables (C1-C5) in the retained design note
 * `evidence/implementation/TASK-SKRIPT-39-04-09/design.md`.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  EXAM_WORKSPACE_ENRICHMENT_MAX_POLL_MS,
  EXAM_WORKSPACE_ENRICHMENT_POLL_MS,
} from "./useExamWorkspaceEnrichment";
import {
  composeWorkspace,
  expectDelivered,
  expectUntouched,
  jobStatus,
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

describe("an exam opening asks for its lost job", () => {
  it("C1: no job leaves the exam as opened and polls nothing", async () => {
    const { document, enrichment, fence } = composeWorkspace();
    await open({ document, fence }, "lineage-a", apiMocks);
    await flushPromises();

    expect(apiMocks.findExamWorkspaceAnswerKeySuggestions).toHaveBeenCalledWith("lineage-a", 1);
    expectUntouched(document);
    expect(enrichment.enrichmentStatus.value).toBeNull();
    await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_ENRICHMENT_MAX_POLL_MS);
    expect(apiMocks.getExamWorkspaceAnswerKeySuggestions).not.toHaveBeenCalled();
  });

  it("C4: a succeeded job arrives on its question, unsaved, as if no reload happened", async () => {
    const { document, enrichment, lookup } = await openAWithLookupHeld(apiMocks);

    lookup.resolve(jobStatus("succeeded", { withSuggestion: true }));
    await flushPromises();

    expectDelivered(document);
    expect(enrichment.enrichmentMessage.value).toBe("1 facitförslag har lagts in på frågorna.");
  });

  it("C2/C3: a running job is polled in this opening and delivers when it finishes", async () => {
    const { document, enrichment, lookup } = await openAWithLookupHeld(apiMocks);
    lookup.resolve(jobStatus("running"));
    await flushPromises();
    expect(enrichment.isEnrichmentPending.value).toBe(true);
    expectUntouched(document);

    apiMocks.getExamWorkspaceAnswerKeySuggestions.mockResolvedValueOnce(
      jobStatus("succeeded", { withSuggestion: true }),
    );
    await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_ENRICHMENT_POLL_MS);

    expect(apiMocks.getExamWorkspaceAnswerKeySuggestions).toHaveBeenCalledWith(
      "lineage-a",
      "job-a",
    );
    expectDelivered(document);
  });

  it("C2: a resumed pending job blocks a second request in the same opening", async () => {
    const { enrichment, lookup } = await openAWithLookupHeld(apiMocks);
    lookup.resolve(jobStatus("queued"));
    await flushPromises();

    await enrichment.requestSuggestionsForAll();

    expect(apiMocks.requestExamWorkspaceAnswerKeySuggestions).not.toHaveBeenCalled();
  });

  it("C5: a failed job delivers its partial suggestions with its failure message", async () => {
    const { document, enrichment, lookup } = await openAWithLookupHeld(apiMocks);

    lookup.resolve(jobStatus("failed", { withSuggestion: true, message: "Budget slut." }));
    await flushPromises();

    expectDelivered(document);
    expect(enrichment.enrichmentMessage.value).toBe("Budget slut.");
  });

});
