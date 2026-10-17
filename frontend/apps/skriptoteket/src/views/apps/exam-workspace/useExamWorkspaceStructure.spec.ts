/**
 * Exam workspace structure commands.
 *
 * Expected behavior:
 *   A new question lands after the selected unit and never inside an
 *   instruction's deluppgifter; deleting a standalone question keeps the
 *   sequences contiguous. Server commands run against the cursor the history
 *   holds after storing the pending edit, never the cursor from before it.
 *   Byt frågetyp names what it removed in Swedish; a refused command leaves
 *   no notice behind.
 */

import { createPinia, setActivePinia } from "pinia";
import { effectScope, ref } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../api/client";
import type { ExamWorkspaceDocumentResponse, NativeExamDocument } from "../../../api/examWorkspace";
import { newTeacherItem } from "./examWorkspaceItemEdits";
import { buildParentDocument } from "./examWorkspaceParentDocument.specSupport";
import { buildSavedExamSummary } from "./useExamWorkspaceDocument.specSupport";
import { useExamWorkspaceStructure } from "./useExamWorkspaceStructure";

const apiMocks = vi.hoisted(() => ({
  addExamWorkspaceChild: vi.fn(),
  changeExamWorkspaceItemType: vi.fn(),
  createExamWorkspaceParent: vi.fn(),
  deleteExamWorkspaceChild: vi.fn(),
  reorderExamWorkspaceChildren: vi.fn(),
}));

vi.mock("../../../api/examWorkspace", () => apiMocks);

function response(document: NativeExamDocument): ExamWorkspaceDocumentResponse {
  return {
    conversion: null,
    document,
    history_cursor: "cursor-after-command",
    notes: [],
    saved_document: document,
    summary: buildSavedExamSummary({ title: document.title }),
  };
}

function setup(selected: string | null = null) {
  const workspaceDocument = ref<NativeExamDocument | null>(buildParentDocument());
  const selectedItemId = ref<string | null>(selected);
  const historyCursor = ref<string | null>("cursor-before-flush");
  const calls: string[] = [];
  const flush = vi.fn(async (settle: boolean) => {
    calls.push(`flush:${settle}`);
    historyCursor.value = "cursor-after-flush";
  });
  const onConflict = vi.fn(async () => undefined);
  const applied: ExamWorkspaceDocumentResponse[] = [];
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
      isBusy: () => false,
      lineageId: () => "lineage-1",
      onConflict,
      savedRevision: () => 7,
      selectItem: (itemId) => {
        selectedItemId.value = itemId;
      },
      selectedItemId,
      workspaceDocument,
    }),
  )!;
  return { applied, calls, flush, onConflict, selectedItemId, structure, workspaceDocument };
}

beforeEach(() => {
  setActivePinia(createPinia());
  for (const mock of Object.values(apiMocks)) mock.mockReset();
});

describe("adding and deleting standalone questions", () => {
  it("puts a question added from a deluppgift after the whole instruction", () => {
    const { structure, workspaceDocument, selectedItemId } = setup("item_002");

    structure.addItem("single_choice");

    const document = workspaceDocument.value!;
    expect(document.items.map((item) => item.item_id)).toEqual([
      "item_001",
      "item_002",
      "item_003",
      "item_005",
      "item_004",
    ]);
    expect(document.items.map((item) => item.sequence)).toEqual([1, 2, 3, 4, 5]);
    expect(document.parents).toEqual(buildParentDocument().parents);
    expect(selectedItemId.value).toBe("item_005");
  });

  it("appends when nothing is selected", () => {
    const { structure, workspaceDocument } = setup(null);

    structure.addItem("free_text");

    expect(workspaceDocument.value!.items.at(-1)).toMatchObject({ item_id: "item_005", sequence: 5 });
  });

  it("deletes a standalone question, closes the sequence gap and selects its neighbour", () => {
    const { structure, workspaceDocument, selectedItemId } = setup("item_004");
    structure.addItem("matching");
    selectedItemId.value = "item_005";

    structure.deleteItem("item_005");

    expect(workspaceDocument.value!.items.map((item) => [item.item_id, item.sequence])).toEqual([
      ["item_001", 1],
      ["item_002", 2],
      ["item_003", 3],
      ["item_004", 4],
    ]);
    expect(selectedItemId.value).toBe("item_004");
  });
});

describe("new questions keep the server's structure rules", () => {
  it.each(["single_choice", "multiple_response", "gap_fill", "inline_choice", "matching", "short_answer"] as const)(
    "%s",
    (kind) => {
      const item = newTeacherItem("item_009", 9, kind);
      const placed = item.body.flatMap((paragraph) =>
        paragraph.segments.flatMap((segment) => (segment.kind === "gap" ? [segment.gap_id] : [])),
      );
      expect(placed.sort()).toEqual(item.gaps.map((gap) => gap.gap_id).sort());
      if (item.kind === "single_choice" || item.kind === "multiple_response") {
        expect(item.choices.length).toBeGreaterThanOrEqual(2);
      }
      for (const gap of item.gaps) {
        if (item.kind === "inline_choice") {
          expect(gap.options.map((option) => option.choice_id)).toContain(gap.correct_option_id);
        } else {
          expect(gap.options).toEqual([]);
        }
      }
      if (item.kind === "matching") {
        expect(item.match_left.length).toBeGreaterThanOrEqual(1);
        expect(item.match_right.length).toBeGreaterThanOrEqual(2);
        expect(item.points).toBeNull();
        expect(item.answer_key.match_pairs).toEqual([]);
      } else {
        expect(item.tick_points).toBeNull();
      }
      for (const text of [...item.choices, ...item.match_left, ...item.match_right].flatMap((entry) =>
        entry.body.flatMap((paragraph) => paragraph.segments),
      )) {
        expect(text.kind === "text" && text.text.length).toBeGreaterThan(0);
      }
    },
  );
});

describe("server commands", () => {
  it("deletes a deluppgift with the cursor stored after the pending edit", async () => {
    const { structure, calls } = setup("item_002");
    const after = buildParentDocument();
    after.items = after.items.filter((item) => item.item_id !== "item_002");
    after.parents = after.parents.map((parent) => ({
      ...parent,
      item_ids: parent.item_ids.filter((id) => id !== "item_002"),
    }));
    apiMocks.deleteExamWorkspaceChild.mockImplementation(async () => {
      calls.push("delete");
      return response(after);
    });

    structure.deleteItem("item_002");
    await vi.waitFor(() => expect(apiMocks.deleteExamWorkspaceChild).toHaveBeenCalled());

    expect(calls).toEqual(["flush:true", "delete"]);
    expect(apiMocks.deleteExamWorkspaceChild.mock.calls[0]).toEqual([
      "lineage-1",
      buildParentDocument().parents[0]!.parent_id,
      "item_002",
      "cursor-after-flush",
    ]);
  });

  it("refuses to delete the last deluppgift without asking the server", () => {
    const { structure, workspaceDocument } = setup("item_001");
    const document = workspaceDocument.value!;
    workspaceDocument.value = {
      ...document,
      parents: document.parents.map((parent) => ({ ...parent, item_ids: ["item_001"] })),
    };

    structure.deleteItem("item_001");

    expect(apiMocks.deleteExamWorkspaceChild).not.toHaveBeenCalled();
    expect(workspaceDocument.value.items).toHaveLength(4);
  });

  it("selects the deluppgift the server added", async () => {
    const { structure, selectedItemId } = setup("item_001");
    const after = buildParentDocument();
    const parentId = after.parents[0]!.parent_id;
    after.items = [...after.items, newTeacherItem("item_005", 5, "free_text")];
    apiMocks.addExamWorkspaceChild.mockResolvedValue(response(after));

    await structure.addChild(parentId, "free_text");

    expect(apiMocks.addExamWorkspaceChild.mock.calls[0]![2]).toMatchObject({
      expected_cursor: "cursor-after-flush",
      position: 3,
    });
    expect(selectedItemId.value).toBe("item_005");
  });

  it("names the removed content in Swedish after Byt frågetyp", async () => {
    const { structure } = setup("item_004");
    apiMocks.changeExamWorkspaceItemType.mockResolvedValue({
      ...response(buildParentDocument()),
      dropped_content: ["choices", "correct_choice_ids", "ai_suggestion"],
    });

    await structure.changeType("item_004", "free_text");

    expect(apiMocks.changeExamWorkspaceItemType.mock.calls[0]![1]).toEqual({
      expected_cursor: "cursor-after-flush",
      expected_revision: 7,
      item_id: "item_004",
      target_kind: "free_text",
    });
    expect(structure.typeNotice.value).toEqual({
      itemId: "item_004",
      kind: "free_text",
      text: "Bytte till Fritext. Borttaget: svarsalternativen, facit och AI:s facitförslag.",
    });
  });

  it("reloads on a conflict and shows no notice", async () => {
    const { structure, onConflict, applied } = setup("item_004");
    apiMocks.changeExamWorkspaceItemType.mockRejectedValue(
      new ApiError({ code: "CONFLICT", message: "Dokumentet har ändrats.", status: 409 }),
    );

    await structure.changeType("item_004", "free_text");

    expect(onConflict).toHaveBeenCalledOnce();
    expect(applied).toEqual([]);
    expect(structure.typeNotice.value).toBeNull();
  });
});
