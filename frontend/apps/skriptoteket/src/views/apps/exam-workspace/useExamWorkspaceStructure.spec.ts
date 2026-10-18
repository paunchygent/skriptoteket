/**
 * Exam workspace structure commands.
 *
 * Expected behavior:
 *   A new question lands after the selected unit and never inside an
 *   instruction's deluppgifter; deleting a standalone question keeps the
 *   sequences contiguous. Server commands run against the cursor the history
 *   holds after storing the pending edit, never the cursor from before it.
 *   Byt frågetyp names what it removed in Swedish; a refused command leaves
 *   no notice behind. Deleting an instruction keeps its questions by default
 *   or takes them along; deleting its last question keeps the part as an
 *   instruction block (G8); a delete that would empty the exam is refused
 *   inline, never in a toast (user ruling 2026-10-17).
 */

import { createPinia, setActivePinia } from "pinia";
import { effectScope, ref } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../api/client";
import type {
  ExamWorkspaceDocumentResponse,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import { useToastStore } from "../../../stores/toast";
import { newTeacherItem } from "./examWorkspaceItemEdits";
import { examWorkspaceItemReadiness } from "./examWorkspaceItemReadiness";
import { buildParentDocument } from "./examWorkspaceParentDocument.specSupport";
import { buildSavedExamSummary } from "./useExamWorkspaceDocument.specSupport";
import { useExamWorkspaceStructure } from "./useExamWorkspaceStructure";

const apiMocks = vi.hoisted(() => ({
  addExamWorkspaceChild: vi.fn(),
  changeExamWorkspaceItemType: vi.fn(),
  createExamWorkspaceParent: vi.fn(),
  deleteExamWorkspaceChild: vi.fn(),
  deleteExamWorkspaceParent: vi.fn(),
  reorderExamWorkspaceChildren: vi.fn(),
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

/** The fixture without its instruction; `keep` leaves the deluppgifter as standalone questions. */
function withoutParent(keep: boolean): NativeExamDocument {
  const document = buildParentDocument();
  const childIds = new Set(document.parents[0]!.item_ids);
  return {
    ...document,
    items: keep ? document.items : document.items.filter((item) => !childIds.has(item.item_id)),
    parents: [],
  };
}

const EMPTY_EXAM = new ApiError({
  code: "VALIDATION_ERROR",
  details: { parent_id: "parent_001", reason: "exam_requires_question" },
  message: "Provet måste ha minst en fråga.",
  status: 422,
});

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
  const selectParent = vi.fn();
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
      replaceCopy: (run) => run(),
      savedRevision: () => 7,
      selectItem: (itemId) => {
        selectedItemId.value = itemId;
      },
      selectParent,
      selectedItemId,
      selectedParentId,
      workspaceDocument,
    }),
  )!;
  return { applied, calls, flush, onConflict, selectParent, selectedItemId, selectedParentId, structure, workspaceDocument };
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
      for (const entry of [...item.choices, ...item.match_left, ...item.match_right]) {
        expect(entry.body).toEqual([]);
      }
      expect(item.body.flatMap((paragraph) => paragraph.segments).some((segment) => segment.kind === "text")).toBe(
        false,
      );
    },
  );

  it("starts a question without text, so the empty-text blocker shows at once", () => {
    const item = newTeacherItem("item_009", 9, "free_text");

    expect(item.body).toEqual([]);
    expect(examWorkspaceItemReadiness(item)).toContain("empty_question_text");
  });
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

  it("deletes the last deluppgift on the server and keeps the part as an instruction block (G8)", async () => {
    const { structure, workspaceDocument } = setup("item_001");
    const document = workspaceDocument.value!;
    workspaceDocument.value = {
      ...document,
      parents: document.parents.map((parent) => ({ ...parent, item_ids: ["item_001"] })),
    };
    const after = {
      ...document,
      items: document.items.filter((item) => item.item_id !== "item_001"),
      parents: document.parents.map((parent) => ({ ...parent, item_ids: [] })),
    };
    apiMocks.deleteExamWorkspaceChild.mockResolvedValue(response(after));

    structure.deleteItem("item_001");

    await vi.waitFor(() => expect(apiMocks.deleteExamWorkspaceChild).toHaveBeenCalled());
    await vi.waitFor(() => expect(structure.running.value).toBe(false));
    expect(structure.deleteNotice.value).toBeNull();
    expect(workspaceDocument.value.parents).toEqual(
      document.parents.map((parent) => ({ ...parent, item_ids: [] })),
    );
    expect(useToastStore().toasts).toEqual([]);
  });

  it("says nothing about the heading when the server kept it", async () => {
    const { structure } = setup("item_002");
    const after = buildParentDocument();
    after.items = after.items.filter((item) => item.item_id !== "item_002");
    apiMocks.deleteExamWorkspaceChild.mockResolvedValue(response(after));

    structure.deleteItem("item_002");
    await vi.waitFor(() => expect(apiMocks.deleteExamWorkspaceChild).toHaveBeenCalled());
    await vi.waitFor(() => expect(structure.running.value).toBe(false));

    expect(structure.deleteNotice.value).toBeNull();
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

describe("deleting an instruction", () => {
  it("keeps the questions by default and selects the first of them", async () => {
    const { structure, selectedItemId, workspaceDocument } = setup("item_004");
    apiMocks.deleteExamWorkspaceParent.mockResolvedValue(response(withoutParent(true)));

    await structure.deleteParent("parent_001", "keep_questions");

    expect(apiMocks.deleteExamWorkspaceParent.mock.calls[0]).toEqual([
      "lineage-1",
      "parent_001",
      "keep_questions",
      "cursor-after-flush",
    ]);
    expect(workspaceDocument.value!.items).toHaveLength(4);
    expect(selectedItemId.value).toBe("item_001");
    expect(structure.deleteNotice.value).toBeNull();
  });

  it("takes the questions along only when asked, and selects the next unit", async () => {
    const { structure, selectedItemId, workspaceDocument } = setup("item_002");
    apiMocks.deleteExamWorkspaceParent.mockResolvedValue(response(withoutParent(false)));

    await structure.deleteParent("parent_001", "with_questions");

    expect(apiMocks.deleteExamWorkspaceParent.mock.calls[0]![2]).toBe("with_questions");
    expect(workspaceDocument.value!.items.map((item) => item.item_id)).toEqual(["item_004"]);
    expect(selectedItemId.value).toBe("item_004");
  });

  it("refuses inline, never in a toast, when the exam would have no question left", async () => {
    const { structure, applied } = setup("item_001");
    apiMocks.deleteExamWorkspaceParent.mockRejectedValue(EMPTY_EXAM);

    await structure.deleteParent("parent_001", "with_questions");

    expect(applied).toEqual([]);
    expect(structure.deleteNotice.value).toEqual({ kind: "refused", text: "Provet måste ha minst en fråga." });
    expect(useToastStore().toasts).toEqual([]);
  });

  it("refuses a last-deluppgift delete inline when it would empty the exam", async () => {
    const { structure } = setup("item_001");
    apiMocks.deleteExamWorkspaceChild.mockRejectedValue(EMPTY_EXAM);

    structure.deleteItem("item_001");

    await vi.waitFor(() => expect(structure.deleteNotice.value?.kind).toBe("refused"));
    expect(useToastStore().toasts).toEqual([]);
  });

  it("still toasts any other refusal and clears an earlier notice when the next command starts", async () => {
    const { structure } = setup("item_001");
    apiMocks.deleteExamWorkspaceParent.mockRejectedValueOnce(EMPTY_EXAM);
    await structure.deleteParent("parent_001", "with_questions");
    expect(structure.deleteNotice.value).not.toBeNull();

    apiMocks.deleteExamWorkspaceParent.mockRejectedValueOnce(
      new ApiError({ code: "VALIDATION_ERROR", message: "Instruktionen finns inte.", status: 422 }),
    );
    await structure.deleteParent("parent_001", "keep_questions");

    expect(structure.deleteNotice.value).toBeNull();
    expect(useToastStore().toasts.map((toast) => [toast.variant, toast.message])).toEqual([
      ["failure", "Instruktionen finns inte."],
    ]);
  });

  it("reloads on a stale cursor and leaves the document alone", async () => {
    const { structure, onConflict, applied } = setup("item_001");
    apiMocks.deleteExamWorkspaceParent.mockRejectedValue(
      new ApiError({ code: "CONFLICT", message: "Dokumentet har ändrats.", status: 409 }),
    );

    await structure.deleteParent("parent_001", "keep_questions");

    expect(onConflict).toHaveBeenCalledOnce();
    expect(applied).toEqual([]);
    expect(structure.deleteNotice.value).toBeNull();
  });
});
