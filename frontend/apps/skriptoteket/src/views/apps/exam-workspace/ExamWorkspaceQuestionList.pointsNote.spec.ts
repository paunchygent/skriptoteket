/**
 * Exam workspace question list, printed-total mismatch lines.
 *
 * Expected behavior:
 *   The footer reads "Totalt N p" with one line below it per printed
 *   total that differs from its questions' sum: the exam line first, then
 *   one line per differing part in document order. Each line states the
 *   exact printed and summed points and is followed by two compact
 *   glyph-only buttons with no visible text, named only by tooltip and
 *   aria-label: confirm ("Godta frågornas summa, {sum} p", clears that line's
 *   own level) and continue ("Visa frågorna", selects the line's target,
 *   hidden when the line has no target). A line is `role="group"` named by
 *   its text. While the workspace is busy both buttons are disabled.
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
import type { PrintedTotalMismatch } from "./examWorkspaceTotals";
import {
  examWorkspacePrintedTotalMismatches,
  withoutExamPrintedTotal,
  withoutPartPrintedTotal,
} from "./examWorkspaceTotals";

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
    header: { printed_total: 70, tags: [] },
    instructions: [],
    items: [
      item(1, 10, 12),
      item(2, 9, 9),
      item(3, 9, 10),
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
      instruction: [paragraph("Del 3: Satslösning")],
    }],
    revision: 1,
    schema_version: "native_exam_document_v11",
    title: "Prov",
  };
}

function entriesOf(document: NativeExamDocument): ExamWorkspaceListEntry[] {
  return examWorkspaceListEntries(document, {}, new Set());
}

const LINE = '[data-test="exam-workspace-printed-total-line"]';
const CHANGE = '[data-test="exam-workspace-printed-total-change"]';
const SHOW = '[data-test="exam-workspace-printed-total-show"]';

const mounted: Array<VueWrapper> = [];

function mountList(
  document: NativeExamDocument,
  options: { mismatches?: PrintedTotalMismatch[]; disabled?: boolean } = {},
): VueWrapper {
  const entries = entriesOf(document);
  const wrapper = mount(ExamWorkspaceQuestionList, {
    props: {
      canAdd: true,
      disabled: options.disabled ?? false,
      entries,
      examInstructionsPreview: null,
      importPointsIds: [],
      mismatches: options.mismatches ?? examWorkspacePrintedTotalMismatches(document),
      overlay: false,
      questionCount: entries.filter((entry) => entry.kind === "item").length,
      selectedId: null,
      total: entries.reduce((sum, entry) => sum + (entry.kind === "item" ? (entry.points ?? 0) : 0), 0),
    },
  });
  mounted.push(wrapper);
  return wrapper;
}

function lineTexts(wrapper: VueWrapper): string[] {
  return wrapper.findAll(LINE).map((line) => (line.attributes("aria-label") ?? "").replace(/\s+/g, " ").trim());
}

afterEach(() => {
  for (const wrapper of mounted.splice(0)) wrapper.unmount();
});

describe("ExamWorkspaceQuestionList printed-total lines", () => {
  it("states the exam difference with exact numbers and the two glyph-only actions", () => {
    const document: NativeExamDocument = {
      ...mockupDocument(),
      items: [item(1, 30, 30), item(2, 37, 38)],
      parents: [],
    };
    const wrapper = mountList(document);

    expect(wrapper.get('[data-test="exam-workspace-exam-points"]').text()).toBe("Totalt 67 p");
    expect(lineTexts(wrapper)).toEqual(["Provtexten säger 70 p, frågorna ger 67 p."]);

    const line = wrapper.get(LINE);
    expect(line.attributes("role")).toBe("group");
    const change = line.get(CHANGE);
    expect(change.attributes("aria-label")).toBe("Godta frågornas summa, 67 p");
    expect(change.attributes("title")).toBe("Godta frågornas summa, 67 p");
    expect(change.findComponent(UiGlyph).props("meaning")).toBe("confirm");
    const show = line.get(SHOW);
    expect(show.attributes("aria-label")).toBe("Visa frågorna");
    expect(show.attributes("title")).toBe("Visa frågorna");
    expect(show.findComponent(UiGlyph).props("meaning")).toBe("continue");
  });

  it("prints a third decimal instead of two equal numbers", () => {
    const document: NativeExamDocument = {
      ...mockupDocument(),
      header: { printed_total: 12.001, tags: [] },
      items: [item(1, 12, 12.001)],
      parents: [],
    };
    const wrapper = mountList(document);

    expect(lineTexts(wrapper)).toEqual(["Provtexten säger 12,001 p, frågorna ger 12 p."]);
    expect(wrapper.get(CHANGE).attributes("aria-label")).toBe("Godta frågornas summa, 12 p");
  });

  it("lists the exam line first, then one line per differing part with the list's numbers", () => {
    const document: NativeExamDocument = {
      ...mockupDocument(),
      header: { printed_total: 70, tags: [] },
      items: [item(1, 10, 10), item(2, 10, 12), item(3, 5, 5), item(4, 5, 5)],
      parents: [
        {
          parent_id: "parent_001", item_ids: ["item_001", "item_002"], place: 0,
          printed_total: 22, instruction: [paragraph("Del 1")],
        },
        {
          parent_id: "parent_002", item_ids: ["item_003", "item_004"], place: 2,
          printed_total: 12, instruction: [paragraph("Del 2")],
        },
      ],
    };
    const wrapper = mountList(document);

    expect(lineTexts(wrapper)).toEqual([
      "Provtexten säger 70 p, frågorna ger 30 p.",
      "Del 1 i provtexten säger 22 p, frågorna ger 20 p.",
      "Del 2 i provtexten säger 12 p, frågorna ger 10 p.",
    ]);
  });

  it("shows only the part line when the exam total agrees", () => {
    const document: NativeExamDocument = {
      ...mockupDocument(),
      header: { printed_total: 5, tags: [] },
      items: [item(1, 2, 2), item(2, 3, 3)],
      parents: [{
        parent_id: "parent_001", item_ids: ["item_001", "item_002"], place: 0,
        printed_total: 8, instruction: [paragraph("Del 1")],
      }],
    };
    const wrapper = mountList(document);

    expect(wrapper.get('[data-test="exam-workspace-exam-points"]').text()).toBe("Totalt 5 p");
    expect(lineTexts(wrapper)).toEqual(["Del 1 i provtexten säger 8 p, frågorna ger 5 p."]);
  });

  it("emits one clear per level: the exam line clears only the header, a part line only its part", async () => {
    const wrapper = mountList(mockupDocument());

    await wrapper.findAll(CHANGE).at(0)!.trigger("click");
    await wrapper.findAll(CHANGE).at(1)!.trigger("click");
    expect(wrapper.emitted("clearPrintedTotal")).toEqual([[null], ["parent_001"]]);

    const clearedExam = withoutExamPrintedTotal(mockupDocument());
    expect(examWorkspacePrintedTotalMismatches(clearedExam)).toHaveLength(1);
    expect(clearedExam.header.printed_total).toBeNull();
    expect(clearedExam.parents[0]!.printed_total).toBe(22);

    const clearedPart = withoutPartPrintedTotal(mockupDocument(), "parent_001");
    expect(examWorkspacePrintedTotalMismatches(clearedPart)).toHaveLength(1);
    expect(clearedPart.header.printed_total).toBe(70);
    expect(clearedPart.parents[0]!.printed_total).toBeNull();
  });

  it("selects the first differing question, and falls back to the first differing part for the exam line", async () => {
    const wrapper = mountList(mockupDocument());

    await wrapper.findAll(SHOW).at(0)!.trigger("click");
    await wrapper.findAll(SHOW).at(1)!.trigger("click");
    expect(wrapper.emitted("select")).toEqual([["item_001"], ["item_003"]]);

    const sourceItself: NativeExamDocument = {
      ...mockupDocument(),
      items: [item(1, 30, 30), item(2, 37, 37)],
      parents: [{
        parent_id: "parent_001", item_ids: ["item_001"], place: 0,
        printed_total: 31, instruction: [paragraph("Del 1")],
      }],
    };
    const fallback = mountList(sourceItself);
    await fallback.findAll(SHOW).at(0)!.trigger("click");
    expect(fallback.emitted("select")).toEqual([["parent_001"]]);
  });

  it("hides Visa frågorna when the line has no target", () => {
    const document: NativeExamDocument = {
      ...mockupDocument(),
      items: [item(1, 30, 30), item(2, 37, 37)],
      parents: [],
    };
    const wrapper = mountList(document);

    expect(wrapper.findAll(LINE)).toHaveLength(1);
    expect(wrapper.findAll(SHOW)).toHaveLength(0);
    expect(wrapper.findAll(CHANGE)).toHaveLength(1);
  });

  it("shows no line for float noise", () => {
    const document: NativeExamDocument = {
      ...mockupDocument(),
      header: { printed_total: 0.3, tags: [] },
      items: [item(1, 0.1, 0.1), item(2, 0.2, 0.2)],
      parents: [],
    };
    const wrapper = mountList(document);

    expect(wrapper.findAll(LINE)).toHaveLength(0);
    expect(wrapper.get('[data-test="exam-workspace-exam-points"]').text()).toBe("Totalt 0,3 p");
  });

  it("disables both buttons while the workspace is busy", async () => {
    const wrapper = mountList(mockupDocument());
    await wrapper.setProps({ disabled: true });

    expect(wrapper.get(CHANGE).attributes("disabled")).toBeDefined();
    expect(wrapper.get(SHOW).attributes("disabled")).toBeDefined();
    expect(wrapper.get('[data-test="exam-workspace-marking-toggle"]').attributes("disabled")).toBeDefined();
  });

  it("keeps both buttons free of visible text and removes every note element", () => {
    const wrapper = mountList(mockupDocument());

    for (const button of wrapper.findAll(`${CHANGE}, ${SHOW}`)) {
      expect(button.text()).toBe("");
    }
    expect(wrapper.find('[data-test="exam-workspace-points-note"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-points-keep"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-points-use-computed"]').exists()).toBe(false);
  });

  it("floats the lines over the list, outside the fixed-height footer", () => {
    const wrapper = mountList(mockupDocument());

    const lines = wrapper.get('[data-test="exam-workspace-printed-total-lines"]');
    expect(lines.element.closest(".list__foot")).toBeNull();
    expect(wrapper.get(".list__foot").find('[data-test="exam-workspace-printed-total-lines"]').exists()).toBe(false);
  });

  it("always ends the scroll content with the one-row end room, with or without a line", () => {
    const withLine = mountList(mockupDocument());
    const endRoom = withLine.get('[data-test="exam-workspace-list-end-room"]');
    expect(endRoom.element.closest(".list__scroll")).not.toBeNull();

    const agreed: NativeExamDocument = {
      ...mockupDocument(),
      header: { printed_total: null, tags: [] },
      parents: [],
    };
    const withoutLine = mountList(agreed, { mismatches: [] });
    expect(withoutLine.findAll(LINE)).toHaveLength(0);
    const bareRoom = withoutLine.get('[data-test="exam-workspace-list-end-room"]');
    expect(bareRoom.element.closest(".list__scroll")).not.toBeNull();
  });
});
