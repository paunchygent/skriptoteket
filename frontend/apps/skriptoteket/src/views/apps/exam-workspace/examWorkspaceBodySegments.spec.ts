import { describe, expect, it } from "vitest";

import {
  applyAssetState,
  atomIds,
  gapChipLabel,
  parseAcceptedValues,
  partsFromParagraphElement,
  renderParagraphElement,
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
        { kind: "text", marks: [], text: "Huvudstaden " },
        { kind: "text", marks: [], text: "är " },
        { kind: "atom", segment: { kind: "gap", gap_id: "gap_001" } },
        { kind: "text", marks: [], text: "" },
        { kind: "atom", segment: { kind: "asset", asset_id: "asset_001" } },
        { kind: "text", marks: [], text: " " },
      ]),
    ).toEqual([
      { kind: "text", marks: [], text: "Huvudstaden är " },
      { kind: "gap", gap_id: "gap_001" },
      { kind: "asset", asset_id: "asset_001" },
      { kind: "text", marks: [], text: " " },
    ]);
  });

  it("returns no segments for an emptied paragraph", () => {
    expect(segmentsFromParts([{ kind: "text", marks: [], text: "" }])).toEqual([]);
  });
});

describe("atom sequence comparison", () => {
  it("identifies gaps and assets by id and order", () => {
    const original = [
      { kind: "text" as const, marks: [], text: "A " },
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
    expect(
      gapChipLabel(
        { gap_id: "gap_001", accepted_values: ["Stockholm", "Sthlm"], automatic_values: [], excluded_automatic_values: [] },
        1,
      ),
    ).toBe("Stockholm / Sthlm");
    expect(gapChipLabel({ gap_id: "gap_002", accepted_values: [], automatic_values: [], excluded_automatic_values: [] }, 2)).toBe("Lucka 2");
  });
});

describe("parseAcceptedValues", () => {
  it("splits on commas, trims and drops empty values", () => {
    expect(parseAcceptedValues(" a , b,, ")).toEqual(["a", "b"]);
  });
});

describe("asset segment rendering", () => {
  it("renders a mapped asset as an image and an unmapped asset as the placeholder", () => {
    const element = document.createElement("div");
    renderParagraphElement(element, [{ kind: "asset", asset_id: "asset_001" }], [], {
      asset_001: "https://gateway.test/assets/asset_001",
    });

    const atom = element.querySelector<HTMLElement>('[data-atom="asset"]')!;
    const image = atom.querySelector("img")!;
    expect(image.getAttribute("src")).toBe("https://gateway.test/assets/asset_001");
    expect(atom.hasAttribute("data-label")).toBe(false);
    expect(segmentsFromParts(partsFromParagraphElement(element))).toEqual([
      { kind: "asset", asset_id: "asset_001" },
    ]);

    applyAssetState(atom, "asset_001", {});
    expect(atom.querySelector("img")).toBeNull();
    expect(atom.getAttribute("data-label")).toBe("Bild");
  });

  it("updates the image source in place and keeps one image per atom", () => {
    const element = document.createElement("div");
    renderParagraphElement(element, [{ kind: "asset", asset_id: "asset_001" }], [], {
      asset_001: "https://gateway.test/assets/one.png",
    });
    const atom = element.querySelector<HTMLElement>('[data-atom="asset"]')!;
    const image = atom.querySelector("img")!;

    applyAssetState(atom, "asset_001", { asset_001: "https://gateway.test/assets/two.png" });
    expect(atom.querySelector("img")).toBe(image);
    expect(image.getAttribute("src")).toBe("https://gateway.test/assets/two.png");

    applyAssetState(atom, "asset_001", { asset_001: "https://gateway.test/assets/two.png" });
    expect(atom.querySelectorAll("img")).toHaveLength(1);
    expect(atom.querySelector("img")).toBe(image);
  });
});

describe("partsFromParagraphElement", () => {
  it("reads text, atoms and inner line breaks and ignores the trailing sentinel", () => {
    const element = paragraphElement(
      'Rad ett<br>rad två <span data-atom="gap" data-gap-id="gap_001">Stockholm</span>' +
        ' och <span data-atom="asset" data-asset-id="asset_001">Bild</span>\nslut<br data-trailing-break="">',
    );
    expect(segmentsFromParts(partsFromParagraphElement(element))).toEqual([
      { kind: "text", marks: [], text: "Rad ett\nrad två " },
      { kind: "gap", gap_id: "gap_001" },
      { kind: "text", marks: [], text: " och " },
      { kind: "asset", asset_id: "asset_001" },
      { kind: "text", marks: [], text: "\nslut" },
    ]);
  });

  it("treats a browser-inserted block as a new line", () => {
    const element = paragraphElement("Första<div>andra</div>");
    expect(segmentsFromParts(partsFromParagraphElement(element))).toEqual([
      { kind: "text", marks: [], text: "Första\nandra" },
    ]);
  });
});
