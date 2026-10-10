/**
 * Saved exam list merge rules.
 *
 * Purpose:
 *   Lock how a fetched saved-exam list merges into entries already known
 *   locally, so an import or save that lands while the list request is in
 *   flight is never dropped or rolled back to an older version.
 */

import { createTestingPinia } from "@pinia/testing";
import { setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ExamWorkspaceDocumentSummary } from "../../../api/examWorkspace";
import { buildResponse } from "../ExamWorkspaceSlice.specSupport";
import { mergeSavedDocuments, useExamWorkspaceDocument } from "./useExamWorkspaceDocument";

const apiMocks = vi.hoisted(() => ({
  getExamWorkspaceDocument: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  saveExamWorkspaceDocument: vi.fn(),
}));

vi.mock("../../../api/examWorkspace", () => apiMocks);

function summary(lineageId: string, version: number): ExamWorkspaceDocumentSummary {
  return {
    lineage_id: lineageId,
    name: `${lineageId}.provdokument.zip`,
    saved_at: "2026-10-09T08:00:00Z",
    vault_file_id: `file-${lineageId}-${version}`,
    version,
  };
}

describe("mergeSavedDocuments", () => {
  it("keeps local entries the response does not know about", () => {
    const merged = mergeSavedDocuments([summary("imported", 1)], [summary("older", 2)]);

    expect(merged.map((entry) => entry.lineage_id)).toEqual(["imported", "older"]);
  });

  it("keeps a newer local version over the fetched one", () => {
    const merged = mergeSavedDocuments([summary("exam", 3)], [summary("exam", 2)]);

    expect(merged).toEqual([summary("exam", 3)]);
  });

  it("takes the fetched entry when it is as new or newer", () => {
    const merged = mergeSavedDocuments([summary("exam", 2)], [summary("exam", 4)]);

    expect(merged).toEqual([summary("exam", 4)]);
  });
});

describe("useExamWorkspaceDocument save outcome", () => {
  beforeEach(() => {
    setActivePinia(createTestingPinia({ createSpy: vi.fn }));
    vi.clearAllMocks();
    apiMocks.getExamWorkspaceDocument.mockResolvedValue(buildResponse({ version: 1 }));
    apiMocks.saveExamWorkspaceDocument.mockResolvedValue(buildResponse({ version: 2 }));
  });

  it("returns false when there is no document or another operation is busy", async () => {
    const document = useExamWorkspaceDocument();
    expect(await document.saveDocument()).toBe(false);
    await document.openDocument("lineage-1");
    document.isBusy.value = true;

    expect(await document.saveDocument(["item_002"])).toBe(false);
    expect(apiMocks.saveExamWorkspaceDocument).not.toHaveBeenCalled();
  });

  it("returns true and sends an empty rejection list for no-argument callers", async () => {
    const document = useExamWorkspaceDocument();
    await document.openDocument("lineage-1");

    expect(await document.saveDocument()).toBe(true);
    expect(apiMocks.saveExamWorkspaceDocument).toHaveBeenCalledWith(
      "lineage-1",
      expect.objectContaining({ rejectedProposalItemIds: [] }),
    );
  });

  it("copies rejection ids before sending and returns false on a transport failure", async () => {
    apiMocks.saveExamWorkspaceDocument.mockRejectedValueOnce(new Error("network"));
    const document = useExamWorkspaceDocument();
    await document.openDocument("lineage-1");
    const rejected = ["item_002"];
    const result = document.saveDocument(rejected);
    rejected.push("item_003");

    expect(await result).toBe(false);
    expect(apiMocks.saveExamWorkspaceDocument).toHaveBeenCalledWith(
      "lineage-1",
      expect.objectContaining({ rejectedProposalItemIds: ["item_002"] }),
    );
  });

  it("returns false without transport when item validation refuses the save", async () => {
    const document = useExamWorkspaceDocument();
    await document.openDocument("lineage-1");
    document.updateItemChoiceText("item_002", "choice_a", "");

    expect(await document.saveDocument()).toBe(false);
    expect(apiMocks.saveExamWorkspaceDocument).not.toHaveBeenCalled();
  });
});
