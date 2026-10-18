/**
 * Group, move and empty-part commands (TASK-SKRIPT-39-06-10 G4, G9, R3, R4).
 *
 * Expected behavior:
 *   Each command is exactly one server call against the cursor the history
 *   holds after the pending edit is stored, and one undo step. Grouping and
 *   Ny del open the created part's instruction in the editor; Ny del lands
 *   after the selected part entry when one is selected, otherwise after the
 *   selected question. Moving a question keeps it selected. A conflict
 *   reloads and selects nothing; a 422 refusal shows one failure toast and
 *   leaves the document untouched; every command is skipped while the editor
 *   is busy.
 */

import { createPinia, setActivePinia } from "pinia";
import { effectScope, ref } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../api/client";
import type { ExamWorkspaceDocumentResponse, NativeExamDocument } from "../../../api/examWorkspace";
import { useToastStore } from "../../../stores/toast";
import { buildParentDocument } from "./examWorkspaceParentDocument.specSupport";
import { buildSavedExamSummary } from "./useExamWorkspaceDocument.specSupport";
import { useExamWorkspaceStructure } from "./useExamWorkspaceStructure";

const apiMocks = vi.hoisted(() => ({
  addExamWorkspaceChild: vi.fn(),
  changeExamWorkspaceItemType: vi.fn(),
  createEmptyExamWorkspacePart: vi.fn(),
  createExamWorkspaceParent: vi.fn(),
  deleteExamWorkspaceChild: vi.fn(),
  deleteExamWorkspaceParent: vi.fn(),
  groupExamWorkspaceItems: vi.fn(),
  moveExamWorkspaceItem: vi.fn(),
  reorderExamWorkspaceChildren: vi.fn(),
}));

vi.mock("../../../api/examWorkspaceStructureCommands", () => apiMocks);

function documentResponse(document: NativeExamDocument): ExamWorkspaceDocumentResponse {
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

function createdPartResponse(
  document: NativeExamDocument,
  createdParentId: string,
): ExamWorkspaceDocumentResponse & { created_parent_id: string } {
  return { ...documentResponse(document), created_parent_id: createdParentId };
}

/** A childless part (parent_002) sitting among standalone questions, after item_002. */
function childlessMiddleDocument(): NativeExamDocument {
  const base = buildParentDocument();
  return {
    ...base,
    parents: [
      { ...base.parents[0]!, item_ids: ["item_001"], place: 0 },
      { instruction: [], item_ids: [], parent_id: "parent_002", place: 2 },
    ],
  };
}

function setup(selected: string | null = null) {
  const workspaceDocument = ref<NativeExamDocument | null>(buildParentDocument());
  const selectedItemId = ref<string | null>(selected);
  const selectedParentId = ref<string | null>(null);
  const historyCursor = ref<string | null>("cursor-before-flush");
  const calls: string[] = [];
  const flush = vi.fn(async (settle: boolean) => {
    calls.push(`flush:${settle}`);
    historyCursor.value = "cursor-after-flush";
    return true;
  });
  const onConflict = vi.fn(async () => undefined);
  const applied: ExamWorkspaceDocumentResponse[] = [];
  // The view wires this to the selection composable's selectEntry, which sets the shared part ref.
  const selectParent = vi.fn((parentId: string) => {
    selectedParentId.value = parentId;
  });
  const selectItem = vi.fn((itemId: string) => {
    selectedItemId.value = itemId;
  });
  let busy = false;
  const structure = effectScope().run(() =>
    useExamWorkspaceStructure({
      applyCommandResponse: (next) => {
        applied.push(next);
        workspaceDocument.value = next.document;
      },
      editDocument: (edit, selectId = null) => {
        workspaceDocument.value = edit(workspaceDocument.value!);
        if (selectId !== null) selectedItemId.value = selectId;
        return true;
      },
      flush,
      historyCursor,
      isBusy: () => busy,
      lineageId: () => "lineage-1",
      onConflict,
      replaceCopy: (run) => run(),
      savedRevision: () => 7,
      selectItem,
      selectParent,
      selectedItemId,
      selectedParentId,
      workspaceDocument,
    }),
  )!;
  return {
    applied,
    calls,
    flush,
    onConflict,
    selectItem,
    selectParent,
    selectedItemId,
    selectedParentId,
    setBusy: (value: boolean) => {
      busy = value;
    },
    structure,
    workspaceDocument,
  };
}

beforeEach(() => {
  setActivePinia(createPinia());
  for (const mock of Object.values(apiMocks)) mock.mockReset();
});

describe("groupItems", () => {
  it("sends the marked ids against the cursor stored after the pending edit and opens the new part", async () => {
    const { applied, calls, selectParent, structure } = setup();
    const grouped: NativeExamDocument = {
      ...buildParentDocument(),
      parents: [
        ...buildParentDocument().parents,
        { instruction: [], item_ids: ["item_004"], parent_id: "parent_002", place: 3 },
      ],
    };
    apiMocks.groupExamWorkspaceItems.mockImplementation(async () => {
      calls.push("group");
      return createdPartResponse(grouped, "parent_002");
    });

    const ok = await structure.groupItems(["item_004"]);

    expect(ok).toBe(true);
    expect(calls).toEqual(["flush:true", "group"]);
    expect(apiMocks.groupExamWorkspaceItems.mock.calls[0]).toEqual([
      "lineage-1",
      ["item_004"],
      "cursor-after-flush",
    ]);
    expect(applied).toHaveLength(1);
    expect(selectParent).toHaveBeenCalledWith("parent_002");
  });

  it("shows one failure toast and leaves the document unchanged on a 422 refusal", async () => {
    const { applied, structure, workspaceDocument } = setup("item_004");
    const before = workspaceDocument.value;
    apiMocks.groupExamWorkspaceItems.mockRejectedValue(
      new ApiError({ code: "VALIDATION_ERROR", message: "Frågan ligger redan i en del.", status: 422 }),
    );

    const ok = await structure.groupItems(["item_004"]);

    expect(ok).toBe(false);
    expect(useToastStore().toasts.map((toast) => [toast.variant, toast.message])).toEqual([
      ["failure", "Frågan ligger redan i en del."],
    ]);
    expect(applied).toEqual([]);
    expect(workspaceDocument.value).toBe(before);
  });
});

describe("addEmptyPart", () => {
  it("sends the position after the selected unit and opens the created part", async () => {
    const { applied, selectParent, structure } = setup("item_002");
    apiMocks.createEmptyExamWorkspacePart.mockResolvedValue(
      createdPartResponse(buildParentDocument(), "parent_002"),
    );

    await structure.addEmptyPart();

    expect(apiMocks.createEmptyExamWorkspacePart.mock.calls[0]).toEqual([
      "lineage-1",
      1,
      "cursor-after-flush",
    ]);
    expect(applied).toHaveLength(1);
    expect(selectParent).toHaveBeenCalledWith("parent_002");
  });

  it("sends the end position when nothing is selected", async () => {
    const { structure } = setup(null);
    apiMocks.createEmptyExamWorkspacePart.mockResolvedValue(
      createdPartResponse(buildParentDocument(), "parent_002"),
    );

    await structure.addEmptyPart();

    expect(apiMocks.createEmptyExamWorkspacePart.mock.calls[0]).toEqual([
      "lineage-1",
      2,
      "cursor-after-flush",
    ]);
  });

  it("inserts after the selected childless part, not the stale selected question", async () => {
    const document = childlessMiddleDocument();
    const { selectParent, selectedItemId, selectedParentId, structure, workspaceDocument } = setup("item_004");
    workspaceDocument.value = document;
    selectedParentId.value = "parent_002";
    apiMocks.createEmptyExamWorkspacePart.mockResolvedValue(createdPartResponse(document, "parent_003"));

    await structure.addEmptyPart();

    expect(selectedItemId.value).toBe("item_004");
    expect(apiMocks.createEmptyExamWorkspacePart.mock.calls[0]).toEqual([
      "lineage-1",
      3,
      "cursor-after-flush",
    ]);
    expect(selectParent).toHaveBeenCalledWith("parent_003");
  });

  it("inserts after the part the previous Ny del created, without a question in between", async () => {
    const base = buildParentDocument();
    const withNewPart: NativeExamDocument = {
      ...base,
      parents: [
        ...base.parents,
        { instruction: [], item_ids: [], parent_id: "parent_002", place: base.items.length },
      ],
    };
    const { selectParent, structure } = setup("item_004");
    apiMocks.createEmptyExamWorkspacePart.mockResolvedValue(createdPartResponse(withNewPart, "parent_002"));

    await structure.addEmptyPart();
    await structure.addEmptyPart();

    expect(apiMocks.createEmptyExamWorkspacePart.mock.calls.map((call) => call[1])).toEqual([2, 3]);
    expect(selectParent).toHaveBeenCalledWith("parent_002");
  });

  it("inserts after the selected part with children, not the unrelated selected question", async () => {
    const base = buildParentDocument();
    const { selectedParentId, structure } = setup("item_004");
    selectedParentId.value = "parent_001";
    apiMocks.createEmptyExamWorkspacePart.mockResolvedValue(createdPartResponse(base, "parent_002"));

    await structure.addEmptyPart();

    expect(apiMocks.createEmptyExamWorkspacePart.mock.calls[0]).toEqual([
      "lineage-1",
      1,
      "cursor-after-flush",
    ]);
  });
});

describe("moveItem", () => {
  it("moves a question to standalone with a null target and keeps it selected", async () => {
    const { selectItem, structure } = setup("item_001");
    apiMocks.moveExamWorkspaceItem.mockResolvedValue(documentResponse(buildParentDocument()));

    await structure.moveItem("item_001", null);

    expect(apiMocks.moveExamWorkspaceItem.mock.calls[0]).toEqual([
      "lineage-1",
      "item_001",
      null,
      "cursor-after-flush",
    ]);
    expect(selectItem).toHaveBeenCalledWith("item_001");
  });

  it("moves a question into a part by id and keeps it selected", async () => {
    const { selectItem, structure } = setup("item_004");
    apiMocks.moveExamWorkspaceItem.mockResolvedValue(documentResponse(buildParentDocument()));

    await structure.moveItem("item_004", "parent_001");

    expect(apiMocks.moveExamWorkspaceItem.mock.calls[0]).toEqual([
      "lineage-1",
      "item_004",
      "parent_001",
      "cursor-after-flush",
    ]);
    expect(selectItem).toHaveBeenCalledWith("item_004");
  });

  it("reloads on a conflict and selects nothing", async () => {
    const { applied, onConflict, selectItem, selectParent, structure } = setup("item_004");
    apiMocks.moveExamWorkspaceItem.mockRejectedValue(
      new ApiError({ code: "CONFLICT", message: "Dokumentet har ändrats.", status: 409 }),
    );

    await structure.moveItem("item_004", null);

    expect(onConflict).toHaveBeenCalledOnce();
    expect(applied).toEqual([]);
    expect(selectParent).not.toHaveBeenCalled();
    expect(selectItem).not.toHaveBeenCalled();
  });
});

describe("busy guard", () => {
  it("skips every command while the editor is busy", async () => {
    const { setBusy, structure } = setup("item_004");
    setBusy(true);

    expect(await structure.groupItems(["item_004"])).toBe(false);
    await structure.addEmptyPart();
    await structure.moveItem("item_004", null);

    expect(apiMocks.groupExamWorkspaceItems).not.toHaveBeenCalled();
    expect(apiMocks.createEmptyExamWorkspacePart).not.toHaveBeenCalled();
    expect(apiMocks.moveExamWorkspaceItem).not.toHaveBeenCalled();
  });
});
