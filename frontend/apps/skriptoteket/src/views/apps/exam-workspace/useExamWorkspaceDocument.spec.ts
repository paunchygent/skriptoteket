/**
 * Saved exam list merge rules.
 *
 * Purpose:
 *   Lock how a fetched saved-exam list merges into entries already known
 *   locally, so an import or save that lands while the list request is in
 *   flight is never dropped or rolled back to an older version.
 */

import { flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { effectScope } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type {
  ExamWorkspaceDocumentResponse,
  ExamWorkspaceDocumentSummary,
} from "../../../api/examWorkspace";
import { buildMatchingItem } from "./examWorkspaceMatchingItem.specSupport";
import { mergeSavedDocuments, useExamWorkspaceDocument } from "./useExamWorkspaceDocument";

const apiMocks = vi.hoisted(() => ({
  downloadExamWorkspaceExport: vi.fn(),
  getExamWorkspaceConversionStatus: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceEnrichment: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  saveExamWorkspaceDocument: vi.fn(),
  startExamWorkspaceEnrichment: vi.fn(),
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

function buildResponse(): ExamWorkspaceDocumentResponse {
  return {
    document: {
      assets: [],
      document_id: "doc-1",
      instructions: [],
      items: [buildMatchingItem()],
      origin: {
        extractor_version: "docx-extractor-1",
        kind: "docx_import",
        source_filename: "english-1.docx",
        source_sha256: "abc123",
      },
      parents: [],
      revision: 1,
      schema_version: "native_exam_document_v1",
      title: "English 1",
    },
    notes: [],
    summary: {
      lineage_id: "lineage-1",
      name: "english-1.provdokument.zip",
      saved_at: "2026-10-11T08:00:00Z",
      vault_file_id: "file-1",
      version: 1,
    },
  };
}

async function openMatchingDocument() {
  apiMocks.getExamWorkspaceDocument.mockResolvedValue(buildResponse());
  const state = effectScope().run(() => useExamWorkspaceDocument());
  if (!state) {
    throw new Error("expected the document state to be created");
  }
  await state.openDocument("lineage-1");
  await flushPromises();
  return state;
}

function currentItem(state: Awaited<ReturnType<typeof openMatchingDocument>>) {
  const item = state.workspaceDocument.value?.items[0];
  if (!item) {
    throw new Error("expected a loaded matching item");
  }
  return item;
}

beforeEach(() => {
  setActivePinia(createPinia());
  apiMocks.getExamWorkspaceDocument.mockReset();
  apiMocks.saveExamWorkspaceDocument.mockReset();
});

describe("matching edits in useExamWorkspaceDocument", () => {
  it("changes only the named entry text on its own side", async () => {
    const state = await openMatchingDocument();

    state.updateItemMatchEntryText("item_001", "left", "left_002", "being locked up");
    state.updateItemMatchEntryText("item_001", "right", "right_003", "contempt");

    const item = currentItem(state);
    expect(item.match_left.map((entry) => entry.text)).toEqual([
      "absence from school without permission",
      "being locked up",
      "a feeling that someone deserves no respect",
    ]);
    expect(item.match_right.map((entry) => entry.text)).toEqual([
      "incarceration",
      "truancy",
      "contempt",
    ]);
    expect(item.answer_key.match_pairs).toHaveLength(3);
    expect(state.isDirty.value).toBe(true);
  });

  it("keys the item as teacher authored when pairs are chosen", async () => {
    const state = await openMatchingDocument();

    state.updateItemMatchPairs("item_001", [{ left_id: "left_001", right_id: "right_001" }]);

    expect(currentItem(state).answer_key).toEqual({
      correct_choice_ids: [],
      match_pairs: [{ left_id: "left_001", right_id: "right_001" }],
      origin: "teacher_authored",
    });
  });

  it("makes the key absent when every pair is cleared, and the save goes through", async () => {
    const state = await openMatchingDocument();
    apiMocks.saveExamWorkspaceDocument.mockResolvedValue(buildResponse());

    state.updateItemMatchPairs("item_001", []);

    expect(currentItem(state).answer_key.origin).toBe("absent");
    expect(currentItem(state).answer_key.match_pairs).toEqual([]);
    await expect(state.saveDocument()).resolves.toBe(true);
    expect(apiMocks.saveExamWorkspaceDocument).toHaveBeenCalledTimes(1);
  });

  it("refuses to save a keyed item that uses a right entry twice", async () => {
    const state = await openMatchingDocument();

    state.updateItemMatchPairs("item_001", [
      { left_id: "left_001", right_id: "right_002" },
      { left_id: "left_002", right_id: "right_002" },
      { left_id: "left_003", right_id: "right_003" },
    ]);

    await expect(state.saveDocument()).resolves.toBe(false);
    expect(apiMocks.saveExamWorkspaceDocument).not.toHaveBeenCalled();
  });

  it("refuses to save an empty entry text", async () => {
    const state = await openMatchingDocument();

    state.updateItemMatchEntryText("item_001", "right", "right_001", "");

    await expect(state.saveDocument()).resolves.toBe(false);
    expect(apiMocks.saveExamWorkspaceDocument).not.toHaveBeenCalled();
  });
});
