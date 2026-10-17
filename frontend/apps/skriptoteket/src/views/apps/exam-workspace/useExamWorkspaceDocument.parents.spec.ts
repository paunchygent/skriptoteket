/**
 * Exam workspace document state with parents.
 *
 * Expected behavior:
 *   Every edit the editor offers on a child (points, text, gap
 *   answers, review) leaves the parents untouched and the children
 *   consecutive and in sequence order, so a save never sends a parent the
 *   server would refuse. Adding questions is covered by
 *   `useExamWorkspaceStructure.spec.ts`.
 */

import { flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { effectScope } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ExamWorkspaceDocumentResponse, NativeExamDocument } from "../../../api/examWorkspace";
import { buildParentDocument } from "./examWorkspaceParentDocument.specSupport";
import { useExamWorkspaceDocument } from "./useExamWorkspaceDocument";
import { buildSavedExamSummary } from "./useExamWorkspaceDocument.specSupport";

const apiMocks = vi.hoisted(() => ({
  downloadExamWorkspaceExport: vi.fn(),
  getExamWorkspaceConversionStatus: vi.fn(),
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  requestExamWorkspaceAnswerMisspellings: vi.fn(),
  saveExamWorkspaceDocument: vi.fn(),
}));

vi.mock("../../../api/examWorkspace", async () => ({
  ...apiMocks,
  getExamCourseCatalog: (await import("../../../test/examCourseCatalog")).getExamCourseCatalog,
}));

function buildResponse(document: NativeExamDocument): ExamWorkspaceDocumentResponse {
  return {
    history_cursor: "00000000-0000-4000-8000-000000000001",
    conversion: null,
    document,
    saved_document: document,
    notes: [],
    summary: buildSavedExamSummary({ title: document.title }),
  };
}

async function openParentDocument() {
  apiMocks.getExamWorkspaceDocument.mockResolvedValue(buildResponse(buildParentDocument()));
  const state = effectScope().run(() => useExamWorkspaceDocument());
  if (!state) {
    throw new Error("expected the document state to be created");
  }
  await state.openDocument("lineage-1");
  await flushPromises();
  return state;
}

function expectParentsValid(document: NativeExamDocument): void {
  for (const parent of document.parents) {
    const children = parent.item_ids.map((itemId) => {
      const child = document.items.find((item) => item.item_id === itemId);
      expect(child).toBeDefined();
      return child!;
    });
    const first = children[0]!.sequence;
    expect(children.map((child) => child.sequence)).toEqual(
      children.map((_, index) => first + index),
    );
  }
}

beforeEach(() => {
  setActivePinia(createPinia());
  apiMocks.getExamWorkspaceDocument.mockReset();
  apiMocks.saveExamWorkspaceDocument.mockReset();
  apiMocks.requestExamWorkspaceAnswerMisspellings.mockReset();
  apiMocks.requestExamWorkspaceAnswerMisspellings.mockResolvedValue({ automatic_values: [] });
});

describe("parents in useExamWorkspaceDocument", () => {
  it("keeps parents and children valid through every child edit", async () => {
    const original = buildParentDocument();
    const state = await openParentDocument();
    apiMocks.saveExamWorkspaceDocument.mockResolvedValue(buildResponse(original));
    const child = original.items[1]!;
    const gapId = child.gaps[0]!.gap_id;

    state.updateItemPoints("item_002", 2);
    state.updateItemGapValues("item_002", gapId, ["grieve", "mourn"]);
    state.updateItemParagraphSegments("item_002", 0, [{ kind: "text", marks: [], text: "Edited." }]);
    state.markItemReviewed("item_002");

    await expect(state.saveDocument()).resolves.toBe(true);

    const sent = apiMocks.saveExamWorkspaceDocument.mock.calls[0]![1].document as NativeExamDocument;
    expect(sent.parents).toEqual(original.parents);
    expect(sent.items.map((item) => item.item_id)).toEqual([
      "item_001",
      "item_002",
      "item_003",
      "item_004",
    ]);
    expectParentsValid(sent);
  });

  it("changes only the edited child's points, so the parent total follows from its children", async () => {
    const state = await openParentDocument();

    state.updateItemPoints("item_003", null);

    const document = state.workspaceDocument.value!;
    expect(document.items.map((item) => item.points)).toEqual([1, 1, null, 1]);
    expect(document.parents).toEqual(buildParentDocument().parents);
  });

  it("clears the estimate mark when the teacher sets the points", async () => {
    const estimated = buildParentDocument();
    estimated.items = estimated.items.map((item) => ({ ...item, points_estimated: true }));
    apiMocks.getExamWorkspaceDocument.mockResolvedValue(buildResponse(estimated));
    const state = effectScope().run(() => useExamWorkspaceDocument())!;
    await state.openDocument("lineage-1");
    await flushPromises();

    state.updateItemPoints("item_002", 3);

    const items = state.workspaceDocument.value!.items;
    expect(items.map((item) => item.points_estimated)).toEqual([true, false, true, true]);
    expect(items[1]!.points).toBe(3);
  });
});
