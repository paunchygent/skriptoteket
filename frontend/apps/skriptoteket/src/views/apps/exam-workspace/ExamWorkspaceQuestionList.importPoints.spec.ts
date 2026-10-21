/**
 * Exam workspace question list, import-points line (TASK-SKRIPT-40-04-23).
 *
 * Expected behavior:
 *   When `importPointsIds` is non-empty the list shows one extra floating
 *   note line "{N} frågor avviker från provtexten" (singular "1 fråga
 *   avviker från provtexten") with two glyph-only actions: "Visa frågorna"
 *   (meaning `continue`) steps through those questions one at a time and
 *   "Avfärda" (meaning `close`) emits a dismiss. The rows whose ids are in
 *   `importPointsIds` show their points amber in the row meta. The existing
 *   printed-total lines stay exactly as they are.
 */

import { mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import { UiGlyph } from "../../../components/ui";
import ExamWorkspaceQuestionList from "./ExamWorkspaceQuestionList.vue";
import type {
  ExamWorkspaceItemEntry,
  ExamWorkspaceListEntry,
} from "./examWorkspaceListEntries";
import type { PrintedTotalMismatch } from "./examWorkspaceTotals";

function question(id: string, label: string): ExamWorkspaceItemEntry {
  return {
    aiKey: null,
    id,
    itemKind: "free_text",
    kind: "item",
    label,
    parentId: null,
    points: 5,
    problem: null,
    status: "ok",
    text: `Text ${label}`,
    typeLabel: "Fritext",
  };
}

const ENTRIES: ExamWorkspaceListEntry[] = [
  question("q1", "1"),
  question("q2", "2"),
  question("q3", "3"),
];

const IMPORT_LINE = '[data-test="exam-workspace-import-points-line"]';
const SHOW = '[data-test="exam-workspace-import-points-show"]';
const DISMISS = '[data-test="exam-workspace-import-points-dismiss"]';
const PRINTED_LINE = '[data-test="exam-workspace-printed-total-line"]';
const PRINTED_SHOW = '[data-test="exam-workspace-printed-total-show"]';
const PRINTED_CHANGE = '[data-test="exam-workspace-printed-total-change"]';
const END_ROOM = '[data-test="exam-workspace-list-end-room"]';

const mounted: Array<VueWrapper> = [];

function mountList(options: {
  importPointsIds?: string[];
  mismatches?: PrintedTotalMismatch[];
  selectedId?: string | null;
} = {}): VueWrapper {
  const wrapper = mount(ExamWorkspaceQuestionList, {
    props: {
      canAdd: true,
      disabled: false,
      entries: ENTRIES,
      examInstructionsPreview: null,
      importPointsIds: options.importPointsIds ?? [],
      mismatches: options.mismatches ?? [],
      overlay: false,
      questionCount: 3,
      selectedId: options.selectedId ?? null,
      total: 15,
    },
  });
  mounted.push(wrapper);
  return wrapper;
}

afterEach(() => {
  for (const wrapper of mounted.splice(0)) wrapper.unmount();
});

describe("ExamWorkspaceQuestionList import-points line", () => {
  it("names one differing question in the singular and two in the plural", () => {
    const one = mountList({ importPointsIds: ["q1"] });
    expect(one.get(IMPORT_LINE).attributes("aria-label")).toBe("1 fråga avviker från provtexten");

    const two = mountList({ importPointsIds: ["q1", "q3"] });
    expect(two.get(IMPORT_LINE).attributes("aria-label")).toBe("2 frågor avviker från provtexten");
  });

  it("shows the line when the totals agree, and first when a printed-total line shows", () => {
    const alone = mountList({ importPointsIds: ["q1"], mismatches: [] });
    expect(alone.findAll(IMPORT_LINE)).toHaveLength(1);
    expect(alone.findAll(PRINTED_LINE)).toHaveLength(0);

    const mismatches: PrintedTotalMismatch[] = [
      { level: "exam", printed: 70, sum: 15, target: "q1" },
    ];
    const both = mountList({ importPointsIds: ["q1", "q3"], mismatches });
    expect(both.findAll(IMPORT_LINE)).toHaveLength(1);
    expect(both.findAll(PRINTED_LINE)).toHaveLength(1);
    expect(both.get(IMPORT_LINE).attributes("aria-label")).toBe("2 frågor avviker från provtexten");
    const stack = both.get('[data-test="exam-workspace-printed-total-lines"]');
    const ordered = stack.findAll(`${IMPORT_LINE}, ${PRINTED_LINE}`);
    expect(ordered.map((line) => line.attributes("data-test"))).toEqual([
      "exam-workspace-import-points-line",
      "exam-workspace-printed-total-line",
    ]);
    expect(both.get(PRINTED_LINE).attributes("aria-label")).toBe(
      "Provtexten säger 70 p, frågorna ger 15 p.",
    );
    expect(both.findAll(PRINTED_CHANGE)).toHaveLength(1);
    expect(both.findAll(PRINTED_SHOW)).toHaveLength(1);
  });

  it("renders no import line for an empty id list", () => {
    const wrapper = mountList({ importPointsIds: [] });
    expect(wrapper.findAll(IMPORT_LINE)).toHaveLength(0);
    expect(wrapper.find('[data-test="exam-workspace-printed-total-lines"]').exists()).toBe(false);
  });

  it("steps Visa frågorna through the ids one at a time, wrapping to the first", async () => {
    const ids = ["q1", "q3"];

    const fromNull = mountList({ importPointsIds: ids, selectedId: null });
    await fromNull.get(SHOW).trigger("click");
    expect(fromNull.emitted("select")).toEqual([["q1"]]);

    const fromFirst = mountList({ importPointsIds: ids, selectedId: "q1" });
    await fromFirst.get(SHOW).trigger("click");
    expect(fromFirst.emitted("select")).toEqual([["q3"]]);

    const fromLast = mountList({ importPointsIds: ids, selectedId: "q3" });
    await fromLast.get(SHOW).trigger("click");
    expect(fromLast.emitted("select")).toEqual([["q1"]]);
  });

  it("emits one dismissImportPoints on Avfärda", async () => {
    const wrapper = mountList({ importPointsIds: ["q1", "q3"] });
    await wrapper.get(DISMISS).trigger("click");
    expect(wrapper.emitted("dismissImportPoints")).toEqual([[]]);
  });

  it("marks only the differing rows' points amber with the same meta text", () => {
    const wrapper = mountList({ importPointsIds: ["q1", "q3"] });

    for (const id of ["q1", "q3"]) {
      const row = wrapper.get(`[data-test="exam-workspace-row-${id}"]`);
      const mark = row.get('[data-test="exam-workspace-row-points-differ"]');
      expect(mark.classes()).toContain("xw-warn");
      expect(row.text()).toContain("Fritext · 5 p");
    }

    const other = wrapper.get('[data-test="exam-workspace-row-q2"]');
    expect(other.find('[data-test="exam-workspace-row-points-differ"]').exists()).toBe(false);
    expect(other.text()).toContain("Fritext · 5 p");
  });

  it("keeps the line's buttons glyph-only with continue and close meanings", () => {
    const wrapper = mountList({ importPointsIds: ["q1"] });

    const line = wrapper.get(IMPORT_LINE);
    expect(line.attributes("role")).toBe("group");
    const show = line.get(SHOW);
    expect(show.attributes("aria-label")).toBe("Visa frågorna");
    expect(show.attributes("title")).toBe("Visa frågorna");
    expect(show.findComponent(UiGlyph).props("meaning")).toBe("continue");
    expect(show.text()).toBe("");
    const dismiss = line.get(DISMISS);
    expect(dismiss.attributes("aria-label")).toBe("Avfärda");
    expect(dismiss.attributes("title")).toBe("Avfärda");
    expect(dismiss.findComponent(UiGlyph).props("meaning")).toBe("close");
    expect(dismiss.text()).toBe("");
  });

  it("always ends the scroll content with the one-row end room, with or without the line", () => {
    const withLine = mountList({ importPointsIds: ["q1"] });
    expect(withLine.get(END_ROOM).element.closest(".list__scroll")).not.toBeNull();

    const withoutLine = mountList({ importPointsIds: [] });
    expect(withoutLine.get(END_ROOM).element.closest(".list__scroll")).not.toBeNull();
  });
});
