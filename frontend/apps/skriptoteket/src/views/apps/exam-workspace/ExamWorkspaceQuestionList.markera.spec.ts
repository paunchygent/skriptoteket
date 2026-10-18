/**
 * Exam workspace question list, Markera mode.
 *
 * Expected behavior:
 *   "Markera" turns the list into Markera mode: only standalone questions carry
 *   a checkbox (a part and a question inside a part do not, G11), an ordering
 *   question's checkbox is disabled with its reason (G6), and a bar groups the
 *   ticked questions. "Skapa del av markerade (N)" is disabled at N = 0 and
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

const mounted: Array<VueWrapper> = [];

function mountList(entries: ExamWorkspaceListEntry[] = ENTRIES, disabled = false): VueWrapper {
  const wrapper = mount(ExamWorkspaceQuestionList, {
    props: {
      canAdd: true,
      disabled,
      entries,
      examInstructionsPreview: null,
      overlay: false,
      printedTotal: null,
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
  it("shows a checkbox per standalone question only, and none before the mode is on", async () => {
    const wrapper = mountList();

    expect(wrapper.find('[data-test="exam-workspace-marking-bar"]').exists()).toBe(false);
    expect(markBoxes(wrapper)).toEqual([]);

    await wrapper.get('[data-test="exam-workspace-marking-start"]').trigger("click");

    expect(wrapper.find('[data-test="exam-workspace-marking-bar"]').exists()).toBe(true);
    expect(markBoxes(wrapper)).toEqual(["item_001", "item_003", "item_004", "item_005"]);
  });

  it("disables an ordering question's checkbox with the reason", async () => {
    const wrapper = mountList();
    await wrapper.get('[data-test="exam-workspace-marking-start"]').trigger("click");

    const ordering = wrapper.get('[data-test="exam-workspace-mark-item_003"]');
    expect(ordering.attributes("disabled")).toBeDefined();
    expect(ordering.attributes("title")).toBe("Ordna-frågor kan inte ligga i en del");

    const freeText = wrapper.get('[data-test="exam-workspace-mark-item_001"]');
    expect(freeText.attributes("disabled")).toBeUndefined();
  });

  it("emits the ticks in document order and disables the action at zero", async () => {
    const wrapper = mountList();
    await wrapper.get('[data-test="exam-workspace-marking-start"]').trigger("click");

    const group = wrapper.get('[data-test="exam-workspace-group-marked"]');
    expect(group.text()).toBe("Skapa del av markerade (0)");
    expect(group.attributes("disabled")).toBeDefined();

    await wrapper.get('[data-test="exam-workspace-mark-item_005"]').setValue(true);
    await wrapper.get('[data-test="exam-workspace-mark-item_001"]').setValue(true);

    expect(wrapper.get('[data-test="exam-workspace-group-marked"]').text()).toBe("Skapa del av markerade (2)");
    await wrapper.get('[data-test="exam-workspace-group-marked"]').trigger("click");

    expect(wrapper.emitted("group")).toEqual([[["item_001", "item_005"]]]);
  });

  it("leaves the mode once the ticked questions become a part's children", async () => {
    const wrapper = mountList();
    await wrapper.get('[data-test="exam-workspace-marking-start"]').trigger("click");
    await wrapper.get('[data-test="exam-workspace-mark-item_001"]').setValue(true);
    await wrapper.get('[data-test="exam-workspace-group-marked"]').trigger("click");

    await wrapper.setProps({
      entries: [
        part("parent_002", "1", ["item_002", "item_001"]),
        question("item_002", "1a", { parentId: "parent_002" }),
        question("item_001", "1b", { parentId: "parent_002" }),
      ],
    });

    expect(wrapper.find('[data-test="exam-workspace-marking-bar"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-marking-start"]').exists()).toBe(true);
  });

  it("clears the ticks and leaves the mode on Avbryt", async () => {
    const wrapper = mountList();
    await wrapper.get('[data-test="exam-workspace-marking-start"]').trigger("click");
    await wrapper.get('[data-test="exam-workspace-mark-item_001"]').setValue(true);

    await wrapper.get('[data-test="exam-workspace-marking-cancel"]').trigger("click");

    expect(wrapper.find('[data-test="exam-workspace-marking-bar"]').exists()).toBe(false);
    expect(markBoxes(wrapper)).toEqual([]);

    await wrapper.get('[data-test="exam-workspace-marking-start"]').trigger("click");
    expect(wrapper.get('[data-test="exam-workspace-group-marked"]').text()).toBe("Skapa del av markerade (0)");
  });

  it("disables the checkboxes and the bar while the workspace is busy", async () => {
    const wrapper = mountList();
    await wrapper.get('[data-test="exam-workspace-marking-start"]').trigger("click");
    await wrapper.get('[data-test="exam-workspace-mark-item_001"]').setValue(true);

    await wrapper.setProps({ disabled: true });

    expect(wrapper.get('[data-test="exam-workspace-mark-item_001"]').attributes("disabled")).toBeDefined();
    expect(wrapper.get('[data-test="exam-workspace-group-marked"]').attributes("disabled")).toBeDefined();
    expect(wrapper.get('[data-test="exam-workspace-marking-cancel"]').attributes("disabled")).toBeDefined();
  });
});
