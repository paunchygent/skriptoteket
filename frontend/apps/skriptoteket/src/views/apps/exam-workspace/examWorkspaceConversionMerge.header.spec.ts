/** Header metadata must survive progressive conversion without replacing local edits. */
import { describe, expect, it } from "vitest";

import { mergeConversionRevision, sameDocument } from "./examWorkspaceConversionMerge";
import { buildParentDocument } from "./examWorkspaceParentDocument.specSupport";

function baseDocument() {
  return {
    ...buildParentDocument(),
    header: { course_hint: null, printed_total: null },
  };
}

describe("conversion merge header metadata", () => {
  it("takes an arriving header and each parent's printed total with its parent, not its array position", () => {
    const base = baseDocument();
    const first = base.parents[0]!;
    base.parents = [
      { ...first, item_ids: ["item_001", "item_002"], printed_total: null },
      { ...first, parent_id: "parent_002", item_ids: ["item_003", "item_004"], printed_total: null },
    ];
    const head = {
      ...base,
      revision: 2,
      header: { course_hint: "Svenska 2", printed_total: 36 },
      parents: [
        { ...base.parents[1]!, printed_total: 15 },
        { ...base.parents[0]!, printed_total: 21 },
      ],
    };

    const merged = mergeConversionRevision({ base, local: base, head, baseUnits: [], headUnits: [] });

    expect(merged.header).toEqual({ course_hint: "Svenska 2", printed_total: 36 });
    expect(merged.parents.map((parent) => [parent.parent_id, parent.printed_total])).toEqual([
      ["parent_002", 15],
      ["parent_001", 21],
    ]);
    expect(sameDocument(merged, head)).toBe(true);
  });

  it("preserves a local header change through a newer head and its re-delivery", () => {
    const base = baseDocument();
    const local = { ...base, header: { course_hint: "Lärarens kursrad", printed_total: 7.5 } };
    const head = { ...base, revision: 2, header: { course_hint: "Konverterad kursrad", printed_total: 20 } };
    const merged = mergeConversionRevision({ base, local, head, baseUnits: [], headUnits: [] });
    const redelivered = mergeConversionRevision({
      base: head,
      local: merged,
      head: { ...head, revision: 3 },
      baseUnits: [],
      headUnits: [],
    });

    expect(merged.header).toEqual(local.header);
    expect(redelivered.header).toEqual(local.header);
    expect(redelivered.revision).toBe(3);
    expect(sameDocument(redelivered, head)).toBe(false);
  });

  it("retains a locally edited parent and its total instead of pairing it with a new server total", () => {
    const base = baseDocument();
    base.parents = base.parents.map((parent) => ({ ...parent, printed_total: 3 }));
    const local = {
      ...base,
      parents: base.parents.map((parent) => ({
        ...parent,
        printed_total: 7.5,
        instruction: [{ heading_level: null, segments: [{ kind: "text" as const, marks: [], text: "Lärarens instruktion" }] }],
      })),
    };
    const head = { ...base, revision: 2, parents: base.parents.map((parent) => ({ ...parent, printed_total: 9 })) };

    const merged = mergeConversionRevision({ base, local, head, baseUnits: [], headUnits: [] });

    expect(merged.parents).toEqual(local.parents);
    expect(merged.parents[0]!.printed_total).toBe(7.5);
  });
});
