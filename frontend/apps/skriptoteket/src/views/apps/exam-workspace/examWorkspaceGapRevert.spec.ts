/**
 * Exam workspace gap revert and restore.
 *
 * Expected behavior (TASK-SKRIPT-40-04-13 items 1-3, unit H3):
 *   `withGapReverted` turns a gap's placement into a text run holding the
 *   gap's first accepted answer (Lucktext) or its correct option's text
 *   (dropdown), linked by a new kept id, and moves the gap's full record
 *   into `kept_gaps` under that id. `withKeptGapRestored` turns the whole
 *   contiguous kept word back into the gap: the word's current text becomes
 *   the first answer (or the correct option's text) and the kept answers and
 *   options come back, so an unedited word restores the gap exactly apart
 *   from the gap id. A word split by formatting restores as one gap from the
 *   joined text; separate runs with the same id lose the link. Both results
 *   pass the frontend save rules.
 */

import { describe, expect, it } from "vitest";

import type {
  NativeExamBodyParagraph,
  NativeExamBodySegment,
  NativeExamItem,
} from "../../../api/examWorkspace";
import {
  dropdownGapsWithoutCorrectOption,
  hasInvalidAnswerKey,
  isPartiallyKeyedGapItem,
} from "./examWorkspaceAnswerKeyRules";
import {
  nextKeptGapId,
  withGapReverted,
  withKeptGapRestored,
} from "./examWorkspaceKeptGapEdits";
import { buildGap } from "./examWorkspaceKeyedItems.specSupport";
import { buildGapItem } from "./ExamWorkspaceBodyEditor.specSupport";
import { bodyText, plainBody } from "./examWorkspaceRichText";

function textRun(value: string, keptGapId: string | null = null): NativeExamBodySegment {
  return { kind: "text", marks: [], text: value, kept_gap_id: keptGapId };
}

function luckaItem(): NativeExamItem {
  return buildGapItem({
    body: [
      {
        heading_level: null,
        segments: [
          textRun("Hon heter "),
          { gap_id: "gap_001", kind: "gap" },
          textRun(" och "),
          { gap_id: "gap_002", kind: "gap" },
          textRun(" ."),
        ],
      },
    ],
    gaps: [
      {
        ...buildGap("gap_001", ["Stockholm", "Sthlm", "Hufvudstaden"]),
        automatic_values: ["Stockhom"],
        excluded_automatic_values: ["Stokholm"],
      },
      buildGap("gap_002", ["Oslo"]),
    ],
  });
}

function dropdownItem(): NativeExamItem {
  return buildGapItem({
    body: [
      {
        heading_level: null,
        segments: [textRun("Välj "), { gap_id: "gap_001", kind: "gap" }, textRun(" nu.")],
      },
    ],
    gaps: [
      buildGap("gap_001", [], {
        correct_option_id: "choice_002",
        options: [
          { body: plainBody("röd"), choice_id: "choice_001" },
          { body: plainBody("blå"), choice_id: "choice_002" },
          { body: plainBody("grön"), choice_id: "choice_003" },
        ],
      }),
    ],
    kind: "inline_choice",
  });
}

/** The source body with one gap placement renamed to its restored id. */
function restoredBody(source: NativeExamItem, oldGapId: string, newGapId: string): NativeExamBodyParagraph[] {
  return source.body.map((paragraph) => ({
    ...paragraph,
    segments: paragraph.segments.map((segment) =>
      segment.kind === "gap" && segment.gap_id === oldGapId
        ? { ...segment, gap_id: newGapId }
        : segment,
    ),
  }));
}

/** The frontend save gate for gap keys: no invalid key, no partial key, no keyless dropdown. */
function expectSaveable(item: NativeExamItem): void {
  expect(hasInvalidAnswerKey(item)).toBe(false);
  expect(isPartiallyKeyedGapItem(item)).toBe(false);
  expect(dropdownGapsWithoutCorrectOption(item)).toEqual([]);
}

describe("nextKeptGapId", () => {
  it("names gap_001 when the item holds no gaps and the body places none", () => {
    expect(nextKeptGapId(buildGapItem({ body: [], gaps: [], kept_gaps: [] }))).toBe("gap_001");
  });

  it("names one above the highest gap, kept gap and placed kept link", () => {
    const item = luckaItem();
    const kept = withGapReverted(item, "gap_001");
    const keptId = kept.kept_gaps[0]?.gap_id ?? "";
    expect(nextKeptGapId(kept)).toBe("gap_004");
    expect(keptId).toBe("gap_003");
  });

  it("returns null when gap_999 is taken by a kept record", () => {
    const item = buildGapItem({ gaps: [], kept_gaps: [buildGap("gap_999", ["x"])] });
    expect(nextKeptGapId(item)).toBeNull();
  });
});

describe("withGapReverted", () => {
  it("reverts a Lucktext gap to its first answer with the other answers kept", () => {
    const source = luckaItem();

    const result = withGapReverted(source, "gap_001");

    expect(result.gaps.map((gap) => gap.gap_id)).toEqual(["gap_002"]);
    expect(result.kept_gaps).toHaveLength(1);
    const keptId = result.kept_gaps[0]?.gap_id ?? "";
    expect(keptId).toMatch(/^gap_\d{3}$/);
    expect(keptId).not.toBe("gap_001");
    expect(result.body[0]?.segments).toEqual([
      textRun("Hon heter "),
      textRun("Stockholm", keptId),
      textRun(" och "),
      { gap_id: "gap_002", kind: "gap" },
      textRun(" ."),
    ]);
    expect(result.kept_gaps[0]).toEqual({ ...source.gaps[0], gap_id: keptId });
    expect(result.kept_gaps[0]?.accepted_values).toEqual(["Stockholm", "Sthlm", "Hufvudstaden"]);
    expect(result.kept_gaps[0]?.automatic_values).toEqual(["Stockhom"]);
    expect(result.kept_gaps[0]?.excluded_automatic_values).toEqual(["Stokholm"]);
    expectSaveable(result);
    expect(source.gaps).toHaveLength(2);
  });

  it("reverts a dropdown gap to its correct option's text with the other options kept", () => {
    const source = dropdownItem();

    const result = withGapReverted(source, "gap_001");

    expect(result.gaps).toEqual([]);
    expect(result.kept_gaps).toHaveLength(1);
    const keptId = result.kept_gaps[0]?.gap_id ?? "";
    expect(result.body[0]?.segments).toEqual([
      textRun("Välj "),
      textRun("blå", keptId),
      textRun(" nu."),
    ]);
    expect(result.kept_gaps[0]).toEqual({ ...source.gaps[0], gap_id: keptId });
    expect(result.kept_gaps[0]?.correct_option_id).toBe("choice_002");
    expect(result.kept_gaps[0]?.options.map((option) => bodyText(option.body))).toEqual([
      "röd",
      "blå",
      "grön",
    ]);
    expectSaveable(result);
  });

  it("refuses an unknown gap, a gap without an answer and a non-gap kind", () => {
    const source = luckaItem();
    expect(withGapReverted(source, "gap_009")).toBe(source);
    const unanswered = buildGapItem({
      body: [{ heading_level: null, segments: [{ gap_id: "gap_001", kind: "gap" }] }],
      gaps: [buildGap("gap_001")],
    });
    expect(withGapReverted(unanswered, "gap_001")).toBe(unanswered);
    const noCorrect = buildGapItem({
      body: [{ heading_level: null, segments: [{ gap_id: "gap_001", kind: "gap" }] }],
      gaps: [buildGap("gap_001", [], { correct_option_id: null, options: [] })],
      kind: "inline_choice",
    });
    expect(withGapReverted(noCorrect, "gap_001")).toBe(noCorrect);
    const freeText = buildGapItem({ gaps: [], kind: "free_text" });
    expect(withGapReverted(freeText, "gap_001")).toBe(freeText);
  });

  it("refuses to revert when no kept id is free", () => {
    const source = buildGapItem({
      body: [{ heading_level: null, segments: [{ gap_id: "gap_001", kind: "gap" }] }],
      gaps: [buildGap("gap_001", ["x"])],
      kept_gaps: [buildGap("gap_999", ["y"])],
    });
    expect(withGapReverted(source, "gap_001")).toBe(source);
  });
});

describe("withKeptGapRestored", () => {
  it("restores an unedited word to its exact gap apart from the gap id", () => {
    const source = luckaItem();
    const reverted = withGapReverted(source, "gap_001");
    const keptId = reverted.kept_gaps[0]?.gap_id ?? "";

    const result = withKeptGapRestored(reverted, keptId, 0);

    expect(result.kept_gaps).toEqual([]);
    expect(result.gaps).toEqual([{ ...source.gaps[0], gap_id: keptId }, source.gaps[1]]);
    expect(result.body).toEqual(restoredBody(source, "gap_001", keptId));
    expectSaveable(result);
  });

  it("restores an unedited dropdown word with its options untouched", () => {
    const source = dropdownItem();
    const reverted = withGapReverted(source, "gap_001");
    const keptId = reverted.kept_gaps[0]?.gap_id ?? "";

    const result = withKeptGapRestored(reverted, keptId, 0);

    expect(result.gaps).toEqual([{ ...source.gaps[0], gap_id: keptId }]);
    expect(result.body).toEqual(restoredBody(source, "gap_001", keptId));
    expectSaveable(result);
  });

  it("makes an edited word the first answer and keeps the rest", () => {
    const reverted = withGapReverted(luckaItem(), "gap_001");
    const keptId = reverted.kept_gaps[0]?.gap_id ?? "";
    const edited: NativeExamItem = {
      ...reverted,
      body: [
        {
          heading_level: null,
          segments: [
            textRun("Hon heter "),
            textRun("Göteborg", keptId),
            textRun(" och "),
            { gap_id: "gap_002", kind: "gap" },
            textRun(" ."),
          ],
        },
      ],
    };

    const result = withKeptGapRestored(edited, keptId, 0);

    expect(result.kept_gaps).toEqual([]);
    expect(result.gaps[0]?.accepted_values).toEqual(["Göteborg", "Sthlm", "Hufvudstaden"]);
    expect(result.gaps[0]?.automatic_values).toEqual(["Stockhom"]);
    expect(result.body[0]?.segments[1]).toEqual({ gap_id: keptId, kind: "gap" });
    expectSaveable(result);
  });

  it("makes an edited dropdown word the correct option's text", () => {
    const reverted = withGapReverted(dropdownItem(), "gap_001");
    const keptId = reverted.kept_gaps[0]?.gap_id ?? "";
    const edited: NativeExamItem = {
      ...reverted,
      body: [
        {
          heading_level: null,
          segments: [textRun("Välj "), textRun("gul", keptId), textRun(" nu.")],
        },
      ],
    };

    const result = withKeptGapRestored(edited, keptId, 0);

    expect(result.gaps).toHaveLength(1);
    expect(result.gaps[0]?.correct_option_id).toBe("choice_002");
    expect(result.gaps[0]?.options.map((option) => bodyText(option.body))).toEqual([
      "röd",
      "gul",
      "grön",
    ]);
    expectSaveable(result);
  });

  it("restores a word split by bold as one gap from the joined text", () => {
    const reverted = withGapReverted(luckaItem(), "gap_001");
    const keptId = reverted.kept_gaps[0]?.gap_id ?? "";
    const split: NativeExamItem = {
      ...reverted,
      body: [
        {
          heading_level: null,
          segments: [
            textRun("Hon heter "),
            { kind: "text", marks: ["bold"], text: "Stock", kept_gap_id: keptId },
            textRun("holm", keptId),
            textRun(" och "),
            { gap_id: "gap_002", kind: "gap" },
            textRun(" ."),
          ],
        },
      ],
    };

    const result = withKeptGapRestored(split, keptId, 0);

    expect(result.gaps).toEqual([{ ...luckaItem().gaps[0], gap_id: keptId }, luckaItem().gaps[1]]);
    expect(result.body).toEqual(restoredBody(luckaItem(), "gap_001", keptId));
  });

  it("restores the first contiguous word and drops the link on separate runs", () => {
    const reverted = withGapReverted(luckaItem(), "gap_001");
    const keptId = reverted.kept_gaps[0]?.gap_id ?? "";
    const forked: NativeExamItem = {
      ...reverted,
      body: [
        {
          heading_level: null,
          segments: [
            textRun("Hon heter "),
            textRun("ett", keptId),
            textRun(" och "),
            { gap_id: "gap_002", kind: "gap" },
            textRun(" plus "),
            textRun("två", keptId),
            textRun(" ."),
          ],
        },
      ],
    };

    const result = withKeptGapRestored(forked, keptId, 0);

    expect(result.gaps[0]?.accepted_values[0]).toBe("ett");
    expect(result.body).toEqual([
      {
        heading_level: null,
        segments: [
          textRun("Hon heter "),
          { gap_id: keptId, kind: "gap" },
          textRun(" och "),
          { gap_id: "gap_002", kind: "gap" },
          textRun(" plus "),
          textRun("två"),
          textRun(" ."),
        ],
      },
    ]);
    expect(result.kept_gaps).toEqual([]);
  });

  it("refuses an unknown kept id and a kept record no run names", () => {
    const reverted = withGapReverted(luckaItem(), "gap_001");
    expect(withKeptGapRestored(reverted, "gap_009", 0)).toBe(reverted);
    const orphaned: NativeExamItem = { ...reverted, body: luckaItem().body };
    expect(withKeptGapRestored(orphaned, reverted.kept_gaps[0]?.gap_id ?? "", 0)).toBe(orphaned);
  });

  it("keeps the other gap's record and order when restoring between gaps", () => {
    const both: NativeExamItem = (() => {
      const first = withGapReverted(luckaItem(), "gap_001");
      return withGapReverted(first, "gap_002");
    })();
    const firstKeptId = both.kept_gaps[0]?.gap_id ?? "";
    const secondKeptId = both.kept_gaps[1]?.gap_id ?? "";
    expect(firstKeptId).not.toBe(secondKeptId);

    const result = withKeptGapRestored(both, secondKeptId, 0);

    expect(result.gaps.map((gap) => gap.gap_id)).toEqual([secondKeptId]);
    expect(result.kept_gaps.map((gap) => gap.gap_id)).toEqual([firstKeptId]);
    expect(result.body[0]?.segments[3]).toEqual({ gap_id: secondKeptId, kind: "gap" });
    expectSaveable(result);
  });
});

describe("withKeptGapRestored at a clicked block", () => {
  function splitKeptItem(): { item: NativeExamItem; keptId: string } {
    const reverted = withGapReverted(luckaItem(), "gap_001");
    const keptId = reverted.kept_gaps[0]?.gap_id ?? "";
    const item: NativeExamItem = {
      ...reverted,
      body: [
        {
          heading_level: null,
          segments: [
            textRun("Hon heter "),
            textRun("ett", keptId),
            textRun(" och "),
            { gap_id: "gap_002", kind: "gap" },
            textRun(" plus "),
            textRun("två", keptId),
            textRun(" ."),
          ],
        },
      ],
    };
    return { item, keptId };
  }

  it("restores the second block the teacher clicked, not the first one", () => {
    const { item, keptId } = splitKeptItem();

    const result = withKeptGapRestored(item, keptId, 1);

    expect(result.gaps.find((gap) => gap.gap_id === keptId)?.accepted_values[0]).toBe("två");
    expect(result.body).toEqual([
      {
        heading_level: null,
        segments: [
          textRun("Hon heter "),
          textRun("ett"),
          textRun(" och "),
          { gap_id: "gap_002", kind: "gap" },
          textRun(" plus "),
          { gap_id: keptId, kind: "gap" },
          textRun(" ."),
        ],
      },
    ]);
    expect(result.kept_gaps).toEqual([]);
    expectSaveable(result);
  });

  it("restores the first block for block index 0", () => {
    const { item, keptId } = splitKeptItem();

    const result = withKeptGapRestored(item, keptId, 0);

    expect(result.gaps[0]?.accepted_values[0]).toBe("ett");
    expect(result.body[0]?.segments[1]).toEqual({ gap_id: keptId, kind: "gap" });
    expectSaveable(result);
  });

  it("restores a clicked block in a later paragraph", () => {
    const reverted = withGapReverted(luckaItem(), "gap_001");
    const keptId = reverted.kept_gaps[0]?.gap_id ?? "";
    const item: NativeExamItem = {
      ...reverted,
      body: [
        { heading_level: null, segments: [textRun("Först "), textRun("ett", keptId)] },
        { heading_level: null, segments: [textRun("Sedan "), textRun("två", keptId)] },
      ],
    };

    const result = withKeptGapRestored(item, keptId, 1);

    expect(result.gaps.find((gap) => gap.gap_id === keptId)?.accepted_values[0]).toBe("två");
    expect(result.body[0]?.segments).toEqual([textRun("Först "), textRun("ett")]);
    expect(result.body[1]?.segments).toEqual([textRun("Sedan "), { gap_id: keptId, kind: "gap" }]);
    expect(result.kept_gaps).toEqual([]);
    expectSaveable(result);
  });

  it("falls back to the first block for an out-of-range block index", () => {
    const { item, keptId } = splitKeptItem();

    const result = withKeptGapRestored(item, keptId, 7);

    expect(result.gaps[0]?.accepted_values[0]).toBe("ett");
    expect(result.kept_gaps).toEqual([]);
    expectSaveable(result);
  });
});
