/**
 * Exam workspace question list, points note.
 *
 * Expected behavior:
 *   While the printed-total account is set and not dismissed, the footer
 *   reads "Totalt N p" with the amber note below it: the heading, one
 *   arrow-glyph jump row per difference in document order, and the last
 *   line "Använd beräknade poäng?" followed by exactly two glyph-only
 *   answers, no (`close`, large filled navy circle, first) and yes
 *   (`confirm`, smaller outlined circle). Each answer's name lives in its
 *   tooltip and aria-label only. Clicking a part or question row selects
 *   it through the list's `select`; the remainder row selects nothing.
 *   While the workspace is busy every note control is disabled, like the
 *   list's other controls. No Använd text button exists anywhere.
 */

import { mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import { UiGlyph } from "../../../components/ui";
import ExamWorkspaceQuestionList from "./ExamWorkspaceQuestionList.vue";
import type { ExamWorkspaceListEntry } from "./examWorkspaceListEntries";
import { examWorkspaceListEntries } from "./examWorkspaceListEntries";
import type { NativeExamDocument, NativeExamItem } from "../../../api/examWorkspace";
import { buildFreeTextItem } from "../../../test/examWorkspaceFixtures";
import type { PrintedTotalAccount } from "./examWorkspaceTotals";
import { examWorkspacePrintedDifferences } from "./examWorkspaceTotals";

function item(sequence: number, points: number | null, source: number | null): NativeExamItem {
  return { ...buildFreeTextItem(sequence), points, source_points: source };
}

function paragraph(text: string) {
  return { heading_level: null, segments: [{ kind: "text" as const, marks: [], text }] };
}

function mockupDocument(): NativeExamDocument {
  return {
    assets: [],
    document_id: "00000000-0000-4000-8000-000000000001",
    header: { printed_total: 70, printed_total_dismissed: false, tags: [] },
    instructions: [],
    items: [
      item(1, 10, 10),
      item(2, 9, 9),
      item(3, 10, 10),
      item(4, 10, 10),
      item(5, 8, 8),
      item(6, 10, 12),
      item(7, 5, 5),
      item(8, 5, 5),
      item(9, null, 4),
    ],
    origin: { kind: "created" },
    parents: [{
      parent_id: "parent_001",
      item_ids: ["item_003", "item_004"],
      place: 2,
      printed_total: 22,
      instruction: [paragraph("Del 2: Satslösning")],
    }],
    revision: 1,
    schema_version: "native_exam_document_v9",
    title: "Prov",
  };
}

function entriesOf(document: NativeExamDocument): ExamWorkspaceListEntry[] {
  return examWorkspaceListEntries(document, {}, new Set());
}

function accountOf(document: NativeExamDocument): PrintedTotalAccount {
  const account = examWorkspacePrintedDifferences(document);
  if (!account) {
    throw new Error("The fixture document holds no printed-total difference.");
  }
  return account;
}

const NOTE = '[data-test="exam-workspace-points-note"]';
const NOTE_ROW = '[data-test="exam-workspace-points-note-row"]';
const NOTE_KEEP = '[data-test="exam-workspace-points-keep"]';
const NOTE_USE = '[data-test="exam-workspace-points-use-computed"]';

const mounted: Array<VueWrapper> = [];

function mountList(document: NativeExamDocument, options: { account?: PrintedTotalAccount | null; examDiffers?: boolean; disabled?: boolean } = {}): VueWrapper {
  const entries = entriesOf(document);
  const wrapper = mount(ExamWorkspaceQuestionList, {
    props: {
      account: options.account === undefined ? examWorkspacePrintedDifferences(document) : options.account,
      canAdd: true,
      disabled: options.disabled ?? false,
      entries,
      examDiffers: options.examDiffers ?? true,
      examInstructionsPreview: null,
      overlay: false,
      questionCount: entries.filter((entry) => entry.kind === "item").length,
      selectedId: null,
      total: entries.reduce((sum, entry) => sum + (entry.kind === "item" ? (entry.points ?? 0) : 0), 0),
    },
  });
  mounted.push(wrapper);
  return wrapper;
}

function rowTexts(wrapper: VueWrapper): string[] {
  return wrapper.findAll(NOTE_ROW).map((row) => row.text().replace(/\s+/g, " ").trim());
}

afterEach(() => {
  for (const wrapper of mounted.splice(0)) wrapper.unmount();
});

describe("ExamWorkspaceQuestionList points note", () => {
  it("renders the mockup rows in order with the arrow glyph and no Använd text", () => {
    const wrapper = mountList(mockupDocument());

    expect(wrapper.get(NOTE).find(".list__note-head").text())
      .toBe("Provtexten anger 70 p. Dessa skiljer sig:");
    expect(rowTexts(wrapper)).toEqual([
      "Del 2: Satslösning — provtexten 22 p, nu 20 p",
      "Fråga 5 — provtexten 12 p, nu 10 p",
      "Fråga 8 — provtexten 4 p, saknar poäng",
      "5 p fler än provtexten anger",
    ]);
    expect(wrapper.findAll(NOTE_ROW)).toHaveLength(4);
    expect(wrapper.get(NOTE_KEEP).findComponent(UiGlyph).props("meaning")).toBe("close");
    expect(wrapper.get(NOTE_USE).findComponent(UiGlyph).props("meaning")).toBe("confirm");
    expect(wrapper.findAll(`button${NOTE_ROW}`).map((row) => row.findComponent(UiGlyph).props("meaning")))
      .toEqual(["continue", "continue", "continue"]);
    // The decide line is plain text; no button offers an Använd action.
    expect(wrapper.get(".list__note-question").text()).toBe("Använd beräknade poäng?");
    expect(wrapper.findAll("button").filter((button) => button.text().startsWith("Använd"))).toHaveLength(0);
    expect(wrapper.find('[data-test^="exam-workspace-accept-"]').exists()).toBe(false);
  });

  it("names a remainder no question explains, in both directions", () => {
    const over: NativeExamDocument = {
      ...mockupDocument(),
      header: { printed_total: 70, printed_total_dismissed: false, tags: [] },
      items: [item(1, 30, 30), item(2, 37, 37)],
      parents: [],
    };
    expect(rowTexts(mountList(over))).toEqual(["Övriga 3 p finns inte i någon fråga"]);

    const under: NativeExamDocument = { ...over, header: { printed_total: 60, printed_total_dismissed: false, tags: [] } };
    expect(rowTexts(mountList(under))).toEqual(["7 p fler än provtexten anger"]);
  });

  it("keeps a third-decimal difference readable instead of two equal numbers", () => {
    const document: NativeExamDocument = {
      ...mockupDocument(),
      header: { printed_total: 12.001, printed_total_dismissed: false, tags: [] },
      items: [item(1, 12, 12.001)],
      parents: [],
    };
    expect(rowTexts(mountList(document))).toEqual(["Fråga 1 — provtexten 12,001 p, nu 12 p"]);
  });

  it("names a question that prints nothing with no source number", () => {
    const document: NativeExamDocument = {
      ...mockupDocument(),
      header: { printed_total: 12, printed_total_dismissed: false, tags: [] },
      items: [item(1, null, null), item(2, 10, 10)],
      parents: [],
    };
    expect(rowTexts(mountList(document))).toEqual(["Fråga 1 — saknar poäng", "Övriga 2 p finns inte i någon fråga"]);
  });

  it("uses the parts heading when only parts differ", () => {
    const document: NativeExamDocument = {
      ...mockupDocument(),
      header: { printed_total: null, printed_total_dismissed: false, tags: [] },
      items: [item(1, 2, 2), item(2, 3, 3)],
      parents: [{
        parent_id: "parent_001", item_ids: ["item_001", "item_002"], place: 0,
        printed_total: 8, instruction: [paragraph("Del 1")],
      }],
    };
    const wrapper = mountList(document, { examDiffers: false });
    expect(wrapper.get('[data-test="exam-workspace-exam-points"]').text()).toBe("Totalt 5 p");
    expect(wrapper.get(NOTE).find(".list__note-head").text()).toBe("Dessa skiljer sig från provtexten:");
    expect(rowTexts(wrapper)).toEqual(["Del 1 — provtexten 8 p, nu 5 p"]);
  });

  it("shows only the sum when the exam total matches but a part differs", () => {
    const document: NativeExamDocument = {
      ...mockupDocument(),
      header: { printed_total: 5, printed_total_dismissed: false, tags: [] },
      items: [item(1, 2, 2), item(2, 3, 3)],
      parents: [{
        parent_id: "parent_001", item_ids: ["item_001", "item_002"], place: 0,
        printed_total: 8, instruction: [paragraph("Del 1")],
      }],
    };
    const wrapper = mountList(document, { examDiffers: false });
    expect(wrapper.get('[data-test="exam-workspace-exam-points"]').text()).toBe("Totalt 5 p");
    expect(wrapper.get(NOTE).find(".list__note-head").text()).toBe("Dessa skiljer sig från provtexten:");
  });

  it("hides the note and greys the printed part once dismissed", () => {
    const document = mockupDocument();
    const account = { ...accountOf(document), dismissed: true };
    const wrapper = mountList(document, { account });

    expect(wrapper.find(NOTE).exists()).toBe(false);
    expect(wrapper.get('[data-test="exam-workspace-exam-points"]').text())
      .toBe("Totalt 67 p · provtexten anger 70 p");
    expect(wrapper.get('[data-test="exam-workspace-exam-points"]').get(".list__dismissed").text())
      .toBe("· provtexten anger 70 p");
  });

  it("shows only the sum when the account is null", () => {
    const document: NativeExamDocument = {
      ...mockupDocument(),
      header: { printed_total: 67, printed_total_dismissed: false, tags: [] },
      items: [item(1, 30, 30), item(2, 37, 37)],
      parents: [],
    };
    const wrapper = mountList(document, { account: null, examDiffers: false });
    expect(wrapper.find(NOTE).exists()).toBe(false);
    expect(wrapper.get('[data-test="exam-workspace-exam-points"]').text()).toBe("Totalt 67 p");
  });

  it("gives the answers no visible text, only the tooltip and aria-label, no first and larger", () => {
    const wrapper = mountList(mockupDocument());
    const keep = wrapper.get(NOTE_KEEP);
    const use = wrapper.get(NOTE_USE);

    expect(keep.text()).toBe("");
    expect(keep.attributes("aria-label")).toBe("Nej, behåll provtextens poäng");
    expect(keep.attributes("title")).toBe("Nej, behåll provtextens poäng");
    expect(use.text()).toBe("");
    expect(use.attributes("aria-label")).toBe("Ja, använd beräknade poäng");
    expect(use.attributes("title")).toBe("Ja, använd beräknade poäng");
    const buttons = wrapper.findAll(".list__note-decide button");
    expect(buttons.map((button) => button.attributes("data-test"))).toEqual([
      "exam-workspace-points-keep",
      "exam-workspace-points-use-computed",
    ]);
    const meanings = wrapper.findAllComponents(UiGlyph).map((glyph) => glyph.props("meaning"));
    expect(meanings).toContain("close");
    expect(meanings).toContain("confirm");
  });

  it("emits the answers and selects a part or question row, never the remainder", async () => {
    const wrapper = mountList(mockupDocument());

    await wrapper.get(NOTE_KEEP).trigger("click");
    await wrapper.get(NOTE_USE).trigger("click");
    expect(wrapper.emitted("dismissPrintedTotal")).toEqual([[]]);
    expect(wrapper.emitted("useComputedPoints")).toEqual([[]]);

    await wrapper.findAll(NOTE_ROW).at(0)!.trigger("click");
    await wrapper.findAll(NOTE_ROW).at(1)!.trigger("click");
    expect(wrapper.emitted("select")).toEqual([[ "parent_001" ], [ "item_006" ]]);

    await wrapper.findAll(NOTE_ROW).at(3)!.trigger("click");
    expect(wrapper.emitted("select")).toHaveLength(2);
  });

  it("disables the note's buttons and jump rows exactly like the list's other controls", async () => {
    const wrapper = mountList(mockupDocument());
    await wrapper.setProps({ disabled: true });

    expect(wrapper.get(NOTE_KEEP).attributes("disabled")).toBeDefined();
    expect(wrapper.get(NOTE_USE).attributes("disabled")).toBeDefined();
    expect(wrapper.findAll(NOTE_ROW).at(0)!.attributes("disabled")).toBeDefined();
    expect(wrapper.get('[data-test="exam-workspace-marking-start"]').attributes("disabled")).toBeDefined();
  });
});
