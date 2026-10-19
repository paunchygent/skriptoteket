/**
 * Exam workspace question list, Markera mode.
 *
 * Expected behavior:
 *   Markera mode changes nothing but state: the bar under the header, its
 *   group action and its one toggle slot are always present, and every row
 *   keeps its mark cell. The toggle shows "Markera" (data-test
 *   exam-workspace-marking-start) when the mode is off and "Avbryt"
 *   (exam-workspace-marking-cancel) when it is on, in the same element; the
 *   group action "Skapa del av markerade (N)" keeps its box but is hidden
 *   while the mode is off. Only standalone questions carry a checkbox (a part
 *   and a question inside a part do not, G11); an ordering question's checkbox
 *   is disabled with its reason (G6). The group action is disabled at N = 0 and
 *   emits the ticks in document order (G10); Avbryt clears the ticks and leaves
 *   the mode; while the workspace is busy every control is disabled.
 */

import { mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import ExamWorkspaceQuestionList from "./ExamWorkspaceQuestionList.vue";
import type {
  ExamWorkspaceItemEntry,
  ExamWorkspaceListEntry,
  ExamWorkspaceParentEntry,
} from "./examWorkspaceListEntries";

function question(
  id: string,
  label: string,
  options: { parentId?: string | null; kind?: "free_text" | "ordering" } = {},
): ExamWorkspaceItemEntry {
  return {
    aiKey: null,
    id,
    itemKind: options.kind ?? "free_text",
    kind: "item",
    label,
    parentId: options.parentId ?? null,
    points: 1,
    problem: null,
    status: "ok",
    text: `Text ${label}`,
    typeLabel: options.kind === "ordering" ? "Ordna" : "Fritext",
  };
}

function part(id: string, label: string, childIds: string[]): ExamWorkspaceParentEntry {
  return { childIds, id, kind: "parent", label, points: 2, printedTotal: null, text: "Delinstruktion" };
}

const ENTRIES: ExamWorkspaceListEntry[] = [
  question("item_001", "1"),
  part("parent_001", "2", ["item_002"]),
  question("item_002", "2a", { parentId: "parent_001" }),
  question("item_003", "3", { kind: "ordering" }),
  question("item_004", "4"),
  question("item_005", "5"),
];

const BAR = '[data-test="exam-workspace-marking-bar"]';
const GROUP = '[data-test="exam-workspace-group-marked"]';
const START = '[data-test="exam-workspace-marking-start"]';
const CANCEL = '[data-test="exam-workspace-marking-cancel"]';
const ROW_MARK = ".row__mark";
/** The class that hides the group action and a row's mark cell while not marking. */
const IDLE_GROUP = "list__markbar-group--idle";
const IDLE_CELL = "row__mark--idle";

const mounted: Array<VueWrapper> = [];

function mountList(entries: ExamWorkspaceListEntry[] = ENTRIES, disabled = false): VueWrapper {
  const wrapper = mount(ExamWorkspaceQuestionList, {
    props: {
      account: null,
      canAdd: true,
      disabled,
      entries,
      examDiffers: false,
      examInstructionsPreview: null,
      overlay: false,
      questionCount: entries.filter((entry) => entry.kind === "item").length,
      selectedId: null,
      total: 5,
    },
  });
  mounted.push(wrapper);
  return wrapper;
}

function markBoxes(wrapper: VueWrapper): string[] {
  return wrapper
    .findAll('[data-test^="exam-workspace-mark-"]')
    .map((box) => box.attributes("data-test")!.replace("exam-workspace-mark-", ""));
}

afterEach(() => {
  for (const wrapper of mounted.splice(0)) wrapper.unmount();
});

describe("ExamWorkspaceQuestionList Markera mode", () => {
  it("keeps the bar, its controls and every row's mark cell in place across Markera and Avbryt", async () => {
    const wrapper = mountList();

    const bar = wrapper.get(BAR).element;
    const group = wrapper.get(GROUP).element;
    const toggle = wrapper.get(START).element;

    // Not marking: same bar, group hidden in its box, one hidden mark cell per row.
    expect(wrapper.get(GROUP).classes()).toContain(IDLE_GROUP);
    expect(wrapper.findAll(ROW_MARK)).toHaveLength(ENTRIES.length);
    expect(wrapper.findAll(`.${IDLE_CELL}`)).toHaveLength(ENTRIES.length);

    await wrapper.get(START).trigger("click");

    // Marking: same elements, the group action shown and the toggle now Avbryt.
    expect(wrapper.get(BAR).element).toBe(bar);
    expect(wrapper.get(GROUP).element).toBe(group);
    expect(wrapper.get(CANCEL).element).toBe(toggle);
    expect(wrapper.get(GROUP).classes()).not.toContain(IDLE_GROUP);
    expect(wrapper.findAll(ROW_MARK)).toHaveLength(ENTRIES.length);
    expect(wrapper.findAll(`.${IDLE_CELL}`)).toHaveLength(0);

    await wrapper.get(CANCEL).trigger("click");

    expect(wrapper.get(BAR).element).toBe(bar);
    expect(wrapper.get(GROUP).element).toBe(group);
    expect(wrapper.get(START).element).toBe(toggle);
    expect(wrapper.get(GROUP).classes()).toContain(IDLE_GROUP);
    expect(wrapper.findAll(`.${IDLE_CELL}`)).toHaveLength(ENTRIES.length);
  });

  it("shows a checkbox per standalone question only", async () => {
    const wrapper = mountList();

    expect(markBoxes(wrapper)).toEqual(["item_001", "item_003", "item_004", "item_005"]);

    await wrapper.get(START).trigger("click");

    expect(markBoxes(wrapper)).toEqual(["item_001", "item_003", "item_004", "item_005"]);
  });

  it("disables an ordering question's checkbox with the reason", async () => {
    const wrapper = mountList();
    await wrapper.get(START).trigger("click");

    const ordering = wrapper.get('[data-test="exam-workspace-mark-item_003"]');
    expect(ordering.attributes("disabled")).toBeDefined();
    expect(ordering.attributes("title")).toBe("Ordna-frågor kan inte ligga i en del");

    const freeText = wrapper.get('[data-test="exam-workspace-mark-item_001"]');
    expect(freeText.attributes("disabled")).toBeUndefined();
  });

  it("emits the ticks in document order and disables the action at zero", async () => {
    const wrapper = mountList();
    await wrapper.get(START).trigger("click");

    const group = wrapper.get(GROUP);
    expect(group.text()).toBe("Skapa del av markerade (0)");
    expect(group.attributes("disabled")).toBeDefined();

    await wrapper.get('[data-test="exam-workspace-mark-item_005"]').setValue(true);
    await wrapper.get('[data-test="exam-workspace-mark-item_001"]').setValue(true);

    expect(wrapper.get(GROUP).text()).toBe("Skapa del av markerade (2)");
    await wrapper.get(GROUP).trigger("click");

    expect(wrapper.emitted("group")).toEqual([[["item_001", "item_005"]]]);
  });

  it("leaves the mode once the ticked questions become a part's children", async () => {
    const wrapper = mountList();
    await wrapper.get(START).trigger("click");
    await wrapper.get('[data-test="exam-workspace-mark-item_001"]').setValue(true);
    await wrapper.get(GROUP).trigger("click");

    await wrapper.setProps({
      entries: [
        part("parent_002", "1", ["item_002", "item_001"]),
        question("item_002", "1a", { parentId: "parent_002" }),
        question("item_001", "1b", { parentId: "parent_002" }),
      ],
    });

    expect(wrapper.find(START).exists()).toBe(true);
    expect(wrapper.get(GROUP).classes()).toContain(IDLE_GROUP);
    expect(markBoxes(wrapper)).toEqual([]);
  });

  it("clears the ticks and leaves the mode on Avbryt", async () => {
    const wrapper = mountList();
    await wrapper.get(START).trigger("click");
    await wrapper.get('[data-test="exam-workspace-mark-item_001"]').setValue(true);

    await wrapper.get(CANCEL).trigger("click");

    expect(wrapper.find(START).exists()).toBe(true);
    expect(wrapper.get(GROUP).classes()).toContain(IDLE_GROUP);

    await wrapper.get(START).trigger("click");
    expect(wrapper.get(GROUP).text()).toBe("Skapa del av markerade (0)");
  });

  it("disables the checkboxes and the bar while the workspace is busy", async () => {
    const wrapper = mountList();
    await wrapper.get(START).trigger("click");
    await wrapper.get('[data-test="exam-workspace-mark-item_001"]').setValue(true);

    await wrapper.setProps({ disabled: true });

    expect(wrapper.get('[data-test="exam-workspace-mark-item_001"]').attributes("disabled")).toBeDefined();
    expect(wrapper.get(GROUP).attributes("disabled")).toBeDefined();
    expect(wrapper.get(CANCEL).attributes("disabled")).toBeDefined();
  });
});
