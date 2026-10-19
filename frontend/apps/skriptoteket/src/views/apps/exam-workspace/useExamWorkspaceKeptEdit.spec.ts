/**
 * Exam workspace kept-edit recovery state: the step document a refused edit
 * started from stays available across a failed reload and a later conflict,
 * and clears only after a merged store, an exam change, or disposal.
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

describe("the kept-edit recovery state", () => {
  it("starts empty, keeps the set base, and clears it", () => {
    const kept = useExamWorkspaceKeptEdit();
    expect(kept.has()).toBe(false);
    expect(kept.get()).toBeNull();
    const base = exam();
    kept.set(base);
    expect(kept.has()).toBe(true);
    const held = kept.get();
    if (held === null) {
      throw new Error("expected the kept base");
    }
    expect(points(held, "item_001")).toBe(2);
    kept.clear();
    expect(kept.has()).toBe(false);
    expect(kept.get()).toBeNull();
  });

  it("replaces the base when a newer refused edit is kept", () => {
    const kept = useExamWorkspaceKeptEdit();
    const first = exam();
    const second: NativeExamDocument = {
      ...exam(),
      items: exam().items.map((item) =>
        item.item_id === "item_001" ? { ...item, points: 7 } : item,
      ),
    };
    kept.set(first);
    kept.set(second);
    const held = kept.get();
    if (held === null) {
      throw new Error("expected the kept base");
    }
    expect(points(held, "item_001")).toBe(7);
  });
});
