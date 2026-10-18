/**
 * Exam workspace ordering transitions.
 *
 * Expected behavior (TASK-SKRIPT-39-06-08 D1, D2, D6):
 *   - A print order from two steps is never the key order, even when the
 *     random source makes the shuffle produce the identity.
 *   - Adding, removing or moving a step keeps the survivors' printed order
 *     and never leaves the print order equal to the key.
 *   - The last step cannot be removed.
 */

import { describe, expect, it } from "vitest";

import { newTeacherItem } from "./examWorkspaceItemEdits";
import {
  drawPrintOrder,
  keptPrintOrder,
  withShuffledSteps,
  withStepAdded,
  withStepMoved,
  withStepRemoved,
} from "./examWorkspaceOrdering";

function ids(count: number): string[] {
  return Array.from({ length: count }, (_, index) => `choice_${String(index + 1).padStart(3, "0")}`);
}

/** A random source that makes Fisher-Yates swap every element with itself, so the shuffle is the identity. */
const identityRandom = () => 0.999999;
const zeroRandom = () => 0;

describe("drawPrintOrder", () => {
  for (const size of [2, 3, 4, 5, 6]) {
    for (const [name, random] of [["identity", identityRandom], ["zero", zeroRandom]] as const) {
      it(`never returns the key order for ${size} steps with the ${name} random source`, () => {
        const key = ids(size);
        const order = drawPrintOrder(key, random);
        expect(order).not.toEqual(key);
        expect([...order].sort()).toEqual(key);
      });
    }
  }

  it("returns a single step unchanged", () => {
    expect(drawPrintOrder(["choice_001"])).toEqual(["choice_001"]);
  });
});

describe("step transitions", () => {
  const ordering = newTeacherItem("item_001", 1, "ordering");

  it("starts a new ordering question with a print order that differs from the key", () => {
    const keyIds = ordering.choices.map((choice) => choice.choice_id);
    expect(ordering.print_order).not.toEqual(keyIds);
    expect([...ordering.print_order].sort()).toEqual(keyIds);
  });

  it("keeps survivors' relative printed order and never equals the key after add, remove and move", () => {
    let item = ordering;
    for (let round = 0; round < 6; round += 1) {
      item = withStepAdded(item, identityRandom);
    }
    expect(item.choices).toHaveLength(8);
    const keyOf = () => item.choices.map((choice) => choice.choice_id);
    expect(item.print_order).not.toEqual(keyOf());

    const before = item.print_order.filter((id) => id !== "choice_004");
    item = withStepRemoved(item, "choice_004", zeroRandom);
    expect(item.choices.some((choice) => choice.choice_id === "choice_004")).toBe(false);
    expect(item.print_order).not.toEqual(keyOf());
    expect(item.print_order.filter((id) => before.includes(id))).toEqual(before);

    const printedBefore = item.print_order;
    item = withStepMoved(item, "choice_002", 1, identityRandom);
    expect(keyOf().slice(0, 3)).toEqual(["choice_001", "choice_003", "choice_002"]);
    expect(item.print_order).not.toEqual(keyOf());
    expect([...item.print_order].sort()).toEqual([...printedBefore].sort());
  });

  it("redraws when a move would make the print order equal the key", () => {
    const item = { ...ordering, print_order: ["choice_001", "choice_002"] };
    // Printed order is the key here by construction; any step change must redraw.
    const moved = withStepMoved(item, "choice_001", 1, zeroRandom);
    expect(moved.choices.map((choice) => choice.choice_id)).toEqual(["choice_002", "choice_001"]);
    expect(moved.print_order).not.toEqual(["choice_002", "choice_001"]);
  });

  it("keeps the last step and refuses ends", () => {
    const single = { ...ordering, choices: [ordering.choices[0]!], print_order: ["choice_001"] };
    expect(withStepRemoved(single, "choice_001")).toBe(single);
    expect(withStepMoved(ordering, "choice_001", -1)).toBe(ordering);
    expect(withStepMoved(ordering, "choice_002", 1)).toBe(ordering);
  });

  it("Blanda om draws a new non-key order", () => {
    const shuffled = withShuffledSteps(ordering, identityRandom);
    expect(shuffled.print_order).toEqual(["choice_002", "choice_001"]);
  });
});

describe("keptPrintOrder", () => {
  it("drops removed steps and places new ones without matching the key", () => {
    const order = keptPrintOrder(["choice_001", "choice_002", "choice_003"], ["choice_003", "choice_001", "choice_009"], zeroRandom);
    expect(order).not.toEqual(["choice_001", "choice_002", "choice_003"]);
    expect(order.filter((id) => id !== "choice_002")).toEqual(["choice_003", "choice_001"]);
  });
});
