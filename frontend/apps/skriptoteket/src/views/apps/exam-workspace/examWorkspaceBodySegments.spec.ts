import { describe, expect, it } from "vitest";

import {
  atomIds,
  gapChipLabel,
  parseAcceptedValues,
  partsFromParagraphElement,
  sameAtomSequence,
  segmentsFromParts,
} from "./examWorkspaceBodySegments";

function paragraphElement(html: string): HTMLElement {
  const element = document.createElement("div");
  element.innerHTML = html;
  return element;
}

describe("segmentsFromParts", () => {
  it("merges adjacent text, drops empty text and keeps atoms in order", () => {
    expect(
      segmentsFromParts([
        { kind: "text", text: "Huvudstaden " },
        { kind: "text", text: "är " },
        { kind: "atom", segment: { kind: "gap", gap_id: "gap_001" } },
        { kind: "text", text: "" },
        { kind: "atom", segment: { kind: "asset", asset_id: "asset_001" } },
        { kind: "text", text: " " },
      ]),
    ).toEqual([
      { kind: "text", text: "Huvudstaden är " },
      { kind: "gap", gap_id: "gap_001" },
      { kind: "asset", asset_id: "asset_001" },
      { kind: "text", text: " " },
    ]);
  });

  it("returns no segments for an emptied paragraph", () => {
    expect(segmentsFromParts([{ kind: "text", text: "" }])).toEqual([]);
  });
});

describe("atom sequence comparison", () => {
  it("identifies gaps and assets by id and order", () => {
    const original = [
      { kind: "text" as const, text: "A " },
      { kind: "gap" as const, gap_id: "gap_001" },
      { kind: "gap" as const, gap_id: "gap_002" },
    ];
    expect(atomIds(original)).toEqual(["gap:gap_001", "gap:gap_002"]);
    expect(sameAtomSequence(original, [original[1]!, original[2]!])).toBe(true);
    expect(sameAtomSequence(original, [original[2]!, original[1]!])).toBe(false);
    expect(sameAtomSequence(original, [original[1]!])).toBe(false);
  });
});

describe("gapChipLabel", () => {
  it("joins accepted values or falls back to the gap number", () => {
    expect(gapChipLabel({ gap_id: "gap_001", accepted_values: ["Stockholm", "Sthlm"] }, 1)).toBe(
      "Stockholm / Sthlm",
    );
    expect(gapChipLabel({ gap_id: "gap_002", accepted_values: [] }, 2)).toBe("Lucka 2");
  });
});

describe("parseAcceptedValues", () => {
  it("splits on commas, trims and drops empty values", () => {
    expect(parseAcceptedValues(" a , b,, ")).toEqual(["a", "b"]);
  });
});

describe("partsFromParagraphElement", () => {
  it("reads text, atoms and inner line breaks and ignores the trailing sentinel", () => {
    const element = paragraphElement(
      'Rad ett<br>rad två <span data-atom="gap" data-gap-id="gap_001">Stockholm</span>' +
        ' och <span data-atom="asset" data-asset-id="asset_001">Bild</span>\nslut<br data-trailing-break="">',
    );
    expect(segmentsFromParts(partsFromParagraphElement(element))).toEqual([
      { kind: "text", text: "Rad ett\nrad två " },
      { kind: "gap", gap_id: "gap_001" },
      { kind: "text", text: " och " },
      { kind: "asset", asset_id: "asset_001" },
      { kind: "text", text: "\nslut" },
    ]);
  });

  it("treats a browser-inserted block as a new line", () => {
    const element = paragraphElement("Första<div>andra</div>");
    expect(segmentsFromParts(partsFromParagraphElement(element))).toEqual([
      { kind: "text", text: "Första\nandra" },
    ]);
  });
});
