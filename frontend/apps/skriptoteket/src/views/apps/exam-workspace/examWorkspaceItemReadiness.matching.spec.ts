import { describe, expect, it } from "vitest";

import { examWorkspaceItemReadiness } from "./examWorkspaceItemReadiness";
import {
  buildMatchingItem,
  buildMatchingItemWithDistractor,
  buildMatchingItemWithPairs,
} from "./examWorkspaceMatchingItem.specSupport";
import { plainBody } from "./examWorkspaceRichText";

describe("examWorkspaceItemReadiness for matching items", () => {
  it("reports nothing for a fully keyed matching item", () => {
    expect(examWorkspaceItemReadiness(buildMatchingItem())).toEqual([]);
  });

  it("reports an absent key as a missing answer key, not as an incomplete one", () => {
    const item = buildMatchingItemWithPairs([]);

    expect(
      examWorkspaceItemReadiness({
        ...item,
        answer_key: { ...item.answer_key, origin: "absent" },
      }),
    ).toEqual(["missing_answer_key"]);
  });

  it("reports a keyed item missing one pair", () => {
    const reasons = examWorkspaceItemReadiness(
      buildMatchingItemWithPairs([
        [1, 2],
        [2, 1],
      ]),
    );

    expect(reasons).toEqual(["incomplete_match_key"]);
  });

  it("reports a keyed item with a repeated tick", () => {
    const reasons = examWorkspaceItemReadiness(
      buildMatchingItemWithPairs([
        [1, 2],
        [1, 2],
        [2, 1],
        [3, 3],
      ]),
    );

    expect(reasons).toEqual(["incomplete_match_key"]);
  });

  it("reports nothing for a keyed item with an unpaired right entry", () => {
    expect(examWorkspaceItemReadiness(buildMatchingItemWithDistractor())).toEqual([]);
  });

  it("reports an entry without text", () => {
    const item = buildMatchingItem();

    expect(
      examWorkspaceItemReadiness({
        ...item,
        match_right: item.match_right.map((entry) =>
          entry.right_id === "right_003" ? { ...entry, body: plainBody("") } : entry,
        ),
      }),
    ).toEqual(["empty_match_entry"]);
  });

  it("reports the incomplete key as a reason", () => {
    const item = buildMatchingItemWithPairs([[1, 2]]);

    expect(examWorkspaceItemReadiness(item)).toEqual(["incomplete_match_key"]);
  });
});
