/** New conversion-key actions use the guarded item patch path and save the resulting key. */
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { examWorkspaceItemReadiness } from "./examWorkspaceItemReadiness";
import { gapItem } from "./examWorkspaceKeyedItems.specSupport";
import { currentDocument, currentItem, openMatchingDocumentWithFence, savedResponse, saveCopyAs } from "./useExamWorkspaceDocument.specSupport";

const api = vi.hoisted(() => ({
  getExamWorkspaceDocument: vi.fn(),
  copyExamWorkspaceDocument: vi.fn(),
}));
vi.mock("../../../api/examWorkspace", async () => ({
  ...api,
  getExamCourseCatalog: (await import("../../../test/examCourseCatalog")).getExamCourseCatalog,
}));

beforeEach(() => {
  vi.clearAllMocks();
  setActivePinia(createPinia());
});

function interpretedItem() {
  const item = gapItem("ai_interpreted", [["gap_001", ["Stockholm"]], ["gap_002", ["Oslo"]]], null);
  return {
    ...item,
    facit_text: "Stockholm och Oslo",
    gaps: item.gaps.map((gap) => ({ ...gap, automatic_values: [gap.gap_id === "gap_001" ? "Stockhom" : "Oslp"] })),
  };
}

describe("document conversion-key actions", () => {
  it("undo makes the copy dirty and export-blocked, then saves the empty key and retained facit", async () => {
    const { fence, state } = await openMatchingDocumentWithFence(api.getExamWorkspaceDocument, interpretedItem());
    state.undoItemAiKey("item_001");
    expect(state.isDirty.value).toBe(true);
    expect(examWorkspaceItemReadiness(currentItem(state))).toContain("missing_answer_key");
    expect(currentItem(state).facit_text).toBe("Stockholm och Oslo");
    expect(currentItem(state).answer_key_retry).toBe("offered");
    const copy = currentDocument(state);
    api.copyExamWorkspaceDocument.mockResolvedValue(savedResponse({ ...copy, revision: 2 }));
    expect(await saveCopyAs(state, fence, "Kopia")).toBe("saved");
    const payload = api.copyExamWorkspaceDocument.mock.calls[0]?.[2];
    expect(payload.items[0].answer_key.origin).toBe("absent");
    expect(payload.items[0].gaps.every((gap: { automatic_values: string[] }) => gap.automatic_values.length === 0)).toBe(true);
    expect(payload.items[0].facit_text).toBe("Stockholm och Oslo");
    expect(payload.items[0].answer_key_retry).toBe("offered");
    expect(state.isDirty.value).toBe(false);
  });

  it.each(["ai_interpreted", "machine_proposed", "source_provided"] as const)(
    "removes one automatic value and turns a different gap into text while preserving %s",
    async (origin) => {
      const source = interpretedItem();
      source.answer_key.origin = origin;
      const readiness = examWorkspaceItemReadiness(source);
      const { fence, state } = await openMatchingDocumentWithFence(api.getExamWorkspaceDocument, source);
      state.removeItemAutomaticValue("item_001", "gap_001", "Stockhom");
      expect(currentItem(state).gaps[0]?.automatic_values).toEqual([]);
      expect(currentItem(state).answer_key.origin).toBe(origin);
      expect(examWorkspaceItemReadiness(currentItem(state))).toEqual(readiness);
      state.showItemGapAsText("item_001", "gap_002");
      expect(currentItem(state).gaps.map((gap) => gap.gap_id)).toEqual(["gap_001"]);
      expect(currentItem(state).body[0]?.segments).toContainEqual({ kind: "text", marks: [], text: "Oslo", kept_gap_id: null });
      expect(currentItem(state).points).toBe(1);
      expect(currentItem(state).answer_key.origin).toBe(origin);
      expect(examWorkspaceItemReadiness(currentItem(state))).toEqual(readiness);
      expect(state.isDirty.value).toBe(true);
      const copy = currentDocument(state);
      api.copyExamWorkspaceDocument.mockResolvedValue(savedResponse({ ...copy, revision: 2 }));
      expect(await saveCopyAs(state, fence, "Kopia")).toBe("saved");
      const payload = api.copyExamWorkspaceDocument.mock.calls[0]?.[2];
      expect(payload.items[0].answer_key.origin).toBe(origin);
      expect(payload.items[0].gaps).toEqual(currentItem(state).gaps);
    },
  );

  it("refuses all new actions while busy and ignores unknown items", async () => {
    const source = interpretedItem();
    const { fence, state } = await openMatchingDocumentWithFence(api.getExamWorkspaceDocument, source);
    state.undoItemAiKey("missing");
    state.removeItemAutomaticValue("missing", "gap_001", "Stockhom");
    state.showItemGapAsText("missing", "gap_002");
    expect(state.isDirty.value).toBe(false);
    const opened = currentDocument(state);
    api.getExamWorkspaceDocument.mockImplementation(() => new Promise(() => {}));
    void state.openDocument("another-lineage", fence.begin());
    expect(state.isBusy.value).toBe(true);
    state.undoItemAiKey("item_001");
    state.removeItemAutomaticValue("item_001", "gap_001", "Stockhom");
    state.showItemGapAsText("item_001", "gap_002");
    expect(currentDocument(state)).toBe(opened);
    expect(state.isDirty.value).toBe(false);
  });
});
