/**
 * Saved exam list merge rules.
 *
 * Purpose:
 *   Lock how a fetched saved-exam list merges into entries already known
 *   locally, so an import or save that lands while the list request is in
 *   flight is never dropped or rolled back to an older version.
 */

import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ExamWorkspaceDocumentSummary } from "../../../api/examWorkspace";
import { bodyText, plainBody } from "./examWorkspaceRichText";
import { mergeSavedDocuments } from "./examWorkspaceSavedDocuments";
import {
  buildResponse,
  buildSavedExamSummary,
  currentItem,
  openMatchingDocument as openWith,
} from "./useExamWorkspaceDocument.specSupport";

const apiMocks = vi.hoisted(() => ({
  downloadExamWorkspaceExport: vi.fn(),
  getExamWorkspaceConversionStatus: vi.fn(),
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  saveExamWorkspaceDocument: vi.fn(),
}));

vi.mock("../../../api/examWorkspace", async () => ({
  ...apiMocks,
  getExamCourseCatalog: (await import("../../../test/examCourseCatalog")).getExamCourseCatalog,
}));

function summary(lineageId: string, version: number): ExamWorkspaceDocumentSummary {
  return buildSavedExamSummary({
    lineage_id: lineageId,
    name: `${lineageId}.provdokument.zip`,
    saved_at: "2026-10-09T08:00:00Z",
    title: lineageId,
    vault_file_id: `file-${lineageId}-${version}`,
    version,
  });
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

beforeEach(() => {
  setActivePinia(createPinia());
  apiMocks.getExamWorkspaceDocument.mockReset();
  apiMocks.saveExamWorkspaceDocument.mockReset();
});

function openMatchingDocument() {
  return openWith(apiMocks.getExamWorkspaceDocument);
}

describe("matching edits in useExamWorkspaceDocument", () => {
  it("changes only the named entry text on its own side", async () => {
    const state = await openMatchingDocument();

    state.updateItemMatchEntryBody("item_001", "left", "left_002", plainBody("being locked up"));
    state.updateItemMatchEntryBody("item_001", "right", "right_003", plainBody("contempt"));

    const item = currentItem(state);
    expect(item.match_left.map((entry) => bodyText(entry.body))).toEqual([
      "absence from school without permission",
      "being locked up",
      "a feeling that someone deserves no respect",
    ]);
    expect(item.match_right.map((entry) => bodyText(entry.body))).toEqual([
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
    await expect(state.saveDocument("position-1")).resolves.toBe(true);
    expect(apiMocks.saveExamWorkspaceDocument).toHaveBeenCalledTimes(1);
  });

  it("refuses to save a keyed grid with a row left without a tick", async () => {
    const state = await openMatchingDocument();

    state.updateItemMatchPairs("item_001", [
      { left_id: "left_001", right_id: "right_002" },
      { left_id: "left_002", right_id: "right_002" },
    ]);

    await expect(state.saveDocument("position-1")).resolves.toBe(false);
    expect(apiMocks.saveExamWorkspaceDocument).not.toHaveBeenCalled();
  });

  it("saves an emptied entry text as an empty body", async () => {
    const state = await openMatchingDocument();
    apiMocks.saveExamWorkspaceDocument.mockResolvedValue(buildResponse());

    state.updateItemMatchEntryBody("item_001", "right", "right_001", []);

    await expect(state.saveDocument("position-1")).resolves.toBe(true);
    const saved = apiMocks.saveExamWorkspaceDocument.mock.calls[0]?.[1].document;
    expect(saved?.items[0]?.match_right.find((entry: { right_id: string }) => entry.right_id === "right_001")?.body).toEqual([]);
  });
});
