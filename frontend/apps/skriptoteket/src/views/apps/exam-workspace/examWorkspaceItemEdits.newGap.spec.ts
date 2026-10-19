/**
 * Exam workspace item edits: atomic new-gap creation.
 *
 * Expected behavior:
 *   `nextGapId` names the next free gap above the item's highest declared or
 *   placed gap id, or null at gap_999. `withNewGap` writes one gap creation
 *   as one atomic structural item edit: the passed body plus the new gap
 *   record, with records ordered by body placement and existing records
 *   untouched. `createItemGap` submits that transition through `patchItem`
 *   as structural.
 */

import { describe, expect, it, vi } from "vitest";

import type {
  NativeExamBodyParagraph,
  NativeExamBodySegment,
  NativeExamItem,
} from "../../../api/examWorkspace";
import { hasInvalidAnswerKey } from "./examWorkspaceAnswerKeyRules";
import { newTeacherItem } from "./examWorkspaceItemEdits";
import { nextGapId, withNewGap } from "./examWorkspaceGapEdits";
import { withGapTextShape, withShortAnswerShape } from "./examWorkspaceShortAnswer";
import { useExamWorkspaceItemEdits } from "./useExamWorkspaceItemEdits";
import { buildGap } from "./examWorkspaceKeyedItems.specSupport";
import { buildGapItem } from "./ExamWorkspaceBodyEditor.specSupport";
import { gapNumberIn } from "./examWorkspaceGapLabels";
import { plainBody } from "./examWorkspaceRichText";

/** One paragraph placing each gap id in order between text runs. */
function gapBody(...gapIds: string[]): NativeExamBodyParagraph[] {
  const segments: NativeExamBodySegment[] = [{ kind: "text", marks: [], text: "Före " }];
  for (const gapId of gapIds) {
    segments.push({ gap_id: gapId, kind: "gap" }, { kind: "text", marks: [], text: " mellan " });
  }
  segments.push({ kind: "text", marks: [], text: "efter." });
  return [{ heading_level: null, segments }];
}

function gapFillItem(gaps: NativeExamItem["gaps"], body: NativeExamBodyParagraph[]): NativeExamItem {
  return buildGapItem({ body, gaps, kind: "gap_fill" });
}

describe("nextGapId", () => {
  it("names gap_001 when the item has no gaps and the body places none", () => {
    expect(nextGapId(buildGapItem({ body: [], gaps: [] }))).toBe("gap_001");
  });

  it("names one above the highest declared gap", () => {
    const item = gapFillItem(
      [buildGap("gap_001", ["100"]), buildGap("gap_007")],
      gapBody("gap_001", "gap_007"),
    );
    expect(nextGapId(item)).toBe("gap_008");
  });

  it("counts a placed body gap that has no record yet", () => {
    const item = gapFillItem(
      [buildGap("gap_001", ["100"]), buildGap("gap_007")],
      gapBody("gap_001", "gap_007", "gap_009"),
    );
    expect(nextGapId(item)).toBe("gap_010");
  });

  it("returns null when gap_999 is declared", () => {
    const item = gapFillItem([buildGap("gap_999")], gapBody("gap_999"));
    expect(nextGapId(item)).toBeNull();
  });

  it("returns null when gap_999 is only placed in the body", () => {
    const item = gapFillItem([buildGap("gap_998")], gapBody("gap_998", "gap_999"));
    expect(nextGapId(item)).toBeNull();
  });

  it("ignores ids that do not match gap_NNN", () => {
    const item = gapFillItem([buildGap("gap_x"), buildGap("gap_002")], gapBody("gap_002"));
    expect(nextGapId(item)).toBe("gap_003");
  });
});

describe("withNewGap", () => {
  it("seeds a gap_fill record from the trimmed seed text", () => {
    const item = gapFillItem([buildGap("gap_001", ["100"])], gapBody("gap_001"));
    const body = gapBody("gap_001", "gap_002");

    const result = withNewGap(item, body, "gap_002", "Paris");

    expect(result.body).toBe(body);
    expect(result.gaps).toHaveLength(2);
    expect(result.gaps[1]).toEqual({
      accepted_values: ["Paris"],
      automatic_values: [],
      correct_option_id: null,
      excluded_automatic_values: [],
      gap_id: "gap_002",
      options: [],
    });
  });

  it("seeds a gap_fill record with no accepted values from a blank seed", () => {
    const item = gapFillItem([buildGap("gap_001", ["100"])], gapBody("gap_001"));

    const result = withNewGap(item, gapBody("gap_001", "gap_002"), "gap_002", "  ");

    expect(result.gaps[1].gap_id).toBe("gap_002");
    expect(result.gaps[1].accepted_values).toEqual([]);
  });

  it("seeds an inline_choice record with one correct option from the seed", () => {
    const item = buildGapItem({
      body: gapBody("gap_001"),
      gaps: [
        buildGap("gap_001", [], {
          correct_option_id: "choice_001",
          options: [{ body: plainBody("ja"), choice_id: "choice_001" }],
        }),
      ],
      kind: "inline_choice",
    });
    const body = gapBody("gap_001", "gap_002");

    const result = withNewGap(item, body, "gap_002", "röd");

    expect(result.body).toBe(body);
    expect(result.gaps[1]).toEqual({
      accepted_values: [],
      automatic_values: [],
      correct_option_id: "choice_001",
      excluded_automatic_values: [],
      gap_id: "gap_002",
      options: [{ body: plainBody("röd"), choice_id: "choice_001" }],
    });
  });

  it("seeds an empty inline_choice record with no options and no correct option", () => {
    const item = buildGapItem({ body: gapBody("gap_001"), gaps: [buildGap("gap_001")], kind: "inline_choice" });

    const result = withNewGap(item, gapBody("gap_001", "gap_002"), "gap_002", "   ");

    expect(result.gaps[1]).toEqual({
      accepted_values: [],
      automatic_values: [],
      correct_option_id: null,
      excluded_automatic_values: [],
      gap_id: "gap_002",
      options: [],
    });
  });

  it("orders the new record by body placement, so its number follows the text", () => {
    const item = gapFillItem([buildGap("gap_002", ["gammal"])], gapBody("gap_002"));

    const result = withNewGap(item, gapBody("gap_001", "gap_002"), "gap_001", "ny");

    expect(result.gaps.map((gap) => gap.gap_id)).toEqual(["gap_001", "gap_002"]);
    expect(gapNumberIn(result.gaps, "gap_001")).toBe(1);
    expect(gapNumberIn(result.gaps, "gap_002")).toBe(2);
  });

  it("leaves existing gap records untouched", () => {
    const item = gapFillItem(
      [
        buildGap("gap_001", ["100"], {
          automatic_values: ["1000"],
          excluded_automatic_values: ["10o0"],
        }),
      ],
      gapBody("gap_001"),
    );

    const result = withNewGap(item, gapBody("gap_001", "gap_002"), "gap_002", "Paris");

    expect(result.gaps[0]).toEqual(item.gaps[0]);
    expect(result.gaps[0].automatic_values).toEqual(["1000"]);
    expect(result.gaps[0].excluded_automatic_values).toEqual(["10o0"]);
  });

  it("drops records the new body no longer places", () => {
    const item = gapFillItem(
      [buildGap("gap_001", ["100"]), buildGap("gap_003", ["borta"])],
      gapBody("gap_001", "gap_003"),
    );

    const result = withNewGap(item, gapBody("gap_001", "gap_002"), "gap_002", "Paris");

    expect(result.gaps.map((gap) => gap.gap_id)).toEqual(["gap_001", "gap_002"]);
  });

  it("returns the identical item when the body does not place the gap", () => {
    const item = gapFillItem([buildGap("gap_001", ["100"])], gapBody("gap_001"));
    const body = gapBody("gap_001");

    expect(withNewGap(item, body, "gap_002", "Paris")).toBe(item);
  });

  it("returns the identical item when the body places the gap twice", () => {
    const item = gapFillItem([], []);
    const body = gapBody("gap_002", "gap_002");

    expect(withNewGap(item, body, "gap_002", "Paris")).toBe(item);
  });

  it("returns the identical item when the item already declares the gap", () => {
    const item = gapFillItem([buildGap("gap_002")], gapBody("gap_002"));

    expect(withNewGap(item, gapBody("gap_002"), "gap_002", "Paris")).toBe(item);
  });

  it.each(["free_text", "single_choice"] as const)(
    "returns the identical item for a %s question",
    (kind) => {
      const item = buildGapItem({ body: [], gaps: [], kind });
      const body = gapBody("gap_001");

      expect(withNewGap(item, body, "gap_001", "Paris")).toBe(item);
    },
  );

  describe("key ownership", () => {
    it("marks a seeded gap on a new Lucktext teacher authored with a valid key", () => {
      const item = newTeacherItem("item_001", 1, "gap_fill");

      const created = withNewGap(item, gapBody("gap_001"), "gap_001", "varm");

      expect(created.answer_key.origin).toBe("teacher_authored");
      expect(created.gaps[0].accepted_values).toEqual(["varm"]);
      expect(hasInvalidAnswerKey(created)).toBe(false);
    });

    it("marks a seeded gap on a new dropdown Lucktext teacher authored", () => {
      const item = newTeacherItem("item_001", 1, "inline_choice");

      const created = withNewGap(item, gapBody("gap_001", "gap_002"), "gap_002", "röd");

      expect(created.answer_key.origin).toBe("teacher_authored");
      expect(created.gaps[1].correct_option_id).toBe("choice_001");
      expect(created.gaps[1].options).toEqual([{ body: plainBody("röd"), choice_id: "choice_001" }]);
    });

    it("keeps the absent origin when an empty insertion adds no key data", () => {
      const item = newTeacherItem("item_001", 1, "gap_fill");

      const created = withNewGap(item, gapBody("gap_001"), "gap_001", "  ");

      expect(created.answer_key.origin).toBe("absent");
      expect(created.gaps[0].accepted_values).toEqual([]);
    });

    it("keeps the teacher-authored key when an empty dropdown insertion adds no key data", () => {
      const item = buildGapItem({
        body: gapBody("gap_001"),
        gaps: [
          buildGap("gap_001", [], {
            correct_option_id: "choice_001",
            options: [{ body: plainBody("ja"), choice_id: "choice_001" }],
          }),
        ],
        kind: "inline_choice",
      });

      const created = withNewGap(item, gapBody("gap_001", "gap_002"), "gap_002", "");

      expect(created.gaps[1].correct_option_id).toBeNull();
      expect(created.gaps[1].options).toEqual([]);
      expect(created.answer_key.origin).toBe("teacher_authored");
      expect(hasInvalidAnswerKey(created)).toBe(false);
    });

    it("marks a seeded gap teacher authored when the key was ai_interpreted", () => {
      const item = buildGapItem({
        answer_key: { correct_choice_ids: [], match_pairs: [], origin: "ai_interpreted" },
        body: gapBody("gap_001"),
        gaps: [buildGap("gap_001", ["tolkad"])],
        kind: "gap_fill",
      });

      const created = withNewGap(item, gapBody("gap_001", "gap_002"), "gap_002", "ny");

      expect(created.answer_key.origin).toBe("teacher_authored");
    });

    it("keeps ai_interpreted when an empty insertion adds no key data", () => {
      const item = buildGapItem({
        answer_key: { correct_choice_ids: [], match_pairs: [], origin: "ai_interpreted" },
        body: gapBody("gap_001"),
        gaps: [buildGap("gap_001", ["tolkad"])],
        kind: "gap_fill",
      });

      const created = withNewGap(item, gapBody("gap_001", "gap_002"), "gap_002", "  ");

      expect(created.gaps[1].accepted_values).toEqual([]);
      expect(created.answer_key.origin).toBe("ai_interpreted");
    });

    it("keeps machine_proposed when an empty insertion adds no key data", () => {
      const item = buildGapItem({
        answer_key: { correct_choice_ids: [], match_pairs: [], origin: "machine_proposed" },
        body: gapBody("gap_001"),
        gaps: [buildGap("gap_001", ["tolkad"])],
        kind: "gap_fill",
      });

      const created = withNewGap(item, gapBody("gap_001", "gap_002"), "gap_002", "");

      expect(created.gaps[1].accepted_values).toEqual([]);
      expect(created.answer_key.origin).toBe("machine_proposed");
    });
  });
});

describe("createItemGap", () => {
  it("patches the item once as structural with withNewGap's transition", () => {
    const patchItem = vi.fn(
      (
        _itemId: string,
        _patch: (item: NativeExamItem) => NativeExamItem,
        _structural?: boolean,
      ): boolean => true,
    );
    const editing = useExamWorkspaceItemEdits(patchItem);
    const item = gapFillItem([buildGap("gap_001", ["100"])], gapBody("gap_001"));
    const body = gapBody("gap_001", "gap_002");

    editing.createItemGap("item_001", body, "gap_002", "Paris");

    expect(patchItem).toHaveBeenCalledTimes(1);
    const [itemId, patch, structural] = patchItem.mock.calls[0];
    expect(itemId).toBe("item_001");
    expect(structural).toBe(true);
    expect(patch(item)).toEqual(withNewGap(item, body, "gap_002", "Paris"));
    expect(patch(item).body).toBe(body);
  });
});

describe("changeItemShape", () => {
  it("patches the item once as structural with the Kort svar or Lucktext transition", () => {
    const patchItem = vi.fn(
      (
        _itemId: string,
        _patch: (item: NativeExamItem) => NativeExamItem,
        _structural?: boolean,
      ): boolean => true,
    );
    const editing = useExamWorkspaceItemEdits(patchItem);
    const item = gapFillItem([buildGap("gap_001", ["100"])], gapBody("gap_001"));

    editing.changeItemShape("item_001", "short_answer");

    expect(patchItem).toHaveBeenCalledTimes(1);
    const [itemId, patch, structural] = patchItem.mock.calls[0];
    expect(itemId).toBe("item_001");
    expect(structural).toBe(true);
    expect(patch(item)).toEqual(withShortAnswerShape(item));

    patchItem.mockClear();
    editing.changeItemShape("item_001", "gap_fill");
    const [, gapPatch, gapStructural] = patchItem.mock.calls[0];
    expect(gapStructural).toBe(true);
    expect(gapPatch(item)).toEqual(withGapTextShape(item));
  });
});
