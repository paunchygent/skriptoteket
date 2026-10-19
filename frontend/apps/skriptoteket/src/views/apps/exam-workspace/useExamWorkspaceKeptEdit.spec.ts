/**
 * Exam workspace kept-edit recovery state: the refused edit's base and edited
 * snapshot stay available across a failed reload and a failed history resync,
 * and clear only after a merged store, an exam change, or disposal.
 */

import { describe, expect, it } from "vitest";

import type { NativeExamDocument } from "../../../api/examWorkspace";
import { useExamWorkspaceKeptEdit } from "./useExamWorkspaceKeptEdit";
import { exam } from "./useExamWorkspaceEditing.history.specSupport";

function points(document: NativeExamDocument, itemId: string): number | null {
  const found = document.items.find((item) => item.item_id === itemId);
  if (found === undefined) {
    throw new Error(`expected ${itemId}`);
  }
  return found.points;
}

function edited(pointsValue: number): NativeExamDocument {
  return {
    ...exam(),
    items: exam().items.map((item) =>
      item.item_id === "item_001" ? { ...item, points: pointsValue } : item,
    ),
  };
}

describe("the kept-edit recovery state", () => {
  it("starts empty, keeps the set base and snapshot, and clears them", () => {
    const kept = useExamWorkspaceKeptEdit();
    expect(kept.has()).toBe(false);
    expect(kept.get()).toBeNull();
    const base = exam();
    kept.set(base, edited(7));
    expect(kept.has()).toBe(true);
    const held = kept.get();
    if (held === null) {
      throw new Error("expected the kept edit");
    }
    expect(points(held.base, "item_001")).toBe(2);
    expect(points(held.edited, "item_001")).toBe(7);
    kept.clear();
    expect(kept.has()).toBe(false);
    expect(kept.get()).toBeNull();
  });

  it("replaces the base and snapshot when a newer refused edit is kept", () => {
    const kept = useExamWorkspaceKeptEdit();
    kept.set(exam(), edited(7));
    kept.set(exam(), edited(8));
    const held = kept.get();
    if (held === null) {
      throw new Error("expected the kept edit");
    }
    expect(points(held.base, "item_001")).toBe(2);
    expect(points(held.edited, "item_001")).toBe(8);
  });
});
