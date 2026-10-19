import { describe, expect, it } from "vitest";

import type { NativeExamItem } from "../../../api/examWorkspace";
import { buildDocument } from "../ExamWorkspaceSlice.specSupport";
import {
  examWorkspaceBlockerEntries,
  examWorkspaceTitleBlockerEntries,
  withoutEmptyOptions,
  withoutOptionHeadings,
} from "./examWorkspaceBlockers";
import { examWorkspaceItemReadiness } from "./examWorkspaceItemReadiness";
import type { ExamWorkspaceReadinessReason } from "./examWorkspaceItemReadiness";
import { reviewed } from "./examWorkspaceItemEdits";
import { buildMatchingItemWithPairs } from "./examWorkspaceMatchingItem.specSupport";
import { buildGap, choiceItem } from "./examWorkspaceKeyedItems.specSupport";
import { examWorkspaceListEntries } from "./examWorkspaceListEntries";
import { plainBody } from "./examWorkspaceRichText";

const BLANK = plainBody(" ");

function withId(item: NativeExamItem, itemId: string, sequence: number): NativeExamItem {
  return { ...item, item_id: itemId, sequence };
}

/** A teacher-checked single choice keyed on choice_001, so only what a test changes blocks. */
function choice(itemId = "item_001", sequence = 1): NativeExamItem {
  return withId(reviewed(choiceItem("single_choice", "teacher_authored", ["choice_001"], null)), itemId, sequence);
}

function rullista(options: NativeExamItem["gaps"][number]["options"], key: string | null): NativeExamItem {
  return {
    ...choice(),
    choices: [],
    body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "Hon " }, { gap_id: "gap_001", kind: "gap" }] }],
    gaps: [buildGap("gap_001", [], { correct_option_id: key, options })],
    kind: "inline_choice",
  };
}

function rows(
  items: NativeExamItem[],
  server: Record<string, ExamWorkspaceReadinessReason[]> = {},
  converting: string[] = [],
) {
  const document = { ...buildDocument(), items, parents: [] };
  const readiness = Object.fromEntries(items.map((item) => [item.item_id, examWorkspaceItemReadiness(item)]));
  const entries = examWorkspaceListEntries(document, readiness, new Set(converting));
  return examWorkspaceBlockerEntries(
    entries,
    items,
    readiness,
    server,
  );
}

describe("examWorkspaceBlockerEntries", () => {
  it("lists nothing for an exam that exports", () => {
    expect(rows([choice()])).toEqual([]);
  });

  it("gives one row per question in the list's words, its first reason, with the fix and the field", () => {
    const unbuilt = {
      ...choice("item_001", 1),
      answer_key: { correct_choice_ids: [], match_pairs: [], origin: "machine_proposed" as const },
      points: null,
      review: { confidence: null, parse_origin: "source_fallback" as const, reasons: [], state: "review_required" as const },
    };
    const noPoints = { ...choice("item_002", 2), points: null };

    expect(rows([unbuilt, noPoints])).toEqual([
      {
        fix: "review",
        focus: '[data-test="exam-workspace-review"]',
        itemId: "item_001",
        label: "1",
        problem: "kunde inte konverteras",
        reason: "unbuilt_question",
      },
      {
        fix: null,
        focus: '[data-test="exam-workspace-item-points-input"]',
        itemId: "item_002",
        label: "2",
        problem: "poäng saknas",
        reason: "missing_points",
      },
    ]);
  });

  it("leads an empty question text and a gap question without gaps to the Frågetext surface, with no fix", () => {
    const emptyText = { ...choice("item_001", 1), body: [] };
    const gapless = {
      ...choice("item_002", 2),
      body: plainBody("Fyll i."),
      choices: [],
      kind: "gap_fill" as const,
    };
    const both = { ...gapless, body: plainBody("  "), item_id: "item_003", sequence: 3 };

    expect(rows([emptyText, gapless, both])).toEqual([
      {
        fix: null,
        focus: '[data-test="exam-workspace-body-editor-surface"]',
        itemId: "item_001",
        label: "1",
        problem: "Frågetexten är tom.",
        reason: "empty_question_text",
      },
      {
        fix: null,
        focus: '[data-test="exam-workspace-body-editor-surface"]',
        itemId: "item_002",
        label: "2",
        problem: "Frågan saknar luckor.",
        reason: "no_gaps",
      },
      expect.objectContaining({ itemId: "item_003", problem: "Frågetexten är tom." }),
    ]);
  });

  it("leads an empty gap to its gap chip with no one-click fix", () => {
    const item: NativeExamItem = {
      ...choice("item_001", 1),
      choices: [],
      body: [{ heading_level: null, segments: [
        { kind: "text", marks: [], text: "Vatten kokar vid " },
        { gap_id: "gap_001", kind: "gap" },
        { kind: "text", marks: [], text: " grader." },
      ] }],
      gaps: [buildGap("gap_001", [])],
      kind: "gap_fill" as const,
    };

    expect(rows([item])).toEqual([
      {
        fix: null,
        focus: '[data-gap-id="gap_001"]',
        itemId: "item_001",
        label: "1",
        problem: "lucka utan svar",
        reason: "partial_gap_key",
      },
    ]);
  });

  it("offers Godkänn for an unapproved AI key and Föreslå facit for a missing key", () => {
    const proposed = withId(choiceItem("single_choice", "machine_proposed", ["choice_002"], null), "item_001", 1);
    const absent = withId(reviewed(choiceItem("multiple_response", "absent", [], null)), "item_002", 2);

    expect(rows([proposed, absent]).map(({ fix, focus, problem }) => ({ fix, focus, problem }))).toEqual([
      { fix: "approve", focus: '[data-test="exam-workspace-review"]', problem: "facit ej granskat" },
      {
        fix: "suggest_key",
        focus: '[data-test="exam-workspace-choice-correct-choice_001"]',
        problem: "facit saknas",
      },
    ]);
  });

  it("takes a reason only the server gave, and none for a question the client and server both pass", () => {
    const items = [choice("item_001", 1), choice("item_002", 2)];

    expect(rows(items, { item_002: ["empty_match_entry" as never] })).toEqual([
      expect.objectContaining({ itemId: "item_002", label: "2", problem: "tom rad eller kategori", fix: null }),
    ]);
  });

  it("names a question that still converts without offering a fix or a field", () => {
    const converting = {
      ...choice(),
      review: { confidence: null, parse_origin: "source_fallback" as const, reasons: [], state: "review_required" as const },
    };

    expect(rows([converting], {}, ["item_001"])).toEqual([
      expect.objectContaining({ fix: null, focus: null, problem: "konverteras fortfarande" }),
    ]);
  });

  it("offers Ta bort tomma only when two filled choices and the key survive the removal", () => {
    const oneEmpty = { ...choice(), choices: [...choice().choices.slice(0, 2), { body: BLANK, choice_id: "choice_003" }] };
    const keyedEmpty = { ...oneEmpty, answer_key: { ...oneEmpty.answer_key, correct_choice_ids: ["choice_003"] } };
    const tooFew = { ...choice(), choices: [choice().choices[0]!, { body: BLANK, choice_id: "choice_003" }] };

    expect(rows([oneEmpty])[0]).toMatchObject({
      fix: "remove_empty",
      focus: '[data-test^="exam-workspace-choice-text-choice_003"]',
      problem: "tomt svarsalternativ",
    });
    expect(rows([keyedEmpty])[0]?.fix).toBeNull();
    expect(rows([tooFew])[0]?.fix).toBeNull();
  });

  it("offers Ta bort tomma for a dropdown only when its key and two filled options stay", () => {
    const options = [
      { body: plainBody("är"), choice_id: "choice_001" },
      { body: plainBody("var"), choice_id: "choice_002" },
      { body: BLANK, choice_id: "choice_003" },
    ];

    expect(rows([rullista(options, "choice_001")])[0]).toMatchObject({
      fix: "remove_empty",
      focus: '[data-gap-id="gap_001"]',
      problem: "tomt alternativ i rullista",
    });
    expect(rows([rullista(options, "choice_003")])[0]?.fix).toBeNull();
    expect(rows([rullista([options[0]!, options[2]!], "choice_001")])[0]?.fix).toBeNull();
  });

  it("offers Ta bort rubrikformat for a heading in a dropdown option and leads to its gap", () => {
    const heading = [
      { body: [{ ...plainBody("är")[0]!, heading_level: 2 as const }], choice_id: "choice_001" },
      { body: plainBody("var"), choice_id: "choice_002" },
    ];

    expect(rows([rullista(heading, "choice_001")])[0]).toMatchObject({
      fix: "strip_headings",
      focus: '[data-gap-id="gap_001"]',
      problem: "rubrik i rullista",
    });
  });

  it("leads a too-short dropdown to its first short gap with no one-click fix", () => {
    const item = rullista(
      [{ body: plainBody("är"), choice_id: "choice_001" }, { body: plainBody("var"), choice_id: "choice_002" }],
      "choice_001",
    );
    item.body = [{
      heading_level: null,
      segments: [
        { kind: "gap", gap_id: "gap_001" }, { kind: "gap", gap_id: "gap_002" }, { kind: "gap", gap_id: "gap_003" },
      ],
    }];
    item.gaps = [
      item.gaps[0]!,
      buildGap("gap_002", [], { correct_option_id: "choice_001", options: [{ body: plainBody("är"), choice_id: "choice_001" }] }),
      buildGap("gap_003", [], { correct_option_id: "choice_001", options: [{ body: plainBody("är"), choice_id: "choice_001" }] }),
    ];

    expect(rows([item])[0]).toMatchObject({
      fix: null,
      focus: '[data-gap-id="gap_002"]',
      problem: "rullista med färre än två alternativ",
      reason: "too_few_gap_options",
    });
  });

  it("leads a dropdown without a correct option to the first unkeyed gap, not the first gap", () => {
    const options = [{ body: plainBody("är"), choice_id: "choice_001" }, { body: plainBody("var"), choice_id: "choice_002" }];
    const item = rullista(options, "choice_001");
    item.body = [{
      heading_level: null,
      segments: [{ kind: "gap", gap_id: "gap_001" }, { kind: "gap", gap_id: "gap_002" }, { kind: "gap", gap_id: "gap_003" }],
    }];
    item.gaps = [
      item.gaps[0]!,
      buildGap("gap_002", [], { correct_option_id: null, options }),
      buildGap("gap_003", [], { correct_option_id: null, options }),
    ];

    expect(rows([item])[0]).toMatchObject({
      fix: null,
      focus: '[data-gap-id="gap_002"]',
      problem: "rullista utan rätt svar",
      reason: "gap_without_correct_option",
    });
  });

  it("names an earlier reason first when the dropdown also lacks points", () => {
    const item = { ...rullista([{ body: plainBody("är"), choice_id: "choice_001" }], "choice_001"), points: null };
    expect(rows([item])[0]).toMatchObject({ reason: "missing_points" });
  });
});

describe("export blocker fixes", () => {
  it("removes the empty choices and dropdown options and clears the blocker, keeping the key", () => {
    const item = rullista(
      [
        { body: plainBody("är"), choice_id: "choice_001" },
        { body: BLANK, choice_id: "choice_002" },
        { body: plainBody("var"), choice_id: "choice_003" },
      ],
      "choice_003",
    );

    const fixed = withoutEmptyOptions(item);

    expect(fixed.gaps[0]!.options.map((option) => option.choice_id)).toEqual(["choice_001", "choice_003"]);
    expect(fixed.gaps[0]!.correct_option_id).toBe("choice_003");
    expect(examWorkspaceItemReadiness(fixed)).toEqual([]);
  });

  it("makes every dropdown option plain text and clears the blocker", () => {
    const item = rullista(
      [
        { body: [{ ...plainBody("är")[0]!, heading_level: 1 as const }], choice_id: "choice_001" },
        { body: [{ ...plainBody("var")[0]!, heading_level: 3 as const }], choice_id: "choice_002" },
      ],
      "choice_001",
    );

    const fixed = withoutOptionHeadings(item);

    expect(fixed.gaps[0]!.options.flatMap((option) => option.body.map((paragraph) => paragraph.heading_level)))
      .toEqual([null, null]);
    expect(fixed.gaps[0]!.options.map((option) => option.body[0]!.segments)).toEqual(
      item.gaps[0]!.options.map((option) => option.body[0]!.segments),
    );
    expect(examWorkspaceItemReadiness(fixed)).toEqual([]);
  });

  describe("incomplete_match_key focus", () => {
    const focusOf = (pairs: Array<[number, number]>) => {
      const [entry] = rows([buildMatchingItemWithPairs(pairs)]);
      expect(entry?.reason).toBe("incomplete_match_key");
      return entry!.focus!;
    };

    it("targets the ticks of the row without a tick, not the first row", () => {
      const focus = focusOf([[1, 2]]);
      expect(focus).toBe('[data-test^="exam-workspace-match-tick-left_002-"]');
      expect(focus).not.toContain("left_001");
    });

    it("targets the first row when that is the unticked one", () => {
      expect(focusOf([[2, 1], [3, 3]])).toBe('[data-test^="exam-workspace-match-tick-left_001-"]');
    });
  });
});

describe("examWorkspaceTitleBlockerEntries", () => {
  it("gives the title row when the server judged the title without text", () => {
    expect(examWorkspaceTitleBlockerEntries(true)).toEqual([
      {
        fix: null,
        focus: '[data-test="exam-workspace-metadata-title"]',
        itemId: null,
        label: null,
        problem: "Ge provet en titel med bokstäver eller siffror",
        reason: "title_without_text",
      },
    ]);
  });

  it("gives no row while the title is not judged without text", () => {
    expect(examWorkspaceTitleBlockerEntries(false)).toEqual([]);
  });
});

describe("ordering blocker rows", () => {
  function ordering(texts: string[]): NativeExamItem {
    return {
      ...choice(),
      answer_key: { correct_choice_ids: [], match_pairs: [], origin: "teacher_authored" },
      choices: texts.map((text, index) => ({ choice_id: `choice_00${index + 1}`, body: plainBody(text) })),
      kind: "ordering",
      print_order: [],
    };
  }

  it("points too few steps at the add-step button with no fix", () => {
    expect(rows([ordering(["Ensam"])])).toEqual([
      {
        fix: null,
        focus: '[data-test="exam-workspace-ordering-add-step"]',
        itemId: "item_001",
        label: "1",
        problem: "för få steg",
        reason: "ordering_too_few_steps",
      },
    ]);
  });

  it("points an empty step at its own text field and never offers remove_empty", () => {
    const [row, ...rest] = rows([ordering(["Först", " ", "", "Sist"])]);
    expect(rest).toEqual([]);
    expect(row).toMatchObject({
      fix: null,
      focus: '[data-test^="exam-workspace-ordering-step-text-choice_002"]',
      problem: "tomt steg",
      reason: "empty_ordering_step",
    });
  });

  it("keeps the remove_empty fix for a single_choice empty option", () => {
    const item = choice();
    item.choices = [...item.choices, { choice_id: "choice_004", body: BLANK }];
    expect(rows([item])[0]).toMatchObject({ fix: "remove_empty", reason: "empty_choice" });
  });
});
