/** New conversion-key actions use the guarded item patch path and save the resulting key. */
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { examWorkspaceItemReadiness } from "./examWorkspaceItemReadiness";
import { gapItem } from "./examWorkspaceKeyedItems.specSupport";
import { currentDocument, currentItem, openMatchingDocument, savedResponse } from "./useExamWorkspaceDocument.specSupport";

const api = vi.hoisted(() => ({
  getExamWorkspaceDocument: vi.fn(),
  saveExamWorkspaceDocument: vi.fn(),
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
    const state = await openMatchingDocument(api.getExamWorkspaceDocument, interpretedItem());
    state.undoItemInterpretation("item_001");
    expect(state.isDirty.value).toBe(true);
    expect(examWorkspaceItemReadiness(currentItem(state))).toContain("missing_answer_key");
    expect(currentItem(state).facit_text).toBe("Stockholm och Oslo");
    const copy = currentDocument(state);
    api.saveExamWorkspaceDocument.mockResolvedValue(savedResponse({ ...copy, revision: 2 }));
    expect(await state.saveDocument()).toBe(true);
    const payload = api.saveExamWorkspaceDocument.mock.calls[0]?.[1].document;
    expect(payload.items[0].answer_key.origin).toBe("absent");
    expect(payload.items[0].gaps.every((gap: { automatic_values: string[] }) => gap.automatic_values.length === 0)).toBe(true);
    expect(payload.items[0].facit_text).toBe("Stockholm och Oslo");
    expect(state.isDirty.value).toBe(false);
  });

  it.each(["ai_interpreted", "machine_proposed", "source_provided"] as const)(
    "removes one automatic value and turns a different gap into text while preserving %s",
    async (origin) => {
      const source = interpretedItem();
      source.answer_key.origin = origin;
      const readiness = examWorkspaceItemReadiness(source);
      const state = await openMatchingDocument(api.getExamWorkspaceDocument, source);
      state.removeItemAutomaticValue("item_001", "gap_001", "Stockhom");
      expect(currentItem(state).gaps[0]?.automatic_values).toEqual([]);
      expect(currentItem(state).answer_key.origin).toBe(origin);
      expect(examWorkspaceItemReadiness(currentItem(state))).toEqual(readiness);
      state.showItemGapAsText("item_001", "gap_002");
      expect(currentItem(state).gaps.map((gap) => gap.gap_id)).toEqual(["gap_001"]);
      expect(currentItem(state).body[0]?.segments).toContainEqual({ kind: "text", marks: [], text: "Oslo" });
      expect(currentItem(state).points).toBe(1);
      expect(currentItem(state).answer_key.origin).toBe(origin);
      expect(examWorkspaceItemReadiness(currentItem(state))).toEqual(readiness);
      expect(state.isDirty.value).toBe(true);
      const copy = currentDocument(state);
      api.saveExamWorkspaceDocument.mockResolvedValue(savedResponse({ ...copy, revision: 2 }));
      expect(await state.saveDocument()).toBe(true);
      const payload = api.saveExamWorkspaceDocument.mock.calls[0]?.[1].document;
      expect(payload.items[0].answer_key.origin).toBe(origin);
      expect(payload.items[0].gaps).toEqual(currentItem(state).gaps);
    },
  );

  it("refuses all new actions while busy and ignores unknown items", async () => {
    const source = interpretedItem();
    const state = await openMatchingDocument(api.getExamWorkspaceDocument, source);
    state.undoItemInterpretation("missing");
    state.removeItemAutomaticValue("missing", "gap_001", "Stockhom");
    state.showItemGapAsText("missing", "gap_002");
    expect(state.isDirty.value).toBe(false);
    const opened = currentDocument(state);
    api.getExamWorkspaceDocument.mockImplementation(() => new Promise(() => {}));
    void state.openDocument("another-lineage");
    expect(state.isBusy.value).toBe(true);
    state.undoItemInterpretation("item_001");
    state.removeItemAutomaticValue("item_001", "gap_001", "Stockhom");
    state.showItemGapAsText("item_001", "gap_002");
    expect(currentDocument(state)).toBe(opened);
    expect(state.isDirty.value).toBe(false);
  });
});
