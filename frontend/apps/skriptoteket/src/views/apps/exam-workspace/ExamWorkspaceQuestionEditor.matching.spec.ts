/**
 * Exam workspace question editor, Kategorisera grid.
 *
 * Expected behavior:
 *   A matching item shows the Kategorisera grid: a row per left entry, a
 *   column per right entry, and a checkbox per cell with the key ticked.
 *   Ticking or unticking a cell emits the full tick list in row and column
 *   order, so a row may hold several ticks and a column several rows (Q9).
 *   The tick value is editable, the points are read-only (Q10), and an
 *   invalid tick value is marked without being emitted. An incomplete key,
 *   meaning a keyed row without a tick, shows the inline guidance; an unused
 *   column keeps the key complete; an empty entry text shows the entry hint.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { NativeExamItem } from "../../../api/examWorkspace";
import ExamWorkspaceQuestionEditor from "./ExamWorkspaceQuestionEditor.vue";
import { INCOMPLETE_MATCH_KEY_GUIDANCE } from "./examWorkspaceAnswerKeyRules";
import { plainBody } from "./examWorkspaceRichText";
import {
  buildMatchingItem,
  buildMatchingItemWithDistractor,
  buildMatchingItemWithPairs,
} from "./examWorkspaceMatchingItem.specSupport";

function mountEditor(item: NativeExamItem) {
  return mount(ExamWorkspaceQuestionEditor, {
    props: {
      item,
      label: "1",
      origin: "digiexam_import",
      parent: null,
      child: null,
      suggestedKind: null,
      converting: false,
      disabled: false,
      notice: null,
      importOpen: false,
      lastChildDeletable: false,
    },
  });
}

function tick(leftId: string, rightId: string): string {
  return `[data-test="exam-workspace-match-tick-${leftId}-${rightId}"]`;
}

describe("ExamWorkspaceQuestionEditor Kategorisera grid", () => {
  it("renders the grid with the key ticked and the Kategorisera labels", () => {
    const wrapper = mountEditor(buildMatchingItem());

    expect(wrapper.get('[data-test="exam-workspace-kategorisera-grid"]').text()).toContain(
      "Kategorisera",
    );
    expect(wrapper.text()).toContain("Fråga 1");
    expect(wrapper.get<HTMLInputElement>(tick("left_001", "right_002")).element.checked).toBe(true);
    expect(wrapper.get<HTMLInputElement>(tick("left_001", "right_001")).element.checked).toBe(false);
    expect(wrapper.get(tick("left_001", "right_002")).attributes("aria-label")).toBe(
      "absence from school without permission: truancy",
    );
    expect(
      wrapper.get('[data-test="exam-workspace-match-right-text-right_003"]').text(),
    ).toBe("disdain");
    expect(wrapper.find('[data-test="exam-workspace-match-key-hint"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-match-hint"]').exists()).toBe(false);
  });

  it("emits a second tick in a row, keeping row and column order", async () => {
    const wrapper = mountEditor(buildMatchingItem());

    await wrapper.get(tick("left_002", "right_003")).setValue(true);

    expect(wrapper.emitted("updateMatchPairs")).toEqual([
      [
        "item_001",
        [
          { left_id: "left_001", right_id: "right_002" },
          { left_id: "left_002", right_id: "right_001" },
          { left_id: "left_002", right_id: "right_003" },
          { left_id: "left_003", right_id: "right_003" },
        ],
      ],
    ]);
  });

  it("emits an empty tick list when the only tick is cleared", async () => {
    const wrapper = mountEditor(buildMatchingItemWithPairs([[2, 1]]));

    await wrapper.get(tick("left_002", "right_001")).setValue(false);

    expect(wrapper.emitted("updateMatchPairs")).toEqual([["item_001", []]]);
  });

  it("accepts one column serving several rows", () => {
    const wrapper = mountEditor(
      buildMatchingItemWithPairs([
        [1, 2],
        [2, 2],
        [3, 2],
      ]),
    );

    expect(wrapper.find('[data-test="exam-workspace-match-key-hint"]').exists()).toBe(false);
  });

  it("shows the key guidance while a keyed row has no tick", () => {
    const wrapper = mountEditor(
      buildMatchingItemWithPairs([
        [1, 2],
        [2, 1],
      ]),
    );

    expect(wrapper.get('[data-test="exam-workspace-match-key-hint"]').text()).toBe(
      INCOMPLETE_MATCH_KEY_GUIDANCE,
    );
  });

  it("keeps the key complete beside an unused column", () => {
    const wrapper = mountEditor(buildMatchingItemWithDistractor());

    expect(wrapper.find('[data-test="exam-workspace-match-key-hint"]').exists()).toBe(false);
    expect(wrapper.find(tick("left_001", "right_004")).exists()).toBe(true);
  });

  it("shows read-only points and emits a valid tick value", async () => {
    const wrapper = mountEditor(buildMatchingItem());
    const points = wrapper.get<HTMLInputElement>('[data-test="exam-workspace-item-points-input"]');
    const tickPoints = wrapper.get('[data-test="exam-workspace-item-tick-points-input"]');

    expect(points.attributes("readonly")).toBeDefined();
    expect(points.element.value).toBe("3");
    await tickPoints.setValue("0.5");

    expect(wrapper.emitted("updateTickPoints")).toEqual([["item_001", "0.5"]]);
    expect(tickPoints.attributes("aria-invalid")).toBeUndefined();
  });

  it("marks a tick value with three decimals and emits nothing", async () => {
    const wrapper = mountEditor(buildMatchingItem());
    const tickPoints = wrapper.get('[data-test="exam-workspace-item-tick-points-input"]');

    await tickPoints.setValue("0.125");

    expect(tickPoints.attributes("aria-invalid")).toBe("true");
    expect(wrapper.emitted("updateTickPoints")).toBeUndefined();
  });

  it("accepts a tick value of zero, which the question editor allows", async () => {
    const wrapper = mountEditor(buildMatchingItem());
    const tickPoints = wrapper.get('[data-test="exam-workspace-item-tick-points-input"]');

    await tickPoints.setValue("0");

    expect(tickPoints.attributes("aria-invalid")).toBeUndefined();
    expect(wrapper.emitted("updateTickPoints")).toEqual([["item_001", "0"]]);
  });

  it("emits the side and id of an edited entry text", async () => {
    const wrapper = mountEditor(buildMatchingItem());
    const left = wrapper.get('[data-test="exam-workspace-match-left-text-left_001"]')
      .element as HTMLElement;
    const right = wrapper.get('[data-test="exam-workspace-match-right-text-right_001"]')
      .element as HTMLElement;

    left.textContent = "skipping class";
    right.textContent = "jail time";
    await wrapper.get('[data-test="exam-workspace-match-left-text-left_001"]').trigger("input");
    await wrapper.get('[data-test="exam-workspace-match-right-text-right_001"]').trigger("input");

    expect(wrapper.emitted("updateMatchEntryBody")).toEqual([
      ["item_001", "left", "left_001", plainBody("skipping class")],
      ["item_001", "right", "right_001", plainBody("jail time")],
    ]);
  });

  it("marks an empty entry text with the hint", () => {
    const item = buildMatchingItem();
    const wrapper = mountEditor({
      ...item,
      match_left: item.match_left.map((entry) =>
        entry.left_id === "left_003" ? { ...entry, body: plainBody("") } : entry,
      ),
    });

    expect(wrapper.get('[data-test="exam-workspace-match-hint"]').text()).toBe(
      "En rad eller en kategori saknar text.",
    );
    expect(
      wrapper.get('[data-test="exam-workspace-match-left-text-left_003"]').attributes("aria-invalid"),
    ).toBe("true");
  });
});
