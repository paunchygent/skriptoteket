import { describe, expect, it } from "vitest";

import type { NativeExamItem } from "../../../api/examWorkspace";
import { examWorkspaceItemReadiness } from "./examWorkspaceItemReadiness";
import { buildChoiceItem } from "./examWorkspaceItemReadiness.specSupport";
import { buildGap } from "./examWorkspaceKeyedItems.specSupport";
import { buildMatchingItem } from "./examWorkspaceMatchingItem.specSupport";
import { plainBody } from "./examWorkspaceRichText";

describe("export-only content readiness", () => {
  function dropdown(): NativeExamItem {
    return buildChoiceItem({
      kind: "inline_choice",
      choices: [],
      answer_key: { origin: "teacher_authored", correct_choice_ids: [], match_pairs: [] },
      body: [{ heading_level: null, segments: [{ kind: "gap", gap_id: "gap_001" }] }],
      gaps: [buildGap("gap_001", [], {
        correct_option_id: "option_001",
        options: [
          { choice_id: "option_001", body: plainBody("Syre") },
          { choice_id: "option_002", body: plainBody("Järn") },
        ],
      })],
    });
  }

  it("blocks a dropdown without a key but accepts the keyed dropdown", () => {
    const item = dropdown();
    expect(examWorkspaceItemReadiness(item)).toEqual([]);
    item.answer_key.origin = "absent";
    item.gaps[0]!.correct_option_id = null;
    expect(examWorkspaceItemReadiness(item)).toEqual(["missing_answer_key"]);
  });

  it("blocks a heading in any paragraph of any dropdown option", () => {
    const item = dropdown();
    item.gaps[0]!.options[1]!.body.push({
      heading_level: 2, segments: [{ kind: "text", marks: [], text: "Rubrik" }],
    });
    expect(examWorkspaceItemReadiness(item)).toEqual(["inline_choice_option_heading"]);
    item.gaps[0]!.options[1]!.body[1]!.heading_level = null;
    expect(examWorkspaceItemReadiness(item)).toEqual([]);
  });

  it.each(["", " \n\t "])("blocks a blank dropdown option %j", (text) => {
    const item = dropdown();
    item.gaps[0]!.options[1]!.body = plainBody(text);
    expect(examWorkspaceItemReadiness(item)).toEqual(["empty_gap_option"]);
  });

  it.each(["single_choice", "multiple_response"] as const)(
    "blocks whitespace-only %s choices but accepts text after a blank paragraph", (kind) => {
      const item = buildChoiceItem({ kind });
      item.choices[1]!.body = plainBody(" \n\t ");
      expect(examWorkspaceItemReadiness(item)).toEqual(["empty_choice"]);
      item.choices[1]!.body.push(...plainBody(" Järn "));
      expect(examWorkspaceItemReadiness(item)).toEqual([]);
    },
  );

  it.each(["match_left", "match_right"] as const)(
    "blocks whitespace-only entries in %s but accepts nonblank text", (side) => {
      const item = buildMatchingItem();
      item[side][0]!.body = plainBody(" \n\t ");
      expect(examWorkspaceItemReadiness(item)).toEqual(["empty_match_entry"]);
      item[side][0]!.body.push(...plainBody(" Text "));
      expect(examWorkspaceItemReadiness(item)).toEqual([]);
    },
  );
});

describe("export readiness reasons", () => {
  it("reports only the reasons for questions that stop an export", () => {
    const ready = buildChoiceItem();
    const partial = buildChoiceItem({
      choices: [],
      gaps: [buildGap("gap_001")],
      item_id: "item_002",
      kind: "gap_fill",
      match_left: [],
      match_right: [],
      points: null,
      sequence: 2,
    });

    expect(examWorkspaceItemReadiness(ready)).toEqual([]);
    expect(examWorkspaceItemReadiness(partial)).toEqual(["partial_gap_key", "missing_points"]);
  });

  it("reports the save-refused states as reasons", () => {
    const item = buildChoiceItem({
      choices: [
        { choice_id: "choice_001", body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "Syre" }] }] },
        { choice_id: "choice_002", body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "" }] }] },
      ],
      points: -1,
    });

    expect(examWorkspaceItemReadiness(item)).toEqual(["negative_points", "empty_choice"]);
  });
});
