/**
 * Exam workspace question list row, an ordering question's mark checkbox
 * (TASK-SKRIPT-39-06-11 D1 and the orchestrator's grouping decision).
 *
 * Expected behavior:
 *   A standalone ordering question takes a mark like any other standalone
 *   question, because grouping it into a part is now allowed: the checkbox is
 *   enabled and carries no refusal title. A question inside a part and a part
 *   itself still carry no checkbox.
 */

import { mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import ExamWorkspaceQuestionRow from "./ExamWorkspaceQuestionRow.vue";
import type { ExamWorkspaceItemEntry, ExamWorkspaceListEntry } from "./examWorkspaceListEntries";

function question(
  id: string,
  options: { kind?: "free_text" | "ordering"; parentId?: string | null } = {},
): ExamWorkspaceItemEntry {
  const kind = options.kind ?? "free_text";
  return {
    aiKey: null,
    id,
    itemKind: kind,
    kind: "item",
    label: "1",
    parentId: options.parentId ?? null,
    points: 1,
    problem: null,
    status: "ok",
    text: "Text",
    typeLabel: kind === "ordering" ? "Ordna" : "Fritext",
  };
}

const mounted: Array<VueWrapper> = [];

function mountRow(entry: ExamWorkspaceListEntry, marking = true, disabled = false): VueWrapper {
  const wrapper = mount(ExamWorkspaceQuestionRow, {
    props: { disabled, entry, marked: false, marking, pointsDiffer: false, selected: false },
  });
  mounted.push(wrapper);
  return wrapper;
}

function markBox(wrapper: VueWrapper, id: string) {
  return wrapper.get(`[data-test="exam-workspace-mark-${id}"]`);
}

afterEach(() => {
  for (const wrapper of mounted.splice(0)) wrapper.unmount();
});

describe("ExamWorkspaceQuestionRow ordering mark", () => {
  it("enables a standalone ordering question's checkbox with no refusal title", () => {
    const box = markBox(mountRow(question("item_001", { kind: "ordering" })), "item_001");

    expect(box.attributes("disabled")).toBeUndefined();
    expect(box.attributes("title")).toBeUndefined();
  });

  it("emits the tick for a standalone ordering question", async () => {
    const wrapper = mountRow(question("item_001", { kind: "ordering" }));

    await markBox(wrapper, "item_001").setValue(true);

    expect(wrapper.emitted("toggleMark")).toEqual([["item_001"]]);
  });

  it("carries no checkbox for an ordering question inside a part", () => {
    const wrapper = mountRow(question("item_001", { kind: "ordering", parentId: "parent_001" }));

    expect(wrapper.find('[data-test="exam-workspace-mark-item_001"]').exists()).toBe(false);
  });

  it("disables the standalone ordering checkbox while the workspace is busy", () => {
    const box = markBox(mountRow(question("item_001", { kind: "ordering" }), true, true), "item_001");

    expect(box.attributes("disabled")).toBeDefined();
    expect(box.attributes("title")).toBeUndefined();
  });
});
