/**
 * Byt frågetyp on an unconverted question (TASK-SKRIPT-39-05-15 D2).
 *
 * Expected behavior:
 *   Choosing the stored kind on an unbuilt question (review_required with a
 *   source_fallback origin) sends the change-type command, so the server can
 *   flip only the origin; choosing the stored kind on any other question
 *   stays a no-op and sends nothing.
 */

import { createPinia, setActivePinia } from "pinia";
import { effectScope, ref } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type {
  ExamWorkspaceDocumentResponse,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import { buildParentDocument } from "./examWorkspaceParentDocument.specSupport";
import { serverExamWorkspaceStore } from "./examWorkspaceStore";
import { buildSavedExamSummary } from "./useExamWorkspaceDocument.specSupport";
import { useExamWorkspaceStructure } from "./useExamWorkspaceStructure";

const apiMocks = vi.hoisted(() => ({
  changeExamWorkspaceItemType: vi.fn(),
}));

vi.mock("../../../api/examWorkspaceStructureCommands", () => apiMocks);

function response(document: NativeExamDocument): ExamWorkspaceDocumentResponse {
  return {
    conversion: null,
    document,
    export_blockers: [],
    history_cursor: "cursor-after-command",
    notes: [],
    saved_document: document,
    summary: buildSavedExamSummary({ title: document.title }),
  };
}

/** The parent document with item_001 (gap_fill) left unconverted. */
function unbuiltDocument(): NativeExamDocument {
  const document = buildParentDocument();
  return {
    ...document,
    items: document.items.map((item) =>
      item.item_id === "item_001"
        ? { ...item, review: { ...item.review, confidence: null, parse_origin: "source_fallback", state: "review_required" } }
        : item,
    ),
  };
}

function setup(document: NativeExamDocument) {
  const workspaceDocument = ref<NativeExamDocument | null>(document);
  const structure = effectScope().run(() =>
    useExamWorkspaceStructure({
      applyCommandResponse: (next) => {
        workspaceDocument.value = next.document;
      },
      editDocument: () => true,
      flush: async () => true,
      historyCursor: ref("cursor-before-flush"),
      isBusy: () => false,
      isReadOnly: () => false,
      lineageId: () => "lineage-1",
      noteLeaseLost: () => undefined,
      onConflict: async () => undefined,
      replaceCopy: (run) => run(),
      savedRevision: () => 7,
      selectItem: () => undefined,
      selectParent: () => undefined,
      selectedItemId: ref<string | null>(null),
      selectedParentId: ref<string | null>(null),
      shared: serverExamWorkspaceStore.shared,
      tabId: () => "tab-1",
      workspaceDocument,
    }),
  );
  if (!structure) throw new Error("structure composable did not mount");
  return structure;
}

beforeEach(() => {
  setActivePinia(createPinia());
  apiMocks.changeExamWorkspaceItemType.mockReset();
  apiMocks.changeExamWorkspaceItemType.mockResolvedValue({ ...response(unbuiltDocument()), dropped_content: [] });
});

describe("changeType on an unconverted question", () => {
  it("sends the stored kind for an unbuilt question", async () => {
    const structure = setup(unbuiltDocument());

    await structure.changeType("item_001", "gap_fill");

    expect(apiMocks.changeExamWorkspaceItemType).toHaveBeenCalledOnce();
    expect(apiMocks.changeExamWorkspaceItemType.mock.calls[0]![1]).toEqual({
      expected_cursor: "cursor-before-flush",
      expected_revision: 7,
      item_id: "item_001",
      tab_id: "tab-1",
      target_kind: "gap_fill",
    });
  });

  it("sends nothing for the stored kind on a built question", async () => {
    const structure = setup(buildParentDocument());

    await structure.changeType("item_004", "single_choice");

    expect(apiMocks.changeExamWorkspaceItemType).not.toHaveBeenCalled();
  });
});
