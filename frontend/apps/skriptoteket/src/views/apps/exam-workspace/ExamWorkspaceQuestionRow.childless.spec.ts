/**
 * Exam workspace question list row, childless part.
 *
 * Expected behavior:
 *   A part with no questions is an unnumbered instruction block: no number,
 *   its instruction excerpt or "Tom instruktion" when empty, the meta
 *   "Instruktion utan frågor" and no points, though its fixed-height points
 *   line stays in place (G5, R1). Clicking it selects the part, so its
 *   instruction opens in the editor. A part with questions keeps its number,
 *   counts and points.
 */

import { mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import ExamWorkspaceQuestionRow from "./ExamWorkspaceQuestionRow.vue";
import type { ExamWorkspaceListEntry, ExamWorkspaceParentEntry } from "./examWorkspaceListEntries";

function part(id: string, label: string, childIds: string[], text: string): ExamWorkspaceParentEntry {
  return { childIds, id, kind: "parent", label, points: 0, text };
}

const mounted: Array<VueWrapper> = [];

function mountRow(entry: ExamWorkspaceListEntry): VueWrapper {
  const wrapper = mount(ExamWorkspaceQuestionRow, {
    props: { disabled: false, entry, marked: false, marking: false, selected: false },
  });
  mounted.push(wrapper);
  return wrapper;
}

afterEach(() => {
  for (const wrapper of mounted.splice(0)) wrapper.unmount();
});

describe("ExamWorkspaceQuestionRow childless part", () => {
  it("shows no number, the excerpt or Tom instruktion, the meta and no points", () => {
    const empty = mountRow(part("parent_001", "", [], ""));

    expect(empty.get(".row__n").text()).toBe("");
    expect(empty.get(".row__text").text()).toBe("Tom instruktion");
    expect(empty.get(".row__meta").text()).toBe("Instruktion utan frågor");
    // The points line keeps its fixed-height slot but renders no points.
    const line = empty.get(".row__pointsline");
    expect(line.text()).toBe("");
    expect(line.attributes("aria-hidden")).toBe("true");
    expect(empty.find('[data-test="exam-workspace-part-points-line"]').exists()).toBe(false);

    const written = mountRow(part("parent_002", "", [], "Läs texten och svara"));
    expect(written.get(".row__text").text()).toBe("Läs texten och svara");
  });

  it("selects the part when clicked", async () => {
    const wrapper = mountRow(part("parent_001", "", [], "Läs texten"));

    await wrapper.get('[data-test="exam-workspace-row-parent_001"]').trigger("click");

    expect(wrapper.emitted("select")).toEqual([["parent_001"]]);
  });

  it("keeps a part with questions numbered and scored", () => {
    const entry = part("parent_001", "2", ["item_003"], "Delinstruktion");
    entry.points = 4;
    const wrapper = mountRow(entry);

    expect(wrapper.get(".row__n").text()).toBe("2");
    expect(wrapper.get(".row__meta").text()).toBe("Instruktion · 1 fråga");
    expect(wrapper.get('[data-test="exam-workspace-part-points-line"]').text()).toBe("4 p");
  });
});
